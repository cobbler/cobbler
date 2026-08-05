"""
Tests that validate the functionality of the module that is responsible for generating the TFTP boot tree.
"""

import glob
import os
import pathlib
import shutil
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Tuple, Union
from unittest.mock import PropertyMock

import pytest

from cobbler import enums, tftpgen, utils
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.profile import Profile
from cobbler.items.system import System
from cobbler.templates import Templar

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
    sub_path = tmpdir.mkdir("loaders")  # type: ignore
    sub_path.join("bootloader1").write(file_contents)  # type: ignore
    sub_path.join("bootloader2").write(file_contents)  # type: ignore

    # Copy temporary bootloader files from tmpdir to expected source directory
    for file in glob.glob(str(sub_path + "/*")):  # type: ignore
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
    """
    Test to verify that copying all files for a single Cobbler Distro is working as expected.
    """
    # Arrange
    # Create fake files
    directory = create_kernel_initrd(fk_kernel, fk_initrd)
    (pathlib.Path(directory) / "images").mkdir()
    # Create a test Distro
    test_distro = Distro(cobbler_api)
    test_distro.name = "test_copy_single_distro_files"  # type: ignore[method-assign]
    test_distro.kernel = str(os.path.join(directory, fk_kernel))  # type: ignore[method-assign]
    test_distro.initrd = str(os.path.join(directory, fk_initrd))  # type: ignore[method-assign]
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
    """
    Test to verify that the files for a given image can be copyied to the correct destinations.
    """
    # Arrange
    test_image = create_image()
    test_gen = tftpgen.TFTPGen(cobbler_api)
    expected_file = pathlib.Path(test_gen.bootloc) / "images2" / test_image.name

    # Act
    test_gen.copy_single_image_files(test_image)

    # Assert
    assert expected_file.exists()


@pytest.fixture(name="setup_test_write_all_system_files")
def fixture_setup_test_write_all_system_files(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
) -> Tuple[System, tftpgen.TFTPGen]:
    """
    Setup fixture for "test_write_all_system_files".
    """
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_gen = tftpgen.TFTPGen(cobbler_api)
    return test_system, test_gen


