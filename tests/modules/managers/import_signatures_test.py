"""
Tests that validate the functionality of the module that is responsible for managing imported distribution trees.
"""

import os
import pathlib
import stat
from typing import Any, Callable, Dict, Generator, List

import pytest
from libcobblersignatures.models.osversion import Osversion
from pytest_mock import MockerFixture

from cobbler.api import CobblerAPI
from cobbler.modules.managers import import_signatures


def _make_signature(**overrides: Any) -> Osversion:
    """
    Build an Osversion DAO for test setup, with the library's own defaults unless overridden.
    """
    version = Osversion()
    for key, value in overrides.items():
        setattr(version, key, value)
    return version


@pytest.fixture(name="reset_import_manager", scope="function", autouse=True)
def fixture_reset_import_manager() -> Generator[Any, Any, Any]:
    """
    Fixture to reset the singleton instance of _ImportSignatureManager before and after each test, so that a stale
    reference to a previous test's (now torn down) collections/settings can't leak into this one.
    """
    import_signatures.MANAGER = None
    yield
    import_signatures.MANAGER = None


def test_register():
    # Arrange
    # Act
    result = import_signatures.register()

    # Assert
    assert result == "manage/import"


@pytest.mark.skip("too lazy to implement")
def test_import_walker():
    # Arrange
    # Act
    import_signatures.import_walker("", True, "")  # type: ignore

    # Assert
    assert False


def test_get_manager(cobbler_api: CobblerAPI):
    # Arrange & Act
    result = import_signatures.get_import_manager(cobbler_api)

    # Assert
    # pylint: disable-next=protected-access
    isinstance(result, import_signatures._ImportSignatureManager)  # type: ignore


def test_manager_what():
    # Arrange & Act & Assert
    # pylint: disable-next=protected-access
    assert import_signatures._ImportSignatureManager.what() == "import/signatures"  # type: ignore


def test_arch_walker_matches_kernel_arch_regex_from_bytes(
    cobbler_api: CobblerAPI, mocker: MockerFixture
):
    # Arrange
    manager = import_signatures.get_import_manager(cobbler_api)
    manager.signature = _make_signature(
        kernel_arch="tools\\.t00",
        kernel_arch_regex="^.*(x86_64).*$",
        supported_arches={"x86_64"},
    )
    get_file_lines = mocker.patch.object(
        manager, "get_file_lines", return_value=[b"architecture=x86_64\n"]
    )
    result: Dict[Any, Any] = {}

    # Act
    manager.arch_walker(result, "/tmp/esxi", ["tools.t00"])

    # Assert
    assert result == {"x86_64": 1}
    get_file_lines.assert_called_once_with(os.path.join("/tmp/esxi", "tools.t00"))


def _prepare_add_entry_manager(
    manager: "import_signatures._ImportSignatureManager",  # type: ignore[reportPrivateUsage]
    mocker: MockerFixture,
    rootdir: str,
    direct_source: bool,
) -> None:
    """
    Shared setup for ``add_entry()`` tests: fake out everything except the bits that matter for
    ``source_tree_path`` handling (arch detection, profile creation).
    """
    manager.path = rootdir
    manager.rootdir = rootdir
    manager.pkgdir = rootdir
    manager.name = "test-import"
    manager.network_root = None
    manager.arch = None
    manager.breed = "redhat"  # type: ignore[assignment]
    manager.os_version = ""
    manager.direct_source = direct_source
    manager.signature = _make_signature()
    mocker.patch.object(manager, "learn_arch_from_tree", return_value=["x86_64"])
    mocker.patch.object(manager, "configure_tree_location")

    def _profiles_find_side_effect(*args: Any, **kwargs: Any) -> Any:
        # The Distro.arch setter itself calls api.find_profile(return_list=True, distro=...), which is backed by
        # this same collection's find(); it needs an (empty) iterable, not a truthy sentinel.
        if kwargs.get("return_list"):
            return []
        # This is add_entry()'s own "does a profile with this name already exist?" check: make it truthy so
        # profile creation (and the real autoinstall template lookup it would require) is skipped, since it isn't
        # relevant to what this test verifies.
        return mocker.Mock()

    mocker.patch.object(
        manager.profiles, "find", side_effect=_profiles_find_side_effect
    )


