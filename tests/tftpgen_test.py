import glob
import os
import shutil

import pytest

from cobbler import tftpgen
from cobbler.items.distro import Distro


def test_copy_bootloaders(tmpdir, cobbler_api):
    """
    Tests copying the bootloaders from the bootloaders_dir (setting specified in /etc/cobbler/settings.yaml) to the
    tftpboot directory.
    """
    # Instantiate TFTPGen class with collection_mgr parameter
    generator = tftpgen.TFTPGen(cobbler_api)

    # Arrange
    # Create temporary bootloader files using tmpdir fixture
    file_contents = "I am a bootloader"
    sub_path = tmpdir.mkdir("loaders")
    sub_path.join("bootloader1").write(file_contents)
    sub_path.join("bootloader2").write(file_contents)

    # Copy temporary bootloader files from tmpdir to expected source directory
    for file in glob.glob(str(sub_path + "/*")):
        bootloader_src = "/var/lib/cobbler/loaders/"
        shutil.copy(file, bootloader_src + file.split("/")[-1])

    # Act
    generator.copy_bootloaders("/srv/tftpboot")

    # Assert
    assert os.path.isfile("/srv/tftpboot/bootloader1")
    assert os.path.isfile("/srv/tftpboot/bootloader2")


def test_copy_single_distro_file(cobbler_api):
    """
    Tests copy_single_distro_file() method using a sample initrd file pulled from CentOS 8
    """
    # Instantiate TFTPGen class with collection_mgr parameter
    generator = tftpgen.TFTPGen(cobbler_api)

    # Arrange
    distro_file = "/code/tests/test_data/dummy_initramfs"
    distro_dir = "/srv/tftpboot/images/"
    symlink_ok = True
    initramfs_dst_path = "/srv/tftpboot/images/dummy_initramfs"

    # Act
    generator.copy_single_distro_file(distro_file, distro_dir, symlink_ok)

    # Assert
    assert os.path.isfile(initramfs_dst_path)


@pytest.fixture(autouse=True)
def cleanup_copy_single_distro_files(cobbler_api):
    yield
    cobbler_api.remove_distro("test_copy_single_distro_files")


def test_copy_single_distro_files(create_kernel_initrd, fk_initrd, fk_kernel, cobbler_api, cleanup_copy_single_distro_files):
    # Arrange
    # Create fake files
    directory = create_kernel_initrd(fk_kernel, fk_initrd)
    # Create a test Distro
    test_distro = Distro(cobbler_api)
    test_distro.name = "test_copy_single_distro_files"
    test_distro.kernel = str(os.path.join(directory, fk_kernel))
    test_distro.initrd = str(os.path.join(directory, fk_initrd))
    # Add test distro to the API
    cobbler_api.add_distro(test_distro)
    # Create class under test
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    test_gen.copy_single_distro_files(test_distro, directory, False)

    # Assert that path created by function under test is actually there
    result_kernel = os.path.join(directory, "images", test_distro.name, fk_kernel)
    result_initrd = os.path.join(directory, "images", test_distro.name, fk_initrd)
    assert os.path.exists(result_kernel)
    assert os.path.exists(result_initrd)
