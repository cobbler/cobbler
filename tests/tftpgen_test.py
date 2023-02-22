"""
Tests that validate the functionallity of the module that is reponsible for generating the TFTP boot tree.
"""

import glob
import os
import pathlib
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
from cobbler.templar import Templar

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_copy_bootloaders(tmpdir: pathlib.Path, cobbler_api: CobblerAPI):
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


def test_copy_single_distro_file(cobbler_api: CobblerAPI):
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


def test_copy_single_distro_files(
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
    cobbler_api: CobblerAPI,
):
    # Arrange
    # Create fake files
    directory = create_kernel_initrd(fk_kernel, fk_initrd)
    (pathlib.Path(directory) / "images").mkdir()
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


@pytest.mark.skip("Test broken atm.")
def test_copy_single_image_files(
    cobbler_api: CobblerAPI, create_image: Callable[[], Image]
):
    # Arrange
    test_image = create_image()
    test_gen = tftpgen.TFTPGen(cobbler_api)
    expected_file = pathlib.Path(test_gen.bootloc) / "images2" / test_image.name

    # Act
    test_gen.copy_single_image_files(test_image)

    # Assert
    assert expected_file.exists()


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
    mock_write_pxe_file_s390 = mocker.patch.object(
        test_gen, "_write_all_system_files_s390"
    )
    mock_fs_helpers_rmfile = mocker.patch("cobbler.utils.filesystem_helpers.rmfile")
    mock_fs_helpers_mkdir = mocker.patch("cobbler.utils.filesystem_helpers.mkdir")
    mock_os_symlink = mocker.patch("os.symlink")

    # Act
    test_gen.write_all_system_files(test_system, result)

    # Assert
    assert mock_write_pxe_file_s390.call_count == 0
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
    test_distro = create_distro()
    test_distro.kernel_options = {
        "foobar1": "whatever",
        "autoyast": "http://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/this-is-a-long-string-that-need-to-be-splitted/zzzzzzzzzzzzzzzzz",
        "foobar2": "woohooo",
    }
    test_profile = create_profile(test_distro.name)
    test_system: System = create_system(profile_name=test_profile.name)  # type: ignore
    test_system.netboot_enabled = True
    test_image = create_image()
    test_gen = tftpgen.TFTPGen(cobbler_api)

    mocker.patch.object(test_system, "is_management_supported", return_value=True)
    open_mock = mocker.mock_open()
    open_mock.write = mocker.MagicMock()
    mocker.patch("builtins.open", open_mock)

    # Act
    test_gen._write_all_system_files_s390(
        test_distro, test_profile, test_image, test_system
    )

    # Assert - ensure generated parm file has fixed 80 characters format
    open_mock().write.assert_called()
    open_mock().write.assert_any_call(
        "foobar1=whatever \nautoyast=http://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/this-is-a-\nlong-string-that-need-to-be-splitted/zzzzzzzzzzzzzzzzz \nfoobar2=woohooo\n"
    )