def test_add_entry_direct_source_sets_source_tree_path(
    cobbler_api: CobblerAPI,
    mocker: MockerFixture,
    tmp_path: pathlib.Path,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    When ``direct_source`` is True, ``add_entry()`` must record the original scan root on the new Distro via
    ``source_tree_path``.
    """
    # Arrange
    test_folder = create_kernel_initrd(fk_kernel, fk_initrd)
    kernel = os.path.join(test_folder, fk_kernel)
    initrd = os.path.join(test_folder, fk_initrd)
    manager = import_signatures.get_import_manager(cobbler_api)
    _prepare_add_entry_manager(manager, mocker, str(tmp_path), direct_source=True)

    # Act
    result = manager.add_entry(test_folder, kernel, initrd)

    # Assert
    assert len(result) == 1
    assert result[0].source_tree_path == str(tmp_path)


def test_add_entry_without_direct_source_leaves_source_tree_path_unset(
    cobbler_api: CobblerAPI,
    mocker: MockerFixture,
    tmp_path: pathlib.Path,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    Regression guard: with ``direct_source`` at its default (False), ``add_entry()`` must not set
    ``source_tree_path`` on the new Distro.
    """
    # Arrange
    test_folder = create_kernel_initrd(fk_kernel, fk_initrd)
    kernel = os.path.join(test_folder, fk_kernel)
    initrd = os.path.join(test_folder, fk_initrd)
    manager = import_signatures.get_import_manager(cobbler_api)
    _prepare_add_entry_manager(manager, mocker, str(tmp_path), direct_source=False)

    # Act
    result = manager.add_entry(test_folder, kernel, initrd)

    # Assert
    assert len(result) == 1
    assert result[0].source_tree_path == ""


def test_get_proposed_name_direct_source_uses_mirror_name_for_shallow_path(
    cobbler_api: CobblerAPI,
):
    """
    Regression guard: in direct-mode imports (``direct_source=True``) ``dirname`` is the admin's own local
    source path (e.g. a shallow mount point like ``/mnt/rocky10``), not a path copied under
    ``webdir/distro_mirror/<name>/...``. The path-depth heuristic (``"-".join(dirname.split("/")[5:])``)
    assumes the latter layout and collapses to an empty string for realistic shallow local paths, which
    would make every direct-mode import generate the same ``-<arch>`` name regardless of the real source
    tree. ``get_proposed_name()`` must instead fall back to the caller-supplied mirror name (``self.name``),
    exactly as it already does when an explicit ``network_root`` is given.
    """
    # Arrange
    manager = import_signatures.get_import_manager(cobbler_api)
    manager.name = "rocky10"
    manager.network_root = None
    manager.direct_source = True

    # Act
    result = manager.get_proposed_name("/mnt/rocky10")

    # Assert
    assert result == "rocky10"


def test_get_proposed_name_direct_source_disambiguates_gtk_variant(
    cobbler_api: CobblerAPI,
):
    """
    Regression guard: Debian/Ubuntu installer media ships a "gtk" (graphical installer) kernel/initrd
    pair alongside the base netboot one (e.g. "install.amd/gtk/vmlinuz" next to "install.amd/vmlinuz").
    Under a classic (copied) import, each variant's own subdirectory differentiates the proposed name via
    the path-depth heuristic. Under direct-mode imports, ``get_proposed_name()`` always falls back to the
    caller-supplied mirror name regardless of which subdirectory the kernel came from, so the "gtk" variant
    used to propose the exact same name as the base variant -- "xen" and "PAE" variants already had an
    explicit kernel-path substring check to disambiguate them, but "gtk" did not, silently dropping the gtk
    distro/profile as a duplicate during a real debian13 import under ``managers.dynamic_httpd``.
    """
    # Arrange
    manager = import_signatures.get_import_manager(cobbler_api)
    manager.name = "debian13"
    manager.network_root = None
    manager.direct_source = True

    # Act
    base_name = manager.get_proposed_name(
        "/srv/www/cobbler/distro_mirror/debian13-x86_64",
        kernel="/srv/www/cobbler/distro_mirror/debian13-x86_64/install.amd/vmlinuz",
    )
    gtk_name = manager.get_proposed_name(
        "/srv/www/cobbler/distro_mirror/debian13-x86_64",
        kernel="/srv/www/cobbler/distro_mirror/debian13-x86_64/install.amd/gtk/vmlinuz",
    )

    # Assert
    assert base_name == "debian13"
    assert gtk_name == "debian13-gtk"
    assert base_name != gtk_name


def test_add_entry_direct_source_shallow_path_names_correctly(
    cobbler_api: CobblerAPI,
    mocker: MockerFixture,
    tmp_path: pathlib.Path,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    Regression test for the naming bug found in code review: in direct mode, ``dirname`` is the admin's own
    shallow local source path (e.g. ``/mnt/rocky10``), not a path under ``webdir/distro_mirror/<name>/...``.
    Previously ``get_proposed_name()``'s path-depth heuristic collapsed such shallow paths to an empty name,
    so every direct-mode import produced just ``-<arch>``, causing distinct distros imported this way to
    collide under the same generated name (with the second one silently dropped as "already exists"). Verify
    ``add_entry()`` now derives the name from the configured mirror name instead.
    """
    # Arrange
    test_folder = create_kernel_initrd(fk_kernel, fk_initrd)
    kernel = os.path.join(test_folder, fk_kernel)
    initrd = os.path.join(test_folder, fk_initrd)
    manager = import_signatures.get_import_manager(cobbler_api)
    _prepare_add_entry_manager(manager, mocker, str(tmp_path), direct_source=True)
    manager.name = "rocky10"
    # A realistic direct-mode dirname: a shallow local mount point, independent of the (deep) pytest tmp_path.
    shallow_dirname = "/mnt/rocky10"

    # Act
    result = manager.add_entry(shallow_dirname, kernel, initrd)

    # Assert
    assert len(result) == 1
    assert result[0].name == "rocky10-x86_64"


def test_configure_tree_location_direct_source(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path, mocker: MockerFixture
):
    """
    With ``direct_source`` True, ``configure_tree_location()`` must not create a ``webdir/links/<name>`` symlink
    and must point the tree at the new ``/cblr/svc/tree/<name>/`` URL instead.
    """
    # Arrange
    manager = import_signatures.get_import_manager(cobbler_api)
    manager.rootdir = str(tmp_path)
    manager.path = str(tmp_path)
    manager.network_root = None
    manager.direct_source = True
    distro = cobbler_api.new_distro()
    distro.name = "test_configure_tree_location_direct_source"  # type: ignore[method-assign]
    dest_link = os.path.join(cobbler_api.settings().webdir, "links", distro.name)
    if os.path.lexists(dest_link):
        os.remove(dest_link)
    symlink_spy = mocker.patch("os.symlink")

    # Act
    manager.configure_tree_location(distro)

    # Assert
    symlink_spy.assert_not_called()
    assert not os.path.lexists(dest_link)
    protocol = cobbler_api.settings().autoinstall_scheme
    assert (
        distro.autoinstall_meta["tree"]
        == f"{protocol}://@@http_server@@/cblr/svc/tree/{distro.name}/"
    )


def test_harden_windows_executable_permissions_sets_execute_bit_on_exe_dll_com(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path
):
    """
    Regression test: Windows-imported ``.exe``/``.dll``/``.com`` files must come out of
    ``harden_windows_executable_permissions()`` with the Unix execute bit set, regardless of case, so that Samba
    grants Windows clients ``FILE_EXECUTE`` access over the SMB share serving ``distro_mirror``.
    """
    # Arrange
    manager = import_signatures.get_import_manager(cobbler_api)
    exe_path = tmp_path / "sources" / "setup.exe"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_bytes(b"MZ")
    exe_path.chmod(0o644)
    dll_path = tmp_path / "SOURCES" / "SOMELIB.DLL"
    dll_path.parent.mkdir(parents=True)
    dll_path.write_bytes(b"MZ")
    dll_path.chmod(0o644)
    com_path = tmp_path / "command.com"
    com_path.write_bytes(b"")
    com_path.chmod(0o644)

    # Act
    manager.harden_windows_executable_permissions(str(tmp_path))

    # Assert
    assert os.stat(exe_path).st_mode & 0o777 == 0o755
    assert os.stat(dll_path).st_mode & 0o777 == 0o755
    assert os.stat(com_path).st_mode & 0o777 == 0o755


def test_harden_windows_executable_permissions_leaves_other_files_untouched(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path
):
    """
    Regression guard: files that are not Windows executables (e.g. ``.cab``/``.txt``) must not be given an
    execute bit they shouldn't have; the fix must not broadly chmod every imported file.
    """
    # Arrange
    manager = import_signatures.get_import_manager(cobbler_api)
    cab_path = tmp_path / "sources" / "install.cab"
    cab_path.parent.mkdir(parents=True)
    cab_path.write_bytes(b"")
    cab_path.chmod(0o644)
    txt_path = tmp_path / "readme.txt"
    txt_path.write_bytes(b"")
    txt_path.chmod(0o644)

    # Act
    manager.harden_windows_executable_permissions(str(tmp_path))

    # Assert
    assert os.stat(cab_path).st_mode & 0o777 == 0o644
    assert os.stat(txt_path).st_mode & 0o777 == 0o644


def test_harden_windows_executable_permissions_does_not_follow_symlinks(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path
):
    """
    Security regression guard: a symlink inside the import tree (e.g. pointing at a file outside the staged
    ``distro_mirror`` tree) must never be chmod'd -- following it would let a crafted import source grant the
    execute bit to an arbitrary file on the host, since ``cobblerd`` runs as root.
    """
    # Arrange
    outside_target = tmp_path.parent / "outside-target.exe"
    outside_target.write_bytes(b"MZ")
    outside_target.chmod(0o600)
    staged_dir = tmp_path / "staged"
    staged_dir.mkdir()
    symlink_path = staged_dir / "setup.exe"
    symlink_path.symlink_to(outside_target)

    manager = import_signatures.get_import_manager(cobbler_api)

    # Act
    manager.harden_windows_executable_permissions(str(staged_dir))

    # Assert
    assert os.stat(outside_target).st_mode & 0o777 == 0o600


def test_harden_windows_executable_permissions_strips_setuid_setgid(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path
):
    """
    Security regression guard: a pre-existing setuid/setgid bit on an imported file must never be carried
    forward onto a now-executable file.
    """
    # Arrange
    exe_path = tmp_path / "setup.exe"
    exe_path.write_bytes(b"MZ")
    exe_path.chmod(0o4644)  # setuid + rw-r--r--

    manager = import_signatures.get_import_manager(cobbler_api)

    # Act
    manager.harden_windows_executable_permissions(str(tmp_path))

    # Assert
    mode = os.stat(exe_path).st_mode
    assert mode & 0o777 == 0o755
    assert not mode & stat.S_ISUID


def test_import_run_skips_hardening_for_direct_source(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path, mocker: MockerFixture
):
    """
    Security regression guard: ``run()`` must not chmod files under a ``direct_source`` (uncopied, externally
    managed) import tree -- Cobbler doesn't own those files and has no business changing their permissions.
    """
    manager = import_signatures.get_import_manager(cobbler_api)
    harden_spy = mocker.patch.object(manager, "harden_windows_executable_permissions")
    mocker.patch.object(manager, "import_winpe")
    mocker.patch.object(manager, "scan_signatures", return_value="windows")

    def _import_walker(
        path: str, func: Callable[[Any, str, List[str]], None], results: Any
    ) -> None:
        return None

    mocker.patch(
        "cobbler.modules.managers.import_signatures.import_walker",
        side_effect=_import_walker,
    )

    # Act
    manager.run(
        path=str(tmp_path),
        name="test-direct-source",
        breed="windows",
        direct_source=True,
    )

    # Assert
    harden_spy.assert_not_called()


def test_apt_repo_adder_debian_sets_breed_correct_components_and_dists(
    cobbler_api: CobblerAPI,
):
    """
    Regression test: ``apt_repo_adder()`` used to set the now-removed flat ``repo.apt_components``/
    ``repo.apt_dists`` attributes, which plain Python accepts as new instance attributes and silently
    discards -- the real ``repo.apt.components``/``repo.apt.dists`` (``APTOption``) stayed empty. It also
    used a Ubuntu-only component list ("main universe") regardless of breed, and its ``dists`` f-string was
    missing a space before the "-security" segment. For a Debian-breed import, the generated repo must get a
    non-empty, Debian-correct component list, a correctly spaced dists string, and a real mirror URL.
    """
    # Arrange
    manager = import_signatures.get_import_manager(cobbler_api)
    distro = cobbler_api.new_distro()
    distro.breed = "debian"
    distro.os_version = "trixie"
    distro.name = "test_apt_repo_adder_debian"

    # Act
    manager.apt_repo_adder(distro)

    # Assert
    repo = cobbler_api.find_repo(name=distro.name)
    assert repo is not None
    assert not isinstance(repo, list)
    assert repo.apt.components == ["main", "contrib", "non-free", "non-free-firmware"]
    assert repo.apt.dists == ["trixie", "trixie-updates", "trixie-security"]
    assert repo.mirror == "http://ftp.us.debian.org/debian/dists/trixie"
    assert repo.mirror_locally is False


def test_apt_repo_adder_ubuntu_sets_breed_correct_components_and_dists(
    cobbler_api: CobblerAPI,
):
    """
    Same regression as the Debian test above, but for an Ubuntu-breed import: Ubuntu does use "universe", but
    the previous hardcoded "main universe" list is missing "restricted"/"multiverse" and (via bug 1) was
    never actually applied anyway. Confirms the Ubuntu-specific component list is distinct from Debian's.
    """
    # Arrange
    manager = import_signatures.get_import_manager(cobbler_api)
    distro = cobbler_api.new_distro()
    distro.breed = "ubuntu"
    distro.os_version = "jammy"
    distro.name = "test_apt_repo_adder_ubuntu"

    # Act
    manager.apt_repo_adder(distro)

    # Assert
    repo = cobbler_api.find_repo(name=distro.name)
    assert repo is not None
    assert not isinstance(repo, list)
    assert repo.apt.components == ["main", "restricted", "universe", "multiverse"]
    assert repo.apt.dists == ["jammy", "jammy-updates", "jammy-security"]
    assert repo.mirror
    assert repo.mirror_locally is False


def test_configure_tree_location_without_direct_source_creates_symlink(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path
):
    """
    Regression guard: with ``direct_source`` at its default (False) and no ``network_root``,
    ``configure_tree_location()`` must behave exactly as it did before this feature: create the
    ``webdir/links/<name>`` symlink and point the tree at the ``/cblr/links/<name>`` URL.
    """
    # Arrange
    manager = import_signatures.get_import_manager(cobbler_api)
    manager.rootdir = str(tmp_path)
    manager.path = str(tmp_path)
    manager.network_root = None
    manager.direct_source = False
    distro = cobbler_api.new_distro()
    distro.name = "test_configure_tree_location_without_direct_source_creates_symlink"  # type: ignore[method-assign]
    dest_link = os.path.join(cobbler_api.settings().webdir, "links", distro.name)
    if os.path.lexists(dest_link):
        os.remove(dest_link)

    try:
        # Act
        manager.configure_tree_location(distro)

        # Assert
        assert os.path.islink(dest_link)
        assert os.readlink(dest_link) == str(tmp_path)
        protocol = cobbler_api.settings().autoinstall_scheme
        assert (
            distro.autoinstall_meta["tree"]
            == f"{protocol}://@@http_server@@/cblr/links/{distro.name}"
        )
    finally:
        if os.path.lexists(dest_link):
            os.remove(dest_link)
