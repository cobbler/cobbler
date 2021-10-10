import glob
import os
import pytest
import shutil

from cobbler.api import CobblerAPI
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler import tftpgen
from cobbler.items.distro import Distro
from tests.conftest import does_not_raise

# Tests copying the bootloaders from the bootloaders_dir (setting specified in /etc/cobbler/settings.yaml) to the tftpboot directory.
def test_copy_bootloaders(tmpdir):
    # Instantiate TFTPGen class with collection_mgr parameter
    test_api = CobblerAPI()
    test_collection_mgr = CollectionManager(test_api)
    generator = tftpgen.TFTPGen(test_collection_mgr)

    # Arrange
    ## Create temporary bootloader files using tmpdir fixture
    file_contents = "I am a bootloader"
    sub_path = tmpdir.mkdir("loaders")
    sub_path.join("bootloader1").write(file_contents)
    sub_path.join("bootloader2").write(file_contents)

    ## Copy temporary bootloader files from tmpdir to expected source directory
    for file in glob.glob(str(sub_path + "/*")):
        bootloader_src = "/var/lib/cobbler/loaders/"
        shutil.copy(file, bootloader_src + file.split("/")[-1])

    # Act
    generator.copy_bootloaders("/srv/tftpboot")

    # Assert
    assert os.path.isfile("/srv/tftpboot/bootloader1")
    assert os.path.isfile("/srv/tftpboot/bootloader2")

# Tests copy_single_distro_file() method using a sample initrd file pulled from Centos 8
def test_copy_single_distro_file():
    # Instantiate TFTPGen class with collection_mgr parameter
    test_api = CobblerAPI()
    test_collection_mgr = CollectionManager(test_api)
    generator = tftpgen.TFTPGen(test_collection_mgr)

    # Arrange
    distro_file = "/code/tests/test_data/dummy_initramfs"
    distro_dir = "/srv/tftpboot/images/"
    symlink_ok = True
    initramfs_dst_path = "/srv/tftpboot/images/dummy_initramfs"

    # Act
    generator.copy_single_distro_file(distro_file, distro_dir, symlink_ok)

    # Assert
    assert os.path.isfile(initramfs_dst_path)


def test_copy_single_distro_files(create_kernel_initrd, fk_initrd, fk_kernel):
    # Arrange
    # Create fake files
    directory = create_kernel_initrd(fk_kernel, fk_initrd)
    # Create test API        
    test_api = CobblerAPI()
    # Get Collection Manager used by the API
    test_collection_mgr = test_api._collection_mgr
    # Create a test Distro
    test_distro = Distro(test_api)
    test_distro.name = "test_copy_single_distro_files"
    test_distro.kernel = str(os.path.join(directory, fk_kernel))
    test_distro.initrd = str(os.path.join(directory, fk_initrd))
    # Add test distro to the API
    test_api.add_distro(test_distro)
    # Create class under test
    test_gen = tftpgen.TFTPGen(test_collection_mgr)

    # Act
    test_gen.copy_single_distro_files(test_distro, directory, False)

    # Assert that path created by function under test is actually there
    result_kernel = os.path.join(directory, "images", test_distro.name, fk_kernel)
    result_initrd = os.path.join(directory, "images", test_distro.name, fk_initrd)
    assert os.path.exists(result_kernel)
    assert os.path.exists(result_initrd)
