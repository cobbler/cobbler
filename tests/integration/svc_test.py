"""
Integration test module to verify the functionality of the /svc/ HTTP endpoint.
"""

import pathlib
import shutil
import urllib.request
from typing import Any, Callable, List, Tuple

import pytest

from cobbler.remote import CobblerXMLRPCInterface

from tests.integration.conftest import WaitTaskEndType


@pytest.fixture(name="create_distro_profile_system")
def fixture_create_distro_profile_system(
    images_fake_path: pathlib.Path,
    create_distro: Callable[[List[Tuple[List[str], Any]]], str],
    create_profile: Callable[[List[Tuple[List[str], Any]]], str],
    create_system: Callable[[List[Tuple[List[str], Any]]], str],
) -> Tuple[str, str, str]:
    """
    Fixture to create the set of Cobbler Distro, Profile and System.

    :returns: The IDs of Distro, Profile and System (in that order.)
    """
    did = create_distro(
        [
            (["name"], "fake"),
            (["arch"], "x86_64"),
            (["kernel"], str(images_fake_path / "vmlinuz")),
            (["initrd"], str(images_fake_path / "initramfs")),
        ]
    )
    pid = create_profile([(["name"], "fake"), (["distro"], did)])
    sid = create_system([(["name"], "testbed"), (["profile"], pid)])
    return did, pid, sid


@pytest.mark.integration
def test_svc_autodetect(create_distro_profile_system: Tuple[str, str, str]):
    """
    Check that the Cobbler HTTP endpoint /autodetect/ is callable
    """
    # Arrange
    _ = create_distro_profile_system
    # TODO maybe test with more than one system

    # Prepare expected result
    # expected_result = "TODO"

    # Act
    urllib.request.urlopen("http://localhost/cblr/svc/op/autodetect")

    # Assert
    # FIXME endpoint not yet testable


@pytest.mark.integration
def test_svc_autoinstall(create_distro_profile_system: Tuple[str, str, str]):
    """
    Check that the Cobbler HTTP endpoint /autoinstall/ is callable
    """
    # Arrange
    _ = create_distro_profile_system
    # Prepare expected result
    expected_result = "# this file intentionally left blank\n"
    expected_result += "# admins:  edit it as you like, or leave it blank for non-interactive install\n"

    # Act
    result_system = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/autoinstall/system/testbed"
    )
    result_profile = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/autoinstall/profile/fake"
    )

    # Assert
    assert result_profile.read().decode() == expected_result
    assert result_system.read().decode() == expected_result


@pytest.mark.integration
def test_svc_bootcfg(create_distro_profile_system: Tuple[str, str, str]):
    """
    Check that the Cobbler HTTP endpoint /bootcfg/ is callable
    """
    # Arrange
    _ = create_distro_profile_system
    # Prepare expected result
    expected_result_profile = "bootstate=0\n"
    expected_result_profile += "title=Loading ESXi installer\n"
    expected_result_profile += "prefix=/images/fake\n"
    expected_result_profile += "kernel=vmlinuz\n"
    expected_result_profile += "kernelopt=runweasel \n"
    expected_result_profile += "modules=$esx_modules\n"
    expected_result_profile += "build=\n"
    expected_result_profile += "updated=0\n"
    expected_result_system = "bootstate=0\n"
    expected_result_system += "title=Loading ESXi installer\n"
    expected_result_system += "prefix=/images/fake\n"
    expected_result_system += "kernel=vmlinuz\n"
    expected_result_system += "kernelopt=runweasel \n"
    expected_result_system += "modules=$esx_modules\n"
    expected_result_system += "build=\n"
    expected_result_system += "updated=0\n"

    # Act
    result_profile = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/bootcfg/profile/fake"
    )
    result_system = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/bootcfg/system/testbed"
    )

    # Assert
    assert result_profile.read().decode() == expected_result_profile
    assert result_system.read().decode() == expected_result_system


