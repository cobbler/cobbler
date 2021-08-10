import pytest
import subprocess
import pathlib
from cobbler.actions import grubimage
from cobbler.api import CobblerAPI


@pytest.fixture()
def api():
    return CobblerAPI()


def test_mkimage(mocker):
    mkimage_args = {
        "image_format": "grubx64.efi",
        "image_filename": pathlib.Path("/var/cobbler/loaders/grub/grubx64.efi"),
        "modules": ["btrfs", "ext2", "luks", "serial"],
    }
    mocker.patch("cobbler.actions.grubimage.subprocess.run", spec=subprocess.run)
    grubimage.mkimage(**mkimage_args)

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
    target = tmp_path / "target"
    target.touch()
    link = tmp_path / "link"

    grubimage.symlink(target, link)
    assert link.exists()
    assert link.is_symlink()
    assert link.resolve() == target


def test_symlink_link_exists(tmp_path):
    target = tmp_path / "target"
    target.touch()
    link = tmp_path / "link"
    link.touch()

    with pytest.raises(FileExistsError):
        grubimage.symlink(link, target, skip_existing=False)

    # must not raise an exception
    grubimage.symlink(link, target, skip_existing=True)


def test_symlink_target_missing(tmp_path):
    target = tmp_path / "target"
    link = tmp_path / "link"

    with pytest.raises(FileNotFoundError):
        grubimage.symlink(target, link)