@pytest.mark.parametrize(
    "mock_is_management_supported,mock_get_config_filename,expected_pxe_file,expected_rmfile,expected_mkdir,expected_symlink",
    [
        (True, ["A", "B"], 2, 1, 1, 1),
        (True, ["A", None], 1, 1, 0, 0),
        (True, [None, "B"], 1, 1, 1, 1),
        # TODO: Add image based scenario
        (False, ["A", "B"], 0, 3, 0, 0),
        (False, ["A", None], 0, 2, 0, 0),
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
    result: Dict[str, Union[str, Dict[str, str]]] = {}
    mocker.patch.object(
        test_system,
        "is_management_supported",
        return_value=mock_is_management_supported,
    )
    mocker.patch.object(
        test_system, "get_config_filename", side_effect=mock_get_config_filename
    )
    mocker.patch.object(
        type(test_system),
        "boot_loaders",
        new_callable=PropertyMock,
        return_value=[enums.BootLoader.PXE, enums.BootLoader.GRUB],
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


def test_write_all_system_files_blender_call_count(
    mocker: "MockerFixture",
    setup_test_write_all_system_files: Tuple[System, tftpgen.TFTPGen],
):
    """
    Test that write_all_system_files() computes utils.blender() exactly once for the whole system,
    regardless of how many interfaces/boot loaders end up being written, and returns that result so
    callers (e.g. write_templates()) can reuse it instead of recomputing it.
    """
    # Arrange
    test_system, test_gen = setup_test_write_all_system_files
    # is_management_supported() requires a MAC/IP on at least one interface; without one,
    # write_all_system_files() never reaches the point where it needs blender() at all.
    test_system.interfaces["default"].mac_address = "random"
    blender_spy = mocker.spy(utils, "blender")

    # Act
    meta_blended = test_gen.write_all_system_files(test_system, {})

    # Assert
    assert blender_spy.call_count == 1
    assert meta_blended is not None


def test_write_templates_reuses_supplied_blended(
    mocker: "MockerFixture",
    setup_test_write_all_system_files: Tuple[System, tftpgen.TFTPGen],
):
    """
    Test that write_templates() does not call utils.blender() again when a caller already supplies one,
    even when the object has template_files to render.
    """
    # Arrange
    test_system, test_gen = setup_test_write_all_system_files
    test_system.template_files = {"/nonexistent/source": "/nonexistent/dest"}
    blended = utils.blender(test_gen.api, False, test_system)
    blender_spy = mocker.spy(utils, "blender")

    # Act
    test_gen.write_templates(test_system, blended=blended)

    # Assert
    assert blender_spy.call_count == 0


def test_write_templates_skips_blender_without_templates(
    mocker: "MockerFixture",
    setup_test_write_all_system_files: Tuple[System, tftpgen.TFTPGen],
):
    """
    Test that write_templates() does not call utils.blender() at all when the object has no
    template_files to render.
    """
    # Arrange
    test_system, test_gen = setup_test_write_all_system_files
    blender_spy = mocker.spy(utils, "blender")

    # Act
    test_gen.write_templates(test_system)

    # Assert
    assert blender_spy.call_count == 0


def test_write_all_system_files_removes_unused_pxe_files(
    mocker: "MockerFixture",
    setup_test_write_all_system_files: Tuple[System, tftpgen.TFTPGen],
):
    """
    When PXE support is removed from the system boot loaders we should remove the stale PXE file.
    """
    # Arrange
    test_system, test_gen = setup_test_write_all_system_files
    menu_items: Dict[str, Union[str, Dict[str, str]]] = {}
    pxe_filename = "01-aa-bb"
    grub_filename = "aa:bb"
    mocker.patch.object(test_system, "is_management_supported", return_value=True)
    mocker.patch.object(
        test_system,
        "get_config_filename",
        side_effect=[pxe_filename, grub_filename],
    )
    mocker.patch.object(
        type(test_system),
        "boot_loaders",
        new_callable=PropertyMock,
        return_value=[enums.BootLoader.GRUB],
    )
    mocker.patch.object(test_gen, "write_pxe_file")
    mock_rmfile = mocker.patch("cobbler.utils.filesystem_helpers.rmfile")
    mocker.patch("cobbler.utils.filesystem_helpers.mkdir")
    mocker.patch("os.symlink")

    # Act
    test_gen.write_all_system_files(test_system, menu_items)

    # Assert
    expected_pxe_path = os.path.join(test_gen.bootloc, "pxelinux.cfg", pxe_filename)
    removed_paths = [call.args[0] for call in mock_rmfile.call_args_list]
    assert expected_pxe_path in removed_paths


def test_write_all_system_files_removes_unused_grub_files(
    mocker: "MockerFixture",
    setup_test_write_all_system_files: Tuple[System, tftpgen.TFTPGen],
):
    """
    When GRUB support is removed from the system boot loaders we should remove the stale GRUB file and the system link.
    """
    # Arrange
    test_system, test_gen = setup_test_write_all_system_files
    menu_items: Dict[str, Union[str, Dict[str, str]]] = {}
    pxe_filename = "01-aa-bb"
    grub_filename = "aa:bb"
    mocker.patch.object(test_system, "is_management_supported", return_value=True)
    mocker.patch.object(
        test_system,
        "get_config_filename",
        side_effect=[pxe_filename, grub_filename],
    )
    mocker.patch.object(
        type(test_system),
        "boot_loaders",
        new_callable=PropertyMock,
        return_value=[enums.BootLoader.PXE],
    )
    mocker.patch.object(test_gen, "write_pxe_file")
    mock_rmfile = mocker.patch("cobbler.utils.filesystem_helpers.rmfile")
    mocker.patch("cobbler.utils.filesystem_helpers.mkdir")
    mock_symlink = mocker.patch("os.symlink")

    # Act
    test_gen.write_all_system_files(test_system, menu_items)

    # Assert
    expected_grub_path = os.path.join(test_gen.bootloc, "grub", "system", grub_filename)
    expected_link_path = os.path.join(
        test_gen.bootloc, "grub", "system_link", test_system.name
    )
    removed_paths = [call.args[0] for call in mock_rmfile.call_args_list]
    assert expected_grub_path in removed_paths
    assert expected_link_path in removed_paths
    assert mock_symlink.call_count == 0


def test_write_all_system_files_s390(
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
    create_image: Callable[[], Image],
):
    """
    Test that asserts if the generated kernel options are longer then 79 character we insert a newline for S390X.
    """
    # Arrange
    test_distro = create_distro()
    test_distro.kernel_options = {  # type: ignore[method-assign]
        "foobar1": "whatever",
        "autoyast": "http://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/this-is-a-long-string-that-need-to-be-splitted/zzzzzzzzzzzzzzzzz",
        "foobar2": "woohooo",
    }
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_system.netboot_enabled = True  # type: ignore[method-assign]
    test_image = create_image()
    test_gen = tftpgen.TFTPGen(cobbler_api)

    mocker.patch.object(test_system, "is_management_supported", return_value=True)
    open_mock = mocker.mock_open()
    open_mock.write = mocker.MagicMock()
    mocker.patch("builtins.open", open_mock)

    # Act
    # pylint: disable-next=protected-access
    test_gen._write_all_system_files_s390(  # type: ignore[reportPrivateUsage]
        test_distro, test_profile, test_image, test_system
    )

    # Assert - ensure generated parm file has fixed 80 characters format
    open_mock().write.assert_called()
    open_mock().write.assert_any_call(
        "autoyast=http://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/this-is-a-long-string-that-\nneed-to-be-splitted/zzzzzzzzzzzzzzzzz \nfoobar1=whatever \nfoobar2=woohooo\n"
    )


def test_make_pxe_menu(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test to verify that generating the complete PXE menu works as intended.
    """
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
    """
    Test to verify that retrieving the top-level menu is working as expected.
    """
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
    """
    Test to verify that retrieving the submenus works as expected.
    """
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
    """
    Test to verify that retrieving the profiles menu works as expected.
    """
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
    """
    Test to verify that retrieving the images menu works as expected.
    """
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
    """
    Test to verify that getting the metadata for a given menu level works as expected.
    """
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    # FIXME: Mock self.settings.boot_loader_conf_template_dir - maybe?
    # FIXME: Mock open() for template loading and writing
    mocker.patch.object(test_gen, "get_submenus")
    mocker.patch.object(test_gen, "get_profiles_menu")
    mocker.patch.object(test_gen, "get_images_menu")
    test_gen.api.templar = mocker.MagicMock(spec=Templar, autospec=True)

    # Act
    result = test_gen.get_menu_level()

    # Assert
    assert isinstance(result, dict)


@pytest.mark.skip("Test broken atm.")
def test_write_pxe_file(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test to verify that writing a single file related to PXE into the TFTP-root directory.
    """
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    # FIXME: Mock self.settings.to_dict() - maybe?
    # FIXME: Mock self.settings.boot_loader_conf_template_dir - maybe?
    mocker.patch.object(test_gen, "build_kernel")
    mocker.patch.object(test_gen, "build_kernel_options")

    # Act
    result = test_gen.write_pxe_file(
        "",
        None,
        None,
        None,
        enums.Archs.X86_64,
        None,
        {},
        enums.BootLoader.GRUB,
    )

    # Assert
    assert isinstance(result, str)


@pytest.mark.skip("Test broken atm.")
def test_build_kernel(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test to verify that the kernel and initrd metadata can be successfully generated.
    """
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch("cobbler.utils.blender", return_value={})

    # Act
    test_gen.build_kernel({}, None, None, None, None, "pxe")  # type: ignore

    # Assert
    assert False


def test_build_kernel_blender_call_count(
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test that build_kernel() only walks the object tree once (a single utils.blender() call) instead
    of once per remove_dicts value.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_gen = tftpgen.TFTPGen(cobbler_api)
    blender_spy = mocker.spy(utils, "blender")

    # Act
    test_gen.build_kernel({}, test_system, test_profile, test_distro, None, "pxe")

    # Assert
    assert blender_spy.call_count == 1


def test_build_kernel_options_profile(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify that the kernel options for profiles can be generated successfully.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    result = test_gen.build_kernel_options(
        None, test_profile, test_distro, None, enums.Archs.X86_64
    )

    # Assert
    assert result == ""


def test_build_kernel_options_system(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test to verify that the kernel options for systems can be generated successfully.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    result = test_gen.build_kernel_options(
        test_system, None, test_distro, None, enums.Archs.X86_64
    )

    # Assert
    assert result == ""


# pylint: disable=line-too-long
@pytest.mark.parametrize(
    "input_os_breed,input_os_version,input_autoinstall_template,expected_result",
    [
        (
            "redhat",
            "",
            "built-in-default.ks",
            "inst.ks.sendmac inst.ks=http://192.168.1.1/cblr/svc/op/autoinstall/system/test_build_kernel_options_autoinstall/file/built-in-default.ks",
        ),
        (
            "redhat",
            "rhel4",
            "built-in-legacy.ks",
            "kssendmac ks=http://192.168.1.1/cblr/svc/op/autoinstall/system/test_build_kernel_options_autoinstall/file/built-in-legacy.ks",
        ),
        (
            "suse",
            "",
            "built-in-sample_autoyast.xml",
            "info=http://192.168.1.1/cblr/svc/op/nopxe/system/test_build_kernel_options_autoinstall  autoyast=http://192.168.1.1/cblr/svc/op/autoinstall/system/test_build_kernel_options_autoinstall/file/built-in-sample_autoyast.xml",
        ),
        (
            "suse",
            "",
            "built-in-autoinst.json",
            "info=http://192.168.1.1/cblr/svc/op/nopxe/system/test_build_kernel_options_autoinstall  inst.auto=http://192.168.1.1/cblr/svc/op/autoinstall/system/test_build_kernel_options_autoinstall/file/built-in-autoinst.json",
        ),
        (
            "debian",
            "jessie",
            "built-in-sample.seed",
            "auto-install/enable=true priority=critical netcfg/choose_interface=auto url=http://192.168.1.1/cblr/svc/op/autoinstall/system/test_build_kernel_options_autoinstall/file/built-in-sample.seed hostname=test_build_kernel_options_autoinstall domain=local.lan suite=jessie",
        ),
        (
            "ubuntu",
            "lunar",
            "built-in-user-data",
            "ds=nocloud;s=http://192.168.1.1/cblr/svc/op/autoinstall/system/test_build_kernel_options_autoinstall/file/built-in-user-data hostname=test_build_kernel_options_autoinstall domain=local.lan suite=lunar",
        ),
        (
            "freebsd",
            "",
            "built-in-default.ks",
            "ks=http://192.168.1.1/cblr/svc/op/autoinstall/system/test_build_kernel_options_autoinstall/file/built-in-default.ks",
        ),
        (
            "vmware",
            "esx4",
            "built-in-sample_esxi4.ks",
            "vmkopts=debugLogToSerial:1 mem=512M ks=http://192.168.1.1/cblr/svc/op/autoinstall/system/test_build_kernel_options_autoinstall/file/built-in-sample_esxi4.ks",
        ),
        (
            "xen",
            "xenserver620",
            "built-in-answerfile.xml",
            "append /images/test_build_kernel_options_autoinstall/xen.gz dom0_max_vcpus=2 dom0_mem=752M com1=115200,8n1 console=com1,vga --- /images/test_build_kernel_options_autoinstall/vmlinuz xencons=hvc console=hvc0 console=tty0 install answerfile=http://192.168.1.1/cblr/svc/op/autoinstall/system/test_build_kernel_options_autoinstall/file/built-in-answerfile.xml --- /images/test_build_kernel_options_autoinstall/install.img",
        ),
        (
            "powerkvm",
            "",
            "built-in-powerkvm.ks",
            "kssendmac kvmp.inst.auto=http://192.168.1.1/cblr/svc/op/autoinstall/system/test_build_kernel_options_autoinstall/file/built-in-powerkvm.ks",
        ),
    ],
)
# pylint: enable=line-too-long
def test_build_kernel_options_autoinstall(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
    input_os_breed: str,
    input_os_version: str,
    input_autoinstall_template: str,
    expected_result: str,
):
    """
    Test to verify that the kernel options for systems can be generated successfully.
    """
    # Arrange
    test_distro = create_distro()
    test_distro.breed = input_os_breed
    test_distro.os_version = input_os_version
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_system.autoinstall = input_autoinstall_template  # type: ignore
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    result = test_gen.build_kernel_options(
        test_system, None, test_distro, None, enums.Archs.X86_64
    )

    # Assert
    assert result == expected_result


@pytest.mark.skip("Test broken atm.")
def test_write_templates(
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
):
    """
    Test to verify that the templates for a given distro can be written to disk.
    """
    # Arrange
    test_distro = create_distro()
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch("cobbler.utils.blender", return_value={})
    test_gen.api.templar = mocker.MagicMock(spec=Templar, autospec=True)
    # FIXME: Mock self.bootloc
    # FIXME: Mock self.settings.webdir - maybe?
    # FIXME: Mock open()

    # Act
    result = test_gen.write_templates(test_distro, False, "TODO")

    # Assert
    assert isinstance(result, dict)


@pytest.mark.skip("Test broken atm.")
def test_generate_ipxe(
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify that the ipxe config for a given profile can be generated.
    """
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
    """
    Test to verify that the bootcfg for a given profile can be generated.
    """
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
    test_gen.api.templar = mocker.MagicMock(spec=Templar, autospec=True)

    # Act
    result = test_gen.generate_bootcfg("profile", test_profile.name)

    # Assert
    assert isinstance(result, str)


def test_generate_script(
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify that a requested script is generated.
    """
    # Arrange
    expected_template = "# Start preseed_early_default\n"
    expected_template += "# This script is not run in the chroot /target by default\n"
    expected_template += "$SNIPPET('built-in-autoinstall_start')\n"
    expected_template += "$SNIPPET('built-in-save_boot_device')\n"
    expected_template += "# End preseed_early_default\n"
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch("cobbler.utils.blender", return_value={})
    test_gen.api.templar = mocker.MagicMock(spec=Templar, autospec=True)

    # Act
    result = test_gen.generate_script(
        "profile", test_profile.name, "built-in-preseed_early_default"
    )

    # Assert
    assert isinstance(result, mocker.MagicMock)
    test_gen.api.templar.render.assert_called_with(  # type: ignore
        expected_template, {"img_path": f"/images/{test_distro.name}"}, None
    )


def test_generate_windows_initrd(cobbler_api: CobblerAPI):
    """
    Test to verify that the initrd for a Windows distro is generated.
    """
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    # pylint: disable-next=protected-access
    result = test_gen._build_windows_initrd("custom_loader", "my_custom_loader", "ipxe")  # type: ignore[reportPrivateUsage]

    # Assert
    assert result == "--name custom_loader my_custom_loader custom_loader"


def test_generate_initrd(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test to verify that the initrd for a Linux distro is generated.
    """
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch.object(test_gen, "_build_windows_initrd", return_value="Test")
    input_metadata: Dict[str, Union[List[str], str]] = {
        "initrd": [],
        "bootmgr": "True",
        "bcd": "True",
        "winpe": "True",
    }
    expected_result: List[Any] = []

    # Act
    # pylint: disable-next=protected-access
    result = test_gen._generate_initrd(input_metadata, "", "", "ipxe")  # type: ignore[reportPrivateUsage]

    # Assert
    assert result == expected_result


@pytest.fixture(name="cleanup_tftproot", scope="function")
def fixture_cleanup_tftproot():
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
    """
    Test to verify that the bootcfg file is generated for esxi.
    """
    # pylint: disable=unused-argument
    # Disable unused-argument warning for pytest fixture
    # Arrange
    expected_result = "generated bootcfg"
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mocker.patch.object(test_gen, "generate_bootcfg", return_value=expected_result)

    # Act
    # pylint: disable-next=protected-access
    result = test_gen._write_bootcfg_file("profile", "test", "example.txt")  # type: ignore[reportPrivateUsage]

    # Assert
    assert result == expected_result
    assert pathlib.Path("/srv/tftpboot/esxi/example.txt").is_file()


@pytest.fixture(name="tftp_lookup_profile")
def fixture_tftp_lookup_profile(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str, bool], Distro],
    create_profile: Callable[..., Profile],
) -> Profile:
    """
    Setup fixture providing a shared distro/profile for building systems used in the
    _find_system_for_config_filename()/_find_system_for_tftp_path() tests below.
    """
    test_distro = create_distro("test_tftp_lookup_distro", True)
    return create_profile(distro_uid=test_distro.uid, name="test_tftp_lookup_profile")


def _add_tftp_lookup_system(
    cobbler_api: CobblerAPI,
    profile: Profile,
    name: str,
    mac_address: Union[str, None] = None,
    ipv4_address: Union[str, None] = None,
) -> System:
    """
    Create+add a system (with a "default" interface) for the _find_system_for_config_filename() tests.
    """
    system = cobbler_api.new_system()
    system.name = name  # type: ignore[method-assign]
    system.profile = profile.uid  # type: ignore[method-assign]
    cobbler_api.add_system(system)
    interface = cobbler_api.new_network_interface(system_uid=system.uid, name="default")
    cobbler_api.add_network_interface(interface)
    if mac_address is not None:
        interface.mac_address = mac_address  # type: ignore[method-assign]
    if ipv4_address is not None:
        interface.ipv4.address = ipv4_address  # type: ignore[method-assign]
    return system


def test_find_system_for_config_filename_pxe_mac(
    cobbler_api: CobblerAPI, tftp_lookup_profile: Profile
):
    """
    Test that a PXE-format MAC filename resolves to the system owning that MAC.
    """
    # Arrange
    cobbler_api.settings().allow_duplicate_macs = False
    system = _add_tftp_lookup_system(
        cobbler_api,
        tftp_lookup_profile,
        "pxe_mac_system",
        mac_address="AA:BB:CC:DD:EE:FF",
    )
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    # pylint: disable-next=protected-access
    result = test_gen._find_system_for_config_filename(  # type: ignore[reportPrivateUsage]
        "01-aa-bb-cc-dd-ee-ff", enums.BootLoader.PXE
    )

    # Assert
    assert result is not None
    assert result.uid == system.uid


def test_find_system_for_config_filename_grub_mac(
    cobbler_api: CobblerAPI, tftp_lookup_profile: Profile
):
    """
    Test that a GRUB-format MAC filename resolves to the system owning that MAC.
    """
    # Arrange
    cobbler_api.settings().allow_duplicate_macs = False
    system = _add_tftp_lookup_system(
        cobbler_api,
        tftp_lookup_profile,
        "grub_mac_system",
        mac_address="AA:BB:CC:DD:EE:00",
    )
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    # pylint: disable-next=protected-access
    result = test_gen._find_system_for_config_filename(  # type: ignore[reportPrivateUsage]
        "aa:bb:cc:dd:ee:00", enums.BootLoader.GRUB
    )

    # Assert
    assert result is not None
    assert result.uid == system.uid


def test_find_system_for_config_filename_ip_hex(
    cobbler_api: CobblerAPI, tftp_lookup_profile: Profile
):
    """
    Test that an IP-derived hex filename resolves to the system owning that IP.
    """
    # Arrange
    cobbler_api.settings().allow_duplicate_ips = False
    system = _add_tftp_lookup_system(
        cobbler_api, tftp_lookup_profile, "ip_hex_system", ipv4_address="10.0.0.5"
    )
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    # pylint: disable-next=protected-access
    result = test_gen._find_system_for_config_filename(  # type: ignore[reportPrivateUsage]
        utils.get_host_ip("10.0.0.5"), enums.BootLoader.PXE
    )

    # Assert
    assert result is not None
    assert result.uid == system.uid


def test_find_system_for_config_filename_literal_name(
    cobbler_api: CobblerAPI, tftp_lookup_profile: Profile
):
    """
    Test that a system with neither MAC nor IP falls back to a literal name lookup.
    """
    # Arrange
    system = _add_tftp_lookup_system(
        cobbler_api, tftp_lookup_profile, "literal_name_system"
    )
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    # pylint: disable-next=protected-access
    result = test_gen._find_system_for_config_filename(  # type: ignore[reportPrivateUsage]
        "literal_name_system", enums.BootLoader.PXE
    )

    # Assert
    assert result is not None
    assert result.uid == system.uid


def test_find_system_for_config_filename_default(
    cobbler_api: CobblerAPI, tftp_lookup_profile: Profile
):
    """
    Test that the reserved "default" system name resolves via the literal "default" filename.
    """
    # Arrange
    system = _add_tftp_lookup_system(cobbler_api, tftp_lookup_profile, "default")
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    # pylint: disable-next=protected-access
    result = test_gen._find_system_for_config_filename(  # type: ignore[reportPrivateUsage]
        "default", enums.BootLoader.PXE
    )

    # Assert
    assert result is not None
    assert result.uid == system.uid


def test_find_system_for_config_filename_no_match(
    cobbler_api: CobblerAPI, tftp_lookup_profile: Profile
):
    """
    Test that a filename with no matching system returns None (letting the caller fall back to a
    full scan), for each of the recognized filename shapes.
    """
    # Arrange
    _add_tftp_lookup_system(
        cobbler_api,
        tftp_lookup_profile,
        "unrelated_system",
        mac_address="11:22:33:44:55:66",
    )
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act / Assert
    # pylint: disable=protected-access
    assert (
        test_gen._find_system_for_config_filename(  # type: ignore[reportPrivateUsage]
            "01-de-ad-be-ef-00-00", enums.BootLoader.PXE
        )
        is None
    )
    assert (
        test_gen._find_system_for_config_filename(  # type: ignore[reportPrivateUsage]
            "DEADBEEF", enums.BootLoader.PXE
        )
        is None
    )
    assert (
        test_gen._find_system_for_config_filename(  # type: ignore[reportPrivateUsage]
            "nonexistent_system_name", enums.BootLoader.PXE
        )
        is None
    )


def test_find_system_for_config_filename_ambiguous_hex_name_not_misresolved(
    cobbler_api: CobblerAPI, tftp_lookup_profile: Profile
):
    """
    Test that a system literally named like an 8-hex-character IP filename (but with no matching IP)
    is not incorrectly matched via the IP-hex branch - the round-trip verification must reject it.
    """
    # Arrange
    _add_tftp_lookup_system(cobbler_api, tftp_lookup_profile, "DEADBEEF")
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    # pylint: disable-next=protected-access
    result = test_gen._find_system_for_config_filename(  # type: ignore[reportPrivateUsage]
        "DEADBEEF", enums.BootLoader.PXE
    )

    # Assert: falls through to the literal-name branch (uppercase hex doesn't match the lowercase-hex
    # PXE-MAC/GRUB-MAC shapes, and the IP-hex branch decodes to an IP with no owner), not a false match.
    assert result is not None
    assert result.name == "DEADBEEF"


@pytest.mark.parametrize("loader", [enums.BootLoader.PXE, enums.BootLoader.GRUB])
def test_find_system_for_config_filename_roundtrip(
    cobbler_api: CobblerAPI, tftp_lookup_profile: Profile, loader: enums.BootLoader
):
    """
    Property test: for a representative set of systems, resolving the filename that
    get_config_filename() itself produces must return that same system, for both loaders.
    """
    # Arrange
    cobbler_api.settings().allow_duplicate_macs = False
    cobbler_api.settings().allow_duplicate_ips = False
    systems = [
        _add_tftp_lookup_system(
            cobbler_api,
            tftp_lookup_profile,
            "roundtrip_mac",
            mac_address="AA:BB:CC:DD:EE:01",
        ),
        _add_tftp_lookup_system(
            cobbler_api, tftp_lookup_profile, "roundtrip_ip", ipv4_address="10.0.0.6"
        ),
        _add_tftp_lookup_system(cobbler_api, tftp_lookup_profile, "roundtrip_literal"),
    ]
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act / Assert
    for system in systems:
        filename = system.get_config_filename(interface="default", loader=loader)
        if filename is None:
            continue
        # pylint: disable-next=protected-access
        result = test_gen._find_system_for_config_filename(  # type: ignore[reportPrivateUsage]
            filename, loader
        )
        assert result is not None
        assert result.uid == system.uid


def test_find_system_for_tftp_path_dispatch(
    mocker: "MockerFixture", cobbler_api: CobblerAPI
):
    """
    Test that _find_system_for_tftp_path() dispatches each recognized path shape to
    _find_system_for_config_filename() with the correct filename/loader, and returns None for anything
    else (letting the caller fall back to a full scan).
    """
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    mock_lookup = mocker.patch.object(
        test_gen, "_find_system_for_config_filename", return_value=None
    )

    # Act / Assert
    test_gen._find_system_for_tftp_path(  # type: ignore[reportPrivateUsage]
        pathlib.Path("/pxelinux.cfg/01-aa-bb-cc-dd-ee-ff")
    )
    mock_lookup.assert_called_with("01-aa-bb-cc-dd-ee-ff", enums.BootLoader.PXE)

    test_gen._find_system_for_tftp_path(  # type: ignore[reportPrivateUsage]
        pathlib.Path("/esxi/pxelinux.cfg/01-aa-bb-cc-dd-ee-ff")
    )
    mock_lookup.assert_called_with("01-aa-bb-cc-dd-ee-ff", enums.BootLoader.PXE)

    test_gen._find_system_for_tftp_path(  # type: ignore[reportPrivateUsage]
        pathlib.Path("/grub/system/aa:bb:cc:dd:ee:ff")
    )
    mock_lookup.assert_called_with("aa:bb:cc:dd:ee:ff", enums.BootLoader.GRUB)

    assert (
        test_gen._find_system_for_tftp_path(  # type: ignore[reportPrivateUsage]
            pathlib.Path("/some/unrelated/path")
        )
        is None
    )


def test_generate_tftp_file_uses_fast_path(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, tftp_lookup_profile: Profile
):
    """
    Test that generate_tftp_file() resolves a PXE config request via the fast, indexed lookup instead
    of iterating every system, and produces the same content generate_system_file() would directly.
    """
    # Arrange
    cobbler_api.settings().allow_duplicate_macs = False
    system = _add_tftp_lookup_system(
        cobbler_api,
        tftp_lookup_profile,
        "fast_path_system",
        mac_address="AA:BB:CC:DD:EE:02",
    )
    test_gen = tftpgen.TFTPGen(cobbler_api)
    path = pathlib.Path("/pxelinux.cfg/01-aa-bb-cc-dd-ee-02")
    metadata = test_gen.get_menu_items()
    expected = test_gen.generate_system_file(system, path, metadata)
    generate_system_file_spy = mocker.spy(test_gen, "generate_system_file")

    # Act
    content, _length = test_gen.generate_tftp_file(path, 0, 10_000)

    # Assert
    assert expected is not None
    assert content == expected.encode("UTF-8")
    # Exactly one call (for the resolved candidate) - if the fast path had failed and fallen back to
    # the full scan, this would be called once per system up to and including the match.
    assert generate_system_file_spy.call_count == 1


def test_get_bundled_grub_file_returns_default_grub_cfg(cobbler_api: CobblerAPI):
    """
    Test that _get_bundled_grub_file() serves Cobbler's embedded default grub.cfg straight from the package
    resources, without anything needing to be copied to disk.
    """
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    expected = (
        tftpgen.files("cobbler.data.config.grub").joinpath("grub.cfg").read_bytes()
    )

    # Act
    content, length = test_gen._get_bundled_grub_file(  # type: ignore[reportPrivateUsage]
        pathlib.Path("/grub.cfg"), 0, 10_000
    )

    # Assert
    assert content == expected
    assert length == len(expected)


def test_get_bundled_grub_file_returns_default_grub_subfolder_file(
    cobbler_api: CobblerAPI,
):
    """
    Test that _get_bundled_grub_file() also serves files bundled under the "grub/" subfolder.
    """
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)
    expected = (
        tftpgen.files("cobbler.data.config.grub")
        .joinpath("grub")
        .joinpath("local_efi.cfg")
        .read_bytes()
    )

    # Act
    content, length = test_gen._get_bundled_grub_file(  # type: ignore[reportPrivateUsage]
        pathlib.Path("/grub/local_efi.cfg"), 0, 10_000
    )

    # Assert
    assert content == expected
    assert length == len(expected)


def test_get_bundled_grub_file_returns_none_for_unrelated_path(
    cobbler_api: CobblerAPI,
):
    """
    Test that _get_bundled_grub_file() returns None for paths that aren't part of the bundled default GRUB
    configuration, so the caller can continue its own fallback/error handling.
    """
    # Arrange
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act / Assert
    assert (
        test_gen._get_bundled_grub_file(  # type: ignore[reportPrivateUsage]
            pathlib.Path("/pxelinux.0"), 0, 10_000
        )
        is None
    )
    assert (
        test_gen._get_bundled_grub_file(  # type: ignore[reportPrivateUsage]
            pathlib.Path("/grub/does_not_exist.cfg"), 0, 10_000
        )
        is None
    )


def test_get_static_tftp_file_falls_back_to_bundled_grub_cfg(
    tmp_path: pathlib.Path, cobbler_api: CobblerAPI
):
    """
    Test that _get_static_tftp_file() falls back to the bundled default grub.cfg when it's absent from both
    bootloaders_dir and grubconfig_dir.
    """
    # Arrange
    cobbler_api.settings().bootloaders_dir = str(tmp_path / "loaders")
    cobbler_api.settings().grubconfig_dir = str(tmp_path / "grub_config")
    os.makedirs(cobbler_api.settings().bootloaders_dir)
    os.makedirs(cobbler_api.settings().grubconfig_dir)
    test_gen = tftpgen.TFTPGen(cobbler_api)
    expected = (
        tftpgen.files("cobbler.data.config.grub").joinpath("grub.cfg").read_bytes()
    )

    # Act
    result = test_gen._get_static_tftp_file(  # type: ignore[reportPrivateUsage]
        pathlib.Path("/grub.cfg"), 0, 10_000
    )

    # Assert
    assert result is not None
    content, length = result
    assert content == expected
    assert length == len(expected)


def test_get_static_tftp_file_grubconfig_override_takes_precedence(
    tmp_path: pathlib.Path, cobbler_api: CobblerAPI
):
    """
    Test that a custom grub.cfg placed in grubconfig_dir is served instead of the bundled default.
    """
    # Arrange
    cobbler_api.settings().bootloaders_dir = str(tmp_path / "loaders")
    cobbler_api.settings().grubconfig_dir = str(tmp_path / "grub_config")
    os.makedirs(cobbler_api.settings().bootloaders_dir)
    os.makedirs(cobbler_api.settings().grubconfig_dir)
    override_content = b"# custom override grub.cfg\n"
    (tmp_path / "grub_config" / "grub.cfg").write_bytes(override_content)
    test_gen = tftpgen.TFTPGen(cobbler_api)

    # Act
    result = test_gen._get_static_tftp_file(  # type: ignore[reportPrivateUsage]
        pathlib.Path("/grub.cfg"), 0, 10_000
    )

    # Assert
    assert result is not None
    content, length = result
    assert content == override_content
    assert length == len(override_content)
