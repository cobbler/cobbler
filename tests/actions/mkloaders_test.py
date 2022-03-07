import pathlib
import subprocess

import pytest

import cobbler.actions.mkloaders
from cobbler.actions import mkloaders


def test_grubimage_object(cobbler_api):
    # Arrange & Act
    test_image_creator = mkloaders.MkLoaders(cobbler_api)

    # Assert
    assert isinstance(test_image_creator, mkloaders.MkLoaders)
    assert str(test_image_creator.syslinux_folder) == "/usr/share/syslinux"


def test_grubimage_run(cobbler_api, mocker):
    # Arrange
    test_image_creator = mkloaders.MkLoaders(cobbler_api)
    mocker.patch("cobbler.actions.mkloaders.symlink", spec=cobbler.actions.mkloaders.symlink)
    mocker.patch("cobbler.actions.mkloaders.mkimage", spec=cobbler.actions.mkloaders.mkimage)

    # Act
    test_image_creator.run()

    # Assert
    # On a full install: 3 common formats, 4 syslinux links and 9 bootloader formats
    # In our test container we have: shim (1x), ipxe (1x), syslinux v4 (3x) and 3 grubs (4x)
    # On GH we have: shim (1x), ipxe (1x), syslinux v4 (3x) and 3 grubs (3x)
    assert mkloaders.symlink.call_count == 8
    # In our test container we have: x86_64, arm64-efi, i386-efi & i386-pc-pxe
    # On GH we have: x86_64, i386-efi & i386-pc-pxe
    assert mkloaders.mkimage.call_count == 3


def test_mkimage(mocker):
    # Arrange
    mkimage_args = {
        "image_format": "grubx64.efi",
        "image_filename": pathlib.Path("/var/cobbler/loaders/grub/grubx64.efi"),
        "modules": ["btrfs", "ext2", "luks", "serial"],
    }
    mocker.patch("cobbler.actions.mkloaders.subprocess.run", spec=subprocess.run)

    # Act
    mkloaders.mkimage(**mkimage_args)

    # Assert
    mkloaders.subprocess.run.assert_called_once_with(
        [
            "grub2-mkimage",
            "--format",
            mkimage_args["image_format"],
            "--output",
            str(mkimage_args["image_filename"]),
            "--prefix=",
            *mkimage_args["modules"],
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


def test_symlink_link_exists(tmp_path):
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


def test_symlink_target_missing(tmp_path):
    # Arrange
    target = tmp_path / "target"
    link = tmp_path / "link"

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        mkloaders.symlink(target, link)


def test_get_syslinux_version(mocker):
    # Arrange
    mocker.patch(
        "cobbler.actions.mkloaders.subprocess.run",
        autospec=True,
        return_value=subprocess.CompletedProcess(
            "",
            0,
            stdout="syslinux 4.04  Copyright 1994-2011 H. Peter Anvin et al"
        )
    )

    # Act
    result = mkloaders.get_syslinux_version()

    # Assert
    assert result == 4