@pytest.mark.integration
def test_svc_bootcfg_esxi(
    remote: CobblerXMLRPCInterface,
    token: str,
    listings_directory: pathlib.Path,
    create_system: Callable[[List[Tuple[List[str], Any]]], str],
    tmp_path: pathlib.Path,
    wait_task_end: WaitTaskEndType,
):
    """
    Check that the Cobbler HTTP endpoint /autoinstall/ is callable
    """
    # Arrange
    distro = "esxi70"
    version = "VMware-VMvisor-Installer-7.0U3d-19482537.x86_64.iso"
    # import a vmware distro and copy a fake boot.cfg for templating
    iso = listings_directory / "vmware" / distro / version
    root = tmp_path / version
    root.mkdir(exist_ok=True)
    files_to_create = (iso / "index").read_text(encoding="UTF-8").splitlines()
    for file in files_to_create:
        file_obj = root / file
        file_obj.parent.mkdir(parents=True, exist_ok=True)
        file_obj.touch(644, exist_ok=True)
    shutil.copytree(iso, root, dirs_exist_ok=True)
    shutil.copy2("/code/system-tests/images/fake/boot.cfg", root)
    tid = remote.background_import(
        {
            "name": "fake",
            "path": str(root),
            "arch": "x86_64",
            "breed": "vmware",
            "os_version": distro,
        },
        token,
    )
    wait_task_end(tid, remote)
    pid = remote.get_profile_handle("fake-x86_64")
    create_system([(["name"], "testbed"), (["profile"], pid)])
    # Prepare expected result
    expected_result_profile = pathlib.Path(
        "/code/tests/integration/data/test_svc_bootcfg_esxi/expected_result_profile"
    ).read_text(encoding="UTF-8")
    expected_result_system = pathlib.Path(
        "/code/tests/integration/data/test_svc_bootcfg_esxi/expected_result_system"
    ).read_text(encoding="UTF-8")

    # Act
    result_system = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/bootcfg/system/testbed"
    )
    result_profile = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/bootcfg/profile/fake-x86_64"
    )

    # Assert
    assert result_profile.read().decode() == expected_result_profile
    assert result_system.read().decode() == expected_result_system


@pytest.mark.integration
def test_svc_events(create_distro_profile_system: Tuple[str, str, str]):
    """
    Check that the Cobbler HTTP endpoint /events/ is callable
    """
    # Arrange
    _ = create_distro_profile_system
    # TODO user
    # cobbler user add --name testuser
    # Prepare expected result
    expected_result = "[]"

    # Act
    result = urllib.request.urlopen("http://localhost/cblr/svc/op/events")
    # result_user = urllib.request.urlopen("http://localhost/cblr/svc/op/events/user/testuser")

    # Assert
    assert result.read().decode() == expected_result


@pytest.mark.integration
def test_svc_find_autoinstall(create_distro_profile_system: Tuple[str, str, str]):
    """
    Check that the Cobbler HTTP endpoint /find_autoinstall/ is callable
    """
    # Arrange
    _ = create_distro_profile_system
    # Prepare expected result
    # expected_result = "TODO"

    # Act
    urllib.request.urlopen(
        "http://localhost/cblr/svc/op/find_autoinstall/system/testbed"
    )
    urllib.request.urlopen("http://localhost/cblr/svc/op/find_autoinstall/profile/fake")

    # Assert
    # FIXME endpoint not yet testable


@pytest.mark.integration
def test_svc_ipxe_image(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_system: Callable[[List[Tuple[List[str], Any]]], str],
):
    """
    Check that the Cobbler HTTP endpoint /ipxe/image/ is callable
    """
    # Arrange
    iid = remote.new_image(token)
    remote.modify_image(iid, ["name"], "fakeimage", token)
    remote.save_image(iid, token, "new")
    create_system([(["name"], "testbed"), (["image"], iid)])
    # Prepare expected result
    expected_result = ""

    # Act
    result = urllib.request.urlopen("http://localhost/cblr/svc/op/ipxe/image/fakeimage")

    # Assert
    # FIXME no output from endpoint
    assert result.read().decode() == expected_result


@pytest.mark.integration
def test_svc_ipxe_profile(
    remote: CobblerXMLRPCInterface,
    token: str,
    images_fake_path: pathlib.Path,
    create_distro: Callable[[List[Tuple[List[str], Any]]], str],
    create_profile: Callable[[List[Tuple[List[str], Any]]], str],
    create_system: Callable[[List[Tuple[List[str], Any]]], str],
):
    """
    Check that the Cobbler HTTP endpoint /ipxe/profile/ is callable
    """
    # Arrange
    iid = remote.new_image(token)
    remote.modify_image(iid, ["name"], "fakeimage", token)
    remote.save_image(iid, token, "new")
    did = create_distro(
        [
            (["name"], "fake"),
            (["arch"], "x86_64"),
            (["kernel"], str(images_fake_path / "vmlinuz")),
            (["initrd"], str(images_fake_path / "initramfs")),
        ]
    )
    pid = create_profile([(["name"], "fake"), (["distro"], did)])
    create_system([(["name"], "testbed"), (["profile"], pid), (["image"], iid)])
    # Prepare expected result
    expected_result = pathlib.Path(
        "/code/tests/integration/data/test_svc_ipxe_profile/expected_result"
    ).read_text(encoding="UTF-8")

    # Act
    result = urllib.request.urlopen("http://localhost/cblr/svc/op/ipxe/profile/fake")

    # Assert
    assert result.read().decode() == expected_result


@pytest.mark.integration
def test_svc_ipxe_system(create_distro_profile_system: Tuple[str, str, str]):
    """
    Check that the Cobbler HTTP endpoint /ipxe/system/ is callable
    """
    # Arrange
    _ = create_distro_profile_system
    # Prepare expected result
    expected_result = pathlib.Path(
        "/code/tests/integration/data/test_svc_ipxe_system/expected_result"
    ).read_text(encoding="UTF-8")

    # Act
    result = urllib.request.urlopen("http://localhost/cblr/svc/op/ipxe/system/testbed")

    # Assert
    assert result.read().decode() == expected_result