def test_make_pxe_menu(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    metadata_mock = {
        "menu_items": "",
        "menu_labels": "",
    }
    mocker.patch.object(test_gen, "get_menu_items", return_value=metadata_mock)
    mocker.patch.object(test_gen, "_make_pxe_menu_pxe")
    mocker.patch.object(test_gen, "_make_pxe_menu_ipxe")
    mocker.patch.object(test_gen, "_make_pxe_menu_grub")

    # Act
    result = test_gen.make_pxe_menu()

    # Assert
    assert isinstance(result, dict)
    assert metadata_mock["pxe_timeout_profile"] == "local"


def test_get_menu_items(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    # Arrange
    expected_result = {"expected": "dict"}
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch.object(test_gen, "get_menu_level", return_value=expected_result)

    # Act
    result = test_gen.get_menu_items()

    # Assert
    assert result == expected_result


@pytest.mark.skip("Test broken atm.")
def test_get_submenus(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    # TODO: Mock self.menus
    mocker.patch.object(test_gen, "get_menu_level")

    # Act
    test_gen.get_submenus(None, {}, enums.Archs.X86_64)

    # Assert
    assert False


@pytest.mark.skip("Test broken atm.")
def test_get_profiles_menu(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    # FIXME: Mock self.profiles()
    mocker.patch.object(test_gen, "write_pxe_file")

    # Act
    test_gen.get_profiles_menu(None, {}, enums.Archs.X86_64)

    # Assert
    # TODO: Via metadata dict content
    assert False


@pytest.mark.skip("Test broken atm.")
def test_get_images_menu(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    # FIXME: Mock self.images()
    mocker.patch.object(test_gen, "write_pxe_file")

    # Act
    test_gen.get_images_menu(None, {}, enums.Archs.X86_64)

    # Assert
    # TODO: Via metadata dict content
    assert False


@pytest.mark.skip("Test broken atm.")
def test_get_menu_level(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    # FIXME: Mock self.settings.boot_loader_conf_template_dir - maybe?
    # FIXME: Mock open() for template loading and writing
    mocker.patch.object(test_gen, "get_submenus")
    mocker.patch.object(test_gen, "get_profiles_menu")
    mocker.patch.object(test_gen, "get_images_menu")
    test_gen.templar = mocker.MagicMock(spec=Templar, autospec=True)

    # Act
    result = test_gen.get_menu_level()

    # Assert
    assert False


@pytest.mark.skip("Test broken atm.")
def test_write_pxe_file(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    # FIXME: Mock self.settings.to_dict() - maybe?
    # FIXME: Mock self.settings.boot_loader_conf_template_dir - maybe?
    mocker.patch.object(test_gen, "build_kernel")
    mocker.patch.object(test_gen, "build_kernel_options")

    # Act
    result = test_gen.write_pxe_file(
        "", None, None, None, enums.Archs.X86_64, None, {}, ""
    )

    # Assert
    assert False


@pytest.mark.skip("Test broken atm.")
def test_build_kernel(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch("cobbler.utils.blender", return_value={})

    # Act
    test_gen.build_kernel({}, None, None, None, None, "pxe")

    # Assert
    assert False


@pytest.mark.skip("Test broken atm.")
def test_build_kernel_options(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch("cobbler.utils.blender", return_value={})
    mocker.patch("cobbler.utils.dict_to_string", return_value="")
    # FIXME: Mock self.settings.server - maybe?
    # FIXME: Mock self.settings.convert_server_to_ip - maybe?
    test_gen.templar = mocker.MagicMock(spec=Templar, autospec=True)

    # Act
    test_gen.build_kernel_options(None, None, None, None, enums.Archs.X86_64, "")

    # Assert
    assert False


@pytest.mark.skip("Test broken atm.")
def test_write_templates(
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
):
    # Arrange
    test_distro = create_distro()
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch("cobbler.utils.blender", return_value={})
    test_gen.templar = mocker.MagicMock(spec=Templar, autospec=True)
    # FIXME: Mock self.bootloc
    # FIXME: Mock self.settings.webdir - maybe?
    # FIXME: Mock open()

    # Act
    result = test_gen.write_templates(test_distro, False, "TODO")

    # Assert
    assert False


@pytest.mark.skip("Test broken atm.")
def test_generate_ipxe(
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    test_gen = tftpgen.TFTPGen(cobbler_api)
    expected_result = "test"
    mock_write_pxe_file = mocker.patch.object(
        test_gen, "write_pxe_file", return_value=expected_result
    )

    # Act
    result = test_gen.generate_ipxe("profile", test_profile.name)

    # Assert
    mock_write_pxe_file.assert_called_with(
        None, None, test_profile, test_distro, enums.Archs.X86_64, None, format="ipxe"
    )
    assert result == expected_result


@pytest.mark.skip("Test broken atm.")
def test_generate_bootcfg(
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    test_gen = tftpgen.TFTPGen(cobbler_api)
    # TODO: Mock self.api.find_system/find_profile()
    mocker.patch("cobbler.utils.blender", return_value={})
    # FIXME: Mock self.settings.boot_loader_conf_template_dir - maybe?
    # FIXME: Mock self.settings.server - maybe?
    # FIXME: Mock self.settings.http_port - maybe?
    mocker.patch.object(test_gen, "build_kernel_options")
    mocker.patch("builtins.open", mocker.mock_open(read_data="test"))
    test_gen.templar = mocker.MagicMock(spec=Templar, autospec=True)

    # Act
    result = test_gen.generate_bootcfg("profile", test_profile.name)

    # Assert
    assert False


def test_generate_script(
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch("cobbler.utils.blender", return_value={})
    mocker.patch("builtins.open", mocker.mock_open(read_data="test"))
    mocker.patch("os.path.exists", return_value=True)
    test_gen.templar = mocker.MagicMock(spec=Templar, autospec=True)

    # Act
    result = test_gen.generate_script("profile", test_profile.name, "script_name.xml")

    # Assert
    assert isinstance(result, mocker.MagicMock)
    test_gen.templar.render.assert_called_with(
        "test", {"img_path": f"/images/{test_distro.name}"}, None
    )


def test_generate_windows_initrd(cobbler_api: CobblerAPI):
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    result = test_gen._build_windows_initrd("custom_loader", "my_custom_loader", "ipxe")

    # Assert
    assert result == "--name custom_loader my_custom_loader custom_loader"


def test_generate_initrd(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch.object(test_gen, "_build_windows_initrd", return_value="Test")
    input_metadata = {
        "initrd": [],
        "bootmgr": "True",
        "bcd": "True",
        "winpe": "True",
    }
    expected_result = []

    # Act
    result = test_gen._generate_initrd(input_metadata, "", "", "ipxe")

    # Assert
    assert result == expected_result


@pytest.fixture(scope="function")
def cleanup_tftproot():
    """
    Fixture that is responsible for cleaning up for ESXi generated content.
    """
    yield
    pathlib.Path("/srv/tftpboot/esxi/example.txt").unlink()


def test_write_bootcfg_file(
    mocker: "MockerFixture",
    cleanup_tftproot: Callable[[], None],
    cobbler_api: CobblerAPI,
):
    # Arrange
    expected_result = "generated bootcfg"
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch.object(test_gen, "generate_bootcfg", return_value=expected_result)

    # Act
    result = test_gen._write_bootcfg_file("profile", "test", "example.txt")

    # Assert
    assert result == expected_result
    assert pathlib.Path("/srv/tftpboot/esxi/example.txt").is_file()
