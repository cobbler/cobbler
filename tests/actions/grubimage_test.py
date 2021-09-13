import pathlib
import subprocess

import pytest

import cobbler.actions.grubimage
from cobbler.actions import grubimage
from cobbler.api import CobblerAPI


@pytest.fixture()
def api():
    return CobblerAPI()


def test_grubimage_object(api):
    # Arrange & Act
    test_image_creator = grubimage.GrubImage(api)

    # Assert
    assert isinstance(test_image_creator, grubimage.GrubImage)
    assert str(test_image_creator.syslinux_dir) == "/usr/share/syslinux"


def test_grubimage_run(api, mocker):
    # Arrange
    test_image_creator = grubimage.GrubImage(api)
    mocker.patch("cobbler.actions.grubimage.symlink", spec=cobbler.actions.grubimage.symlink)
    mocker.patch("cobbler.actions.grubimage.mkimage", spec=cobbler.actions.grubimage.mkimage)

    # Act
    test_image_creator.run()

    # Assert
    # 3 common formats, 4 syslinux links and 9 common bootloader formats
    assert grubimage.symlink.call_count == 16
    # 9 common bootloader formats
    assert grubimage.mkimage.call_count == 9


def test_mkimage(mocker):
    # Arrange
    mkimage_args = {
        "image_format": "grubx64.efi",
        "image_filename": pathlib.Path("/var/cobbler/loaders/grub/grubx64.efi"),
        "modules": ["btrfs", "ext2", "luks", "serial"],
    }
    mocker.patch("cobbler.actions.grubimage.subprocess.run", spec=subprocess.run)

    # Act
    grubimage.mkimage(**mkimage_args)

    # Assert
    grubimage.subprocess.run.assert_called_once_with(
        [
            "grub2-mkimage",
            "--format",
            mkimage_args["image_format"],
            "--output",
            str(mkimage_args["image_filename"]),
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
    grubimage.symlink(target, link)

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
        grubimage.symlink(link, target, skip_existing=False)

    # Assert: must not raise an exception
    grubimage.symlink(link, target, skip_existing=True)


def test_symlink_target_missing(tmp_path):
    # Arrange
    target = tmp_path / "target"
    link = tmp_path / "link"

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        grubimage.symlink(target, link)
