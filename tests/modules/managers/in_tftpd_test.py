from unittest.mock import MagicMock, Mock

import pytest

from cobbler.api import CobblerAPI
from cobbler.modules.managers import in_tftpd
from cobbler.tftpgen import TFTPGen
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System
from cobbler.settings import Settings


@pytest.fixture
def api_mock_tftp():
    api_mock_tftp = MagicMock(spec=CobblerAPI)
    settings_mock = MagicMock(name="in_tftpd_setting_mock", spec=Settings, autospec=True)
    settings_mock.server = "127.0.0.1"
    settings_mock.default_template_type = "cheetah"
    settings_mock.cheetah_import_whitelist = ["re"]
    settings_mock.always_write_dhcp_entries = True
    settings_mock.http_port = 80
    settings_mock.next_server_v4 = ""
    settings_mock.next_server_v6 = ""
    settings_mock.default_ownership = ""
    settings_mock.default_virt_bridge = ""
    settings_mock.default_virt_type = "auto"
    settings_mock.default_virt_ram = 64
    settings_mock.restart_dhcp = True
    settings_mock.enable_ipxe = True
    settings_mock.enable_menu = True
    settings_mock.virt_auto_boot = True
    settings_mock.default_name_servers = []
    settings_mock.default_name_servers_search = []
    settings_mock.manage_dhcp_v4 = True
    settings_mock.manage_dhcp_v6 = True
    settings_mock.jinja2_includedir = ""
    settings_mock.default_virt_disk_driver = "raw"
    settings_mock.tftpboot_location = "/var/lib/tftpboot"
    settings_mock.webdir = "/srv/www/cobbler"
    api_mock_tftp.settings.return_value = settings_mock
    test_distro = Distro(api_mock_tftp)
    test_distro.name = "test"
    test_profile = Profile(api_mock_tftp)
    test_profile.name = "test"
    test_system = System(api_mock_tftp)
    test_system.name = "test"
    api_mock_tftp.find_system.return_value = test_system
    api_mock_tftp.distros = MagicMock(return_value=[test_distro])
    api_mock_tftp.profiles = MagicMock(return_value=[test_profile])
    api_mock_tftp.systems = MagicMock(return_value=[test_system])
    api_mock_tftp.repos = MagicMock(return_value=[])
    return api_mock_tftp


@pytest.fixture(scope="function", autouse=True)
def reset_singleton():
    in_tftpd.MANAGER = None
    yield
    in_tftpd.MANAGER = None


def test_register():
    # Arrange
    # Act
    result = in_tftpd.register()

    # Assert
    assert result == "manage"


def test_manager_what():
    # Arrange & Act & Assert
    assert in_tftpd._InTftpdManager.what() == "in_tftpd"


def test_tftpd_singleton(reset_singleton):
    # Arrange
    mcollection = Mock()

    # Act
    manager_1 = in_tftpd.get_manager(mcollection)
    manager_2 = in_tftpd.get_manager(mcollection)

    # Assert
    assert manager_1 == manager_2


@pytest.mark.skip("TODO: in utils.blender() we have the problem that 'server' is not available.")
def test_manager_write_boot_files_distro(api_mock_tftp, reset_singleton):
    # Arrange
    manager_obj = in_tftpd.get_manager(api_mock_tftp)

    # Act
    result = manager_obj.write_boot_files_distro(api_mock_tftp.distros()[0])

    # Assert
    assert result == 0


def test_manager_write_boot_files(mocker, api_mock_tftp, reset_singleton):
    # Arrange
    manager_obj = in_tftpd.get_manager(api_mock_tftp)
    mocker.patch.object(manager_obj, "write_boot_files_distro")

    # Act
    result = manager_obj.write_boot_files()

    # Assert
    assert manager_obj.write_boot_files_distro.call_count == 1
    assert result == 0


def test_manager_sync_single_system(mocker, api_mock_tftp, reset_singleton):
    # Arrange
    manager_obj = in_tftpd.get_manager(api_mock_tftp)
    tftpgen_mock = MagicMock(spec=TFTPGen, autospec=True)
    mocker.patch.object(manager_obj, "tftpgen", return_value=tftpgen_mock)

    # Act
    manager_obj.sync_single_system(None, None)

    # Assert
    assert manager_obj.tftpgen.write_all_system_files.call_count == 1
    assert manager_obj.tftpgen.write_templates.call_count == 1


def test_manager_add_single_distro(mocker, api_mock_tftp, reset_singleton):
    # Arrange
    manager_obj = in_tftpd.get_manager(api_mock_tftp)
    tftpgen_mock = MagicMock(spec=TFTPGen, autospec=True)
    mocker.patch.object(manager_obj, "tftpgen", return_value=tftpgen_mock)
    mocker.patch.object(manager_obj, "write_boot_files_distro")

    # Act
    manager_obj.add_single_distro(None)

    # Assert
    assert manager_obj.tftpgen.copy_single_distro_files.call_count == 1
    assert manager_obj.write_boot_files_distro.call_count == 1


@pytest.mark.parametrize(
    "input_systems, input_verbose, expected_output",
    [(["t1.example.org"], True, "t1.example.org")],
)
def test_sync_systems(mocker, api_mock_tftp, input_systems, input_verbose, expected_output, reset_singleton):
    # Arrange
    manager_obj = in_tftpd.get_manager(api_mock_tftp)
    tftpgen_mock = MagicMock(spec=TFTPGen, autospec=True)
    mocker.patch.object(manager_obj, "tftpgen", return_value=tftpgen_mock)
    single_system_mock = mocker.patch.object(manager_obj, "sync_single_system")

    # Act
    manager_obj.sync_systems(input_systems, input_verbose)

    # Assert
    assert manager_obj.tftpgen.get_menu_items.call_count == 1
    assert single_system_mock.call_count == 1
    assert manager_obj.tftpgen.make_pxe_menu.call_count == 1


def test_manager_sync(mocker, api_mock_tftp, reset_singleton):
    # Arrange
    manager_obj = in_tftpd.get_manager(api_mock_tftp)
    tftpgen_mock = MagicMock(spec=TFTPGen, autospec=True)
    mocker.patch.object(manager_obj, "tftpgen", return_value=tftpgen_mock)

    # Act
    manager_obj.sync()

    # Assert
    assert manager_obj.tftpgen.copy_bootloaders.call_count == 1
    assert manager_obj.tftpgen.copy_single_distro_files.call_count == 1
    assert manager_obj.tftpgen.copy_images.call_count == 1
    assert manager_obj.tftpgen.get_menu_items.call_count == 1
    assert manager_obj.tftpgen.write_all_system_files.call_count == 1
    assert manager_obj.tftpgen.make_pxe_menu.call_count == 1
