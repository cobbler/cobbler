"""
Tests that validate the functionality of the module that is responsible for creating the networked bootloaders.
"""

import pathlib
import re
import subprocess
from typing import TYPE_CHECKING

import pytest

from cobbler.actions import mkloaders
from cobbler.api import CobblerAPI

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_grubimage_object(cobbler_api: CobblerAPI):
    # Arrange & Act
    test_image_creator = mkloaders.MkLoaders(cobbler_api)

    # Assert
    assert isinstance(test_image_creator, mkloaders.MkLoaders)
    assert str(test_image_creator.syslinux_folder) == "/usr/share/syslinux"


def test_grubimage_run(cobbler_api: CobblerAPI, mocker: "MockerFixture"):
    # Arrange
    test_image_creator = mkloaders.MkLoaders(cobbler_api)
    mocker.patch("cobbler.actions.mkloaders.symlink", spec=mkloaders.symlink)
    mocker.patch("cobbler.actions.mkloaders.mkimage", spec=mkloaders.mkimage)

    # Act
    test_image_creator.run()

    # Assert
    # pylint: disable=no-member
    # On a full install: 3 common formats, 5 syslinux links and 9 bootloader formats
    # In our test container we have: shim (2x), ipxe (1x), syslinux v4 (5x) and 3 grubs (4x)
    # On GH we have: shim (2x), ipxe (1x), syslinux v4 (5x) and 3 grubs (3x)
    assert mkloaders.symlink.call_count == 11  # type: ignore[reportFunctionMemberAccess]
    # In our test container we have: x86_64, arm64-efi, i386-efi & i386-pc-pxe
    # On GH we have: x86_64, i386-efi & i386-pc-pxe
    assert mkloaders.mkimage.call_count == 3  # type: ignore[reportFunctionMemberAccess]


def test_mkimage(mocker: "MockerFixture"):
    # Arrange
    mkimage_args = {
        "image_format": "grubx64.efi",
        "image_filename": pathlib.Path("/var/cobbler/loaders/grub/grubx64.efi"),
        "modules": ["btrfs", "ext2", "luks", "serial"],
    }
    mocker.patch("cobbler.actions.mkloaders.subprocess.run", spec=subprocess.run)

    # Act
    mkloaders.mkimage(**mkimage_args)  # type: ignore[reportArgumentType]

    # Assert
    # pylint: disable=no-member
    mkloaders.subprocess.run.assert_called_once_with(  # type: ignore[reportFunctionMemberAccess]
        [
            "grub2-mkimage",
            "--format",
            mkimage_args["image_format"],
            "--output",
            str(mkimage_args["image_filename"]),
            "--prefix=",
            *mkimage_args["modules"],  # type: ignore[reportGeneralTypeIssues]
        ],
        check=True,
    )


def test_symlink(tmp_path: pathlib.Path):
    # Arrange
    target = tmp_path / "target"
    target.touch()
    link = tmp_path / "link"

    # Run
    mkloaders.symlink(target, link)

    # Assert
    assert link.exists()
    assert link.is_symlink()
    assert link.resolve() == target


def test_find_file(tmp_path: pathlib.Path):
    # Arrange
    target = tmp_path / "target"
    target.mkdir()
    target_file = target / "file.txt"
    target_file.touch()
    file_regex = re.compile(r"file\.txt")
    invalid_file_regex = re.compile(r"file1\.txt")

    # Act
    valid_file = mkloaders.find_file(target, file_regex)
    invalid_file = mkloaders.find_file(target, invalid_file_regex)

    # Assert
    assert valid_file != None
    assert invalid_file == None


def test_symlink_link_exists(tmp_path: pathlib.Path):
    # Arrange
    target = tmp_path / "target"
    target.touch()
    link = tmp_path / "link"
    link.touch()

    # Act
    with pytest.raises(FileExistsError):
        mkloaders.symlink(link, target, skip_existing=False)

    # Assert: must not raise an exception
    mkloaders.symlink(link, target, skip_existing=True)


