import pytest
import os.path

from cobbler.api import CobblerAPI
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler import tftpgen
from tests.conftest import does_not_raise

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
    assert os.path.isfile(initrd_dst_path)
