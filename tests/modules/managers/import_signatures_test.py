"""
Tests that validate the functionality of the module that is responsible for managing imported distribution trees.
"""

import os
import pathlib
from typing import Any, Callable, Dict, Generator

import pytest
from pytest_mock import MockerFixture

from cobbler.api import CobblerAPI
from cobbler.modules.managers import import_signatures


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
    manager.signature = {
        "kernel_arch": "tools\\.t00",
        "kernel_arch_regex": "^.*(x86_64).*$",
        "supported_arches": ["x86_64"],
    }
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
    manager.signature = {
        "kernel_options": {},
        "kernel_options_post": {},
        "template_files": {},
        "boot_files": [],
    }
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