@pytest.mark.integration
def test_svc_list(create_distro_profile_system: Tuple[str, str, str]):
    """
    Check that the Cobbler HTTP endpoint /list/ is callable
    """
    # Arrange
    _ = create_distro_profile_system
    # TODO add more systems, profiles and distros, images, repos, menus
    # Prepare expected result
    expected_result_system = "testbed\n"
    expected_result_misc = "fake\n"
    expected_result_empty = ""

    # Act
    result_all = urllib.request.urlopen("http://localhost/cblr/svc/op/list")
    result_systems = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/list/what/systems"
    )
    result_profiles = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/list/what/profiles"
    )
    result_distros = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/list/what/distros"
    )
    result_images = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/list/what/images"
    )
    result_repos = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/list/what/repos"
    )
    result_menus = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/list/what/menus"
    )

    # Assert
    assert result_all.read().decode() == expected_result_system
    assert result_systems.read().decode() == expected_result_system
    assert result_profiles.read().decode() == expected_result_misc
    assert result_distros.read().decode() == expected_result_misc
    assert result_images.read().decode() == expected_result_empty
    assert result_repos.read().decode() == expected_result_empty
    assert result_menus.read().decode() == expected_result_empty


@pytest.mark.integration
def test_svc_nopxe(create_distro_profile_system: Tuple[str, str, str]):
    """
    Check that the Cobbler HTTP endpoint /nopxe/ is callable
    """
    # Arrange
    _ = create_distro_profile_system
    # Prepare expected result
    expected_result = "True"

    # Act
    result = urllib.request.urlopen("http://localhost/cblr/svc/op/nopxe/system/testbed")

    # Assert
    assert result.read().decode() == expected_result


@pytest.mark.integration
def test_svc_script(create_distro_profile_system: Tuple[str, str, str]):
    """
    Check that the Cobbler HTTP endpoint /script/ is callable
    """
    # Arrange
    _ = create_distro_profile_system
    # Prepare expected result
    # expected_result = "TODO"

    # Act
    urllib.request.urlopen(
        "http://localhost/cblr/svc/op/script/system/testbed/?script=preseed_early_default"
    )
    urllib.request.urlopen(
        "http://localhost/cblr/svc/op/script/profile/fake/?script=preseed_early_default"
    )

    # Assert
    # FIXME endpoint not yet testable


@pytest.mark.integration
def test_svc_settings(create_distro_profile_system: Tuple[str, str, str]):
    """
    Check that the Cobbler HTTP endpoint /settings/ is callable
    """
    # Arrange
    _ = create_distro_profile_system
    # Prepare expected result
    expected_result = pathlib.Path(
        "/code/tests/integration/data/test_svc_settings/expected_settings.json"
    ).read_text(encoding="UTF-8")

    # Act
    result = urllib.request.urlopen("http://localhost/cblr/svc/op/settings")

    # Assert
    assert result.read().decode() == expected_result


@pytest.mark.integration
def test_svc_template(create_distro_profile_system: Tuple[str, str, str]):
    """
    Check that the Cobbler HTTP endpoint /template/ is callable
    """
    # Arrange
    _ = create_distro_profile_system
    # expected_result = "TODO"

    # Act
    urllib.request.urlopen("http://localhost/cblr/svc/op/template/profile/fake")
    urllib.request.urlopen("http://localhost/cblr/svc/op/template/system/testbed")

    # Assert
    # FIXME endpoint not yet testable


@pytest.mark.integration
def test_svc_trig(create_distro_profile_system: Tuple[str, str, str]):
    """
    Check that the Cobbler HTTP endpoint /trig/ is callable
    """
    # Arrange
    _ = create_distro_profile_system
    # Prepare expected result
    expected_result = "False"

    # Act
    result_general = urllib.request.urlopen("http://localhost/cblr/svc/op/trig")
    result_profile = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/trig/profile/fake"
    )
    result_system = urllib.request.urlopen(
        "http://localhost/cblr/svc/op/trig/system/testbed"
    )

    # Assert
    assert expected_result == result_general.read().decode("utf-8")
    assert expected_result == result_profile.read().decode("utf-8")
    assert expected_result == result_system.read().decode("utf-8")


@pytest.mark.integration
def test_svc_yum(create_distro_profile_system: Tuple[str, str, str]):
    """
    Check that the Cobbler HTTP endpoint /yum/ is callable
    """
    # Arrange
    _ = create_distro_profile_system
    # Prepare expected result
    # expected_result = "TODO"

    # Act
    urllib.request.urlopen("http://localhost/cblr/svc/op/yum/profile/fake")
    urllib.request.urlopen("http://localhost/cblr/svc/op/yum/system/testbed")

    # Assert
    # FIXME endpoint not yet testable
