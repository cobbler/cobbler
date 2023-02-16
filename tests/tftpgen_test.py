import glob
import os
import pathlib
import shutil

import pytest

from cobbler import enums
from cobbler import tftpgen
from cobbler.items.distro import Distro
from cobbler.templar import Templar


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
def test_copy_single_image_files(cobbler_api, create_image):
    # Arrange
    test_image = create_image()
    test_gen = tftpgen.TFTPGen(cobbler_api)
    expected_file = pathlib.Path(test_gen.bootloc) / "images2" / test_image.name

    # Act
    test_gen.copy_single_image_files(test_image)

    # Assert
    assert expected_file.exists()


@pytest.mark.skip("Test broken atm.")
def test_write_all_system_files(
    cobbler_api, create_distro, create_profile, create_system
):
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    test_system = create_system(profile_name=test_profile.name)
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    test_gen.write_all_system_files(test_system, None)

    # Assert
    assert False


def test_write_all_system_files_s390(
    mocker, cobbler_api, create_distro, create_profile, create_system, create_image
):

    # Arrange
    test_distro = create_distro()
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
    test_gen._write_all_system_files_s390(
        test_distro, test_profile, test_image, test_system
    )

    # Assert - ensure generated parm file has fixed 80 characters format
    open_mock().write.assert_called()
    open_mock().write.assert_any_call(
        "foobar1=whatever \nautoyast=http://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/this-is-a-\nlong-string-that-need-to-be-splitted/zzzzzzzzzzzzzzzzz \nfoobar2=woohooo\n"
    )


def test_make_pxe_menu(mocker, cobbler_api):
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


def test_get_menu_items(mocker, cobbler_api):
    # Arrange
    expected_result = {"expected": "dict"}
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch.object(test_gen, "get_menu_level", return_value=expected_result)

    # Act
    result = test_gen.get_menu_items()

    # Assert
    assert result == expected_result


@pytest.mark.skip("Test broken atm.")
def test_get_submenus(mocker, cobbler_api):
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    # TODO: Mock self.menus
    mocker.patch.object(test_gen, "get_menu_level")

    # Act
    test_gen.get_submenus(None, {}, enums.Archs.X86_64)

    # Assert
    assert False


@pytest.mark.skip("Test broken atm.")
def test_get_profiles_menu(mocker, cobbler_api):
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
def test_get_images_menu(mocker, cobbler_api):
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
def test_get_menu_level(mocker, cobbler_api):
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
def test_write_pxe_file(mocker, cobbler_api):
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
def test_build_kernel(mocker, cobbler_api):
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch("cobbler.utils.blender", return_value={})

    # Act
    test_gen.build_kernel({}, None, None, None, None, "pxe")

    # Assert
    assert False


@pytest.mark.skip("Test broken atm.")
def test_build_kernel_options(mocker, cobbler_api):
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
def test_write_templates(mocker, cobbler_api, create_distro):
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
def test_generate_ipxe(mocker, cobbler_api, create_distro, create_profile):
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
def test_generate_bootcfg(mocker, cobbler_api, create_distro, create_profile):
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


def test_generate_script(mocker, cobbler_api, create_distro, create_profile):
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


def test_generate_windows_initrd(cobbler_api):
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    result = test_gen._build_windows_initrd("custom_loader", "my_custom_loader", "ipxe")

    # Assert
    assert result == "--name custom_loader my_custom_loader custom_loader"


def test_generate_initrd(mocker, cobbler_api):
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
    yield
    pathlib.Path("/srv/tftpboot/esxi/example.txt").unlink()


def test_write_bootcfg_file(mocker, cleanup_tftproot, cobbler_api):
    # Arrange
    expected_result = "generated bootcfg"
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch.object(test_gen, "generate_bootcfg", return_value=expected_result)

    # Act
    result = test_gen._write_bootcfg_file("profile", "test", "example.txt")

    # Assert
    assert result == expected_result
    assert pathlib.Path("/srv/tftpboot/esxi/example.txt").is_file()
