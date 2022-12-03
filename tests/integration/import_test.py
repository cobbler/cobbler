"""
This package is responsible for ensuring that the various distros that can be imported into Cobbler.
"""

import pathlib
import shutil

import pytest

from cobbler.remote import CobblerXMLRPCInterface

from tests.integration.conftest import WaitTaskEndType


@pytest.mark.integration
@pytest.mark.parametrize(
    "breed,version",
    [
        ("debian", "bookworm"),
        ("debian", "bullseye"),
        ("freebsd", "freebsd11.4"),
        ("freebsd", "freebsd12.1"),
        ("freebsd", "freebsd12.2"),
        ("freebsd", "freebsd12.3"),
        ("freebsd", "freebsd13.0"),
        ("freebsd", "freebsd13.1"),
        ("freebsd", "freebsd13.2"),
        ("redhat", "cloudlinux7"),
        ("redhat", "cloudlinux8"),
        ("redhat", "cloudlinux9"),
        ("redhat", "fedora36"),
        ("redhat", "fedora37"),
        ("redhat", "fedora38"),
        ("redhat", "rhel10"),
        ("redhat", "rhel8"),
        ("redhat", "rhel9"),
        ("suse", "leapmicro5.3"),
        ("suse", "leapmicro5.4"),
        ("suse", "leapmicro5.5"),
        ("suse", "opensuse15.0"),
        ("suse", "opensuse15.1"),
        ("suse", "opensuse15.2"),
        ("suse", "opensuse15.3"),
        ("suse", "opensuse15.4"),
        ("suse", "opensuse15.5"),
        ("suse", "slemicro5.3"),
        ("suse", "slemicro5.4"),
        ("suse", "slemicro5.5"),
        ("suse", "sles15sp2"),
        ("suse", "sles15sp3"),
        ("suse", "sles15sp4"),
        ("suse", "sles15sp5"),
        ("ubuntu", "bionic"),
        ("ubuntu", "focal"),
        ("ubuntu", "groovy"),
        ("ubuntu", "hirsute"),
        ("ubuntu", "impish"),
        ("ubuntu", "jammy"),
        ("ubuntu", "kinetic"),
        ("ubuntu", "lunar"),
        ("ubuntu", "mantic"),
        ("ubuntu", "trusty"),
        ("ubuntu", "xenial"),
        ("vmware", "esxi70"),
        ("xen", "xenserver720"),
    ],
)
def test_import_iso(
    breed: str,
    version: str,
    listings_directory: pathlib.Path,
    tmp_path: pathlib.Path,
    remote: CobblerXMLRPCInterface,
    token: str,
    wait_task_end: WaitTaskEndType,
):
    """
    Check that Cobbler can import distros
    """
    # Arrange
    iso_directory = listings_directory / breed / version
    for iso in iso_directory.iterdir():
        if iso.is_dir() and iso.name.endswith(".iso"):
            iso_folder = tmp_path / iso.name
            iso_folder.mkdir()
            index = (iso / "index").read_text(encoding="UTF-8").splitlines()
            for file in index:
                file_location = iso_folder / file
                file_location.parent.mkdir(parents=True, exist_ok=True)
                file_location.touch(mode=0o0644)
            shutil.copytree(iso, iso_folder, dirs_exist_ok=True)

            # Act
            tid = remote.background_import(
                {"name": "imported", "path": str(iso_folder)}, token
            )
            wait_task_end(tid, remote)

            # Assert
            # TODO: Check if distro and profile are existing