def test_symlink_target_missing(tmp_path: pathlib.Path):
    # Arrange
    target = tmp_path / "target"
    link = tmp_path / "link"

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        mkloaders.symlink(target, link)


def test_make_syslinux_deploys_linux_c32_without_libcom32_on_syslinux_4(
    cobbler_api: CobblerAPI, mocker: "MockerFixture", tmp_path: pathlib.Path
):
    """
    Regression test: syslinux 4.x's "linux.c32" is a statically self-contained COM32 module and does
    not depend on "libcom32.c32" (that dependency is new in syslinux 5's COM32R format, per
    https://wiki.syslinux.org/wiki/index.php?title=Library_modules). make_syslinux() used to gate the
    "linux.c32" symlink on the exact same "syslinux_version > 4 and libcom32.c32 exists" condition as
    the libcom32.c32 companion copy, so on a syslinux 4.x install "linux.c32" was never deployed at
    all even though it is present and usable standalone -- breaking any Windows/wimboot profile that
    chainloads via it.
    """
    # Arrange
    mocker.patch("cobbler.actions.mkloaders.get_syslinux_version", return_value=4)
    mocker.patch("cobbler.actions.mkloaders.utils.command_existing", return_value=True)
    mock_symlink = mocker.patch("cobbler.actions.mkloaders.symlink")
    test_mkloaders = mkloaders.MkLoaders(cobbler_api)
    syslinux_folder = tmp_path / "syslinux"
    syslinux_folder.mkdir()
    (syslinux_folder / "linux.c32").touch()
    # No libcom32.c32 present, matching a real syslinux 4.x install.
    test_mkloaders.syslinux_folder = syslinux_folder
    test_mkloaders.bootloaders_dir = tmp_path / "bootloaders"

    # Act
    test_mkloaders.make_syslinux()

    # Assert
    symlinked_names = {call.args[1].name for call in mock_symlink.call_args_list}
    assert "linux.c32" in symlinked_names
    assert "libcom32.c32" not in symlinked_names


def test_make_syslinux_skips_linux_c32_on_syslinux_5_without_libcom32(
    cobbler_api: CobblerAPI, mocker: "MockerFixture", tmp_path: pathlib.Path
):
    """
    Regression test: starting with syslinux 5, "linux.c32" depends on "libcom32.c32" (per
    https://wiki.syslinux.org/wiki/index.php?title=Library_modules). The fix for the syslinux 4.x case
    above must not drop this dependency gate entirely -- on a syslinux 5+ install missing
    "libcom32.c32" (e.g. a broken/partial install), "linux.c32" must NOT be symlinked, since it would
    be a non-functional module.
    """
    # Arrange
    mocker.patch("cobbler.actions.mkloaders.get_syslinux_version", return_value=5)
    mocker.patch("cobbler.actions.mkloaders.utils.command_existing", return_value=True)
    mock_symlink = mocker.patch("cobbler.actions.mkloaders.symlink")
    test_mkloaders = mkloaders.MkLoaders(cobbler_api)
    syslinux_folder = tmp_path / "syslinux"
    syslinux_folder.mkdir()
    (syslinux_folder / "linux.c32").touch()
    (syslinux_folder / "ldlinux.c32").touch()
    # No libcom32.c32 present, matching a broken/partial syslinux 5+ install.
    test_mkloaders.syslinux_folder = syslinux_folder
    test_mkloaders.bootloaders_dir = tmp_path / "bootloaders"

    # Act
    test_mkloaders.make_syslinux()

    # Assert
    symlinked_names = {call.args[1].name for call in mock_symlink.call_args_list}
    assert "linux.c32" not in symlinked_names
    assert "libcom32.c32" not in symlinked_names


def test_get_syslinux_version(mocker: "MockerFixture"):
    # Arrange
    mocker.patch(
        "cobbler.actions.mkloaders.subprocess.run",
        autospec=True,
        return_value=subprocess.CompletedProcess(
            "", 0, stdout="syslinux 4.04  Copyright 1994-2011 H. Peter Anvin et al"
        ),
    )

    # Act
    result = mkloaders.get_syslinux_version()

    # Assert
    assert result == 4
