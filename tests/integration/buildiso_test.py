"""
Check that Cobbler is able to build customized ISOs by the "cobbler buildiso" command with the addition of the
airgapped flag
"""

import pathlib
import shutil
import subprocess
import urllib.request
from typing import Any, Generator

import pytest

from cobbler.remote import CobblerXMLRPCInterface

from tests.integration.conftest import WaitTaskEndType


@pytest.fixture(name="isos_folder", scope="session")
def fixture_isos_folder(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[pathlib.Path, None, None]:
    """
    TODO
    """
    isos_directory = tmp_path_factory.mktemp("isos")
    yield isos_directory
    shutil.rmtree(isos_directory, ignore_errors=True)


@pytest.fixture(name="iso_mount_point")
def fixture_iso_mount_point(
    isos_folder: pathlib.Path,
) -> Generator[pathlib.Path, None, None]:
    """
    TODO
    """
    mount_point = isos_folder / "leap-mp"
    mount_point.mkdir()
    yield mount_point
    mount_point.rmdir()


@pytest.fixture(name="buildiso_cleanup")
def fixture_buildiso_cleanup(
    iso_mount_point: pathlib.Path,
) -> Generator[None, None, None]:
    """
    TODO
    """
    yield
    subprocess.call(
        f"mountpoint -q {str(iso_mount_point)} && umount {str(iso_mount_point)}",
        shell=True,
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "flavor",
    [
        "airgapped",
        "full",
        "net",
        "non-standard-directory",
        "ppc64le",
    ],
)
def test_buildiso_integration(
    flavor: str,
    tmp_path: pathlib.Path,
    remote: CobblerXMLRPCInterface,
    token: str,
    wait_task_end: WaitTaskEndType,
    iso_mount_point: pathlib.Path,
    buildiso_cleanup: Any,
    isos_folder: pathlib.Path,
):
    """
    TODO
    """
    # Arrange
    if flavor == "ppc64le":
        filename = "openSUSE-Leap-15.3-DVD-ppc64le-Current.iso"
        iso_downloaded_path = isos_folder / filename
        if not iso_downloaded_path.exists():
            urllib.request.urlretrieve(
                f"https://download.opensuse.org/distribution/leap/15.3/iso/{filename}",
                str(iso_downloaded_path),
            )
            print("ISO downloaded")
        else:
            print("ISO already present")
    else:
        filename = "openSUSE-Leap-15.3-DVD-x86_64-Current.iso"
        iso_downloaded_path = isos_folder / filename
        if not iso_downloaded_path.exists():
            urllib.request.urlretrieve(
                f"https://download.opensuse.org/distribution/leap/15.3/iso/{filename}",
                str(iso_downloaded_path),
            )
            print("ISO downloaded")
        else:
            print("ISO already present")
    mount_point = iso_mount_point
    if flavor == "ppc64le":
        subprocess.call(
            f'mount -o loop,ro "{str(iso_downloaded_path)}" "{str(mount_point)}"',
            shell=True,
        )
    else:
        subprocess.call(
            f'mount -o loop,ro "{str(iso_downloaded_path)}" "{str(mount_point)}"',
            shell=True,
        )
    print("ISO mounted")
    tid = remote.background_import({"name": "leap", "path": str(mount_point)}, token)
    wait_task_end(tid, remote)
    print("ISO imported")
    if flavor == "ppc64le":
        # Install grub2-ppc64le and run cobbler mkloaders
        command = "zypper ar https://download.opensuse.org/ports/ppc/tumbleweed/repo/oss/ tumbleweed_os_ppc64le"
        command += " && zypper ref"
        command += " && zypper in -y grub2-powerpc-ieee1275"
        subprocess.call(command, shell=True)
        tid = remote.background_mkloaders({}, token)
        wait_task_end(tid, remote)
    sid = remote.new_system(token)
    remote.modify_system(sid, "name", "testbed", token)
    if flavor == "ppc64le":
        remote.modify_system(sid, "profile", "leap-ppc64le", token)
    else:
        remote.modify_system(sid, "profile", "leap-x86_64", token)
    remote.save_system(sid, token, "new")
    print("Testsystem created")

    # Tmp: Create "/var/cache/cobbler" because it does not exist per default
    pathlib.Path("/var/cache/cobbler/buildiso").mkdir(exist_ok=True, parents=True)

    # Act
    iso_path = str(tmp_path / "autoinst.iso")
    if flavor == "airgapped":
        tid = remote.background_buildiso(
            {
                "airgapped": True,
                "distro": "leap-x86_64",
                "source": str(mount_point),
                "buildisodir": "/var/cache/cobbler/buildiso",
                "iso": iso_path,
            },
            token,
        )
    elif flavor == "full":
        tid = remote.background_buildiso(
            {
                "standalone": True,
                "distro": "leap-x86_64",
                "source": str(mount_point),
                "buildisodir": "/var/cache/cobbler/buildiso",
                "iso": iso_path,
            },
            token,
        )
    elif flavor == "net":
        tid = remote.background_buildiso(
            {
                "distro": "leap-x86_64",
                "buildisodir": "/var/cache/cobbler/buildiso",
                "iso": iso_path,
            },
            token,
        )
    elif flavor == "non-standard-directory":
        custom_mount_point = pathlib.Path("/var/cache/cobbler/buildiso-test")
        custom_mount_point.mkdir(exist_ok=True)
        tid = remote.background_buildiso(
            {
                "distro": "leap-x86_64",
                "buildisodir": str(custom_mount_point),
                "iso": iso_path,
            },
            token,
        )
    elif flavor == "ppc64le":
        tid = remote.background_buildiso(
            {
                "profile": "leap-ppc64le",
                "distro": "leap-ppc64le",
                "source": str(mount_point),
                "buildisodir": "/var/cache/cobbler/buildiso",
                "iso": iso_path,
            },
            token,
        )
    else:
        pytest.fail("Unknown flavor")
    wait_task_end(tid, remote)
    print("ISO built")

    # Assert
    # Check ISO exists & is bootable
    if flavor == "ppc64le":
        expected_result = "MBR CHRP cyl-align-off\n"
        result = subprocess.check_output(
            rf"xorriso -indev {iso_path} -toc 2>/dev/null | sed -En 's/^Boot record.* \(system area only\) , (.*)$/\\1/p'",
            shell=True,
        )
    else:
        expected_result = "BIOS\nUEFI\n"
        result = subprocess.check_output(
            f"xorriso -indev {iso_path} -report_el_torito 2>/dev/null | awk '/^El Torito boot img[[:space:]]+:[[:space:]]+[0-9]+[[:space:]]+[a-zA-Z]+[[:space:]]+y/{{print $7}}'",
            shell=True,
        )

    assert result.decode(encoding="UTF-8") == expected_result
