import glob
import os
import shutil
from typing import TYPE_CHECKING, Any, Callable, List, Tuple

import pytest

from cobbler import enums
from cobbler import tftpgen
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.profile import Profile
from cobbler.items.system import System

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


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


def test_copy_single_distro_files(
    create_kernel_initrd,
    fk_initrd,
    fk_kernel,
    cobbler_api,
    cleanup_copy_single_distro_files,
):
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


@pytest.fixture()
def setup_test_write_all_system_files(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str, str, str], System],
):
    """
    Setup fixture for "test_write_all_system_files".
    """
    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    test_system: System = create_system(profile_name=test_profile.name)  # type: ignore
    test_gen = tftpgen.TFTPGen(cobbler_api)
    return test_system, test_gen


@pytest.mark.parametrize(
    "mock_is_management_supported,mock_get_config_filename,expected_pxe_file,expected_rmfile,expected_mkdir,expected_symlink",
    [
        (True, ["A", "B"], 2, 1, 1, 1),
        (True, ["A", None], 1, 0, 0, 0),
        (True, [None, "B"], 1, 1, 1, 1),
        # TODO: Add image based scenario
        (False, ["A", "B"], 0, 2, 0, 0),
        (False, ["A", None], 0, 1, 0, 0),
    ],
)
def test_write_all_system_files(
    mocker: "MockerFixture",
    setup_test_write_all_system_files: Tuple[System, tftpgen.TFTPGen],
    mock_is_management_supported: bool,
    mock_get_config_filename: List[Any],
    expected_pxe_file: int,
    expected_rmfile: int,
    expected_mkdir: int,
    expected_symlink: int,
):
    """
    Test that asserts if the "write_all_system_files" subroutine is working as intended.

    Two main scenarios must be tested for

    * normal hardware and
    * S390(X) hardware

    as they generate a different set of files. This method handles only GRUB and pxelinux.

    ESXI bootloader and iPXE generation is handled in a different test.
    """
    # Arrange
    test_system, test_gen = setup_test_write_all_system_files
    result = {}
    mocker.patch.object(
        test_system,
        "is_management_supported",
        return_value=mock_is_management_supported,
    )
    mocker.patch.object(
        test_system, "get_config_filename", side_effect=mock_get_config_filename
    )
    mock_write_pxe_file = mocker.patch.object(test_gen, "write_pxe_file")
    mock_fs_helpers_rmfile = mocker.patch("cobbler.utils.rmfile")
    mock_fs_helpers_mkdir = mocker.patch("cobbler.utils.mkdir")
    mock_os_symlink = mocker.patch("os.symlink")

    # Act
    test_gen.write_all_system_files(test_system, result)

    # Assert
    assert mock_write_pxe_file.call_count == expected_pxe_file
    assert mock_fs_helpers_rmfile.call_count == expected_rmfile
    assert mock_fs_helpers_mkdir.call_count == expected_mkdir
    assert mock_os_symlink.call_count == expected_symlink


def test_write_all_system_files_s390(
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str, str, str], System],
    create_image: Callable[[], Image],
):
    """
    Test that asserts if the generated kernel options are longer then 79 character we insert a newline for S390X.
    """
    # Arrange
    result = {}
    test_distro = create_distro()
    test_distro.arch = enums.Archs.S390X
    test_distro.kernel_options = {
        "foobar1": "whatever",
        "autoyast": "http://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/this-is-a-long-string-that-need-to-be-splitted/zzzzzzzzzzzzzzzzz",
        "foobar2": "woohooo",
    }
    test_profile = create_profile(test_distro.name)
    test_system = create_system(profile_name=test_profile.name)
    test_system.netboot_enabled = True
    test_image = create_image()
    test_gen = tftpgen.TFTPGen(cobbler_api)

    mocker.patch.object(test_system, "is_management_supported", return_value=True)
    open_mock = mocker.mock_open()
    open_mock.write = mocker.MagicMock()
    mocker.patch("builtins.open", open_mock)

    # Act
    test_gen.write_all_system_files(test_system, result)

    # Assert - ensure generated parm file has fixed 80 characters format
    open_mock().write.assert_called()
    open_mock().write.assert_any_call(
        "foobar1=whatever \nautoyast=http://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/this-is-a-\nlong-string-that-need-to-be-splitted/zzzzzzzzzzzzzzzzz \nfoobar2=woohooo\n"
    )
