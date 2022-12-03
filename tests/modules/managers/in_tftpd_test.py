"""
Tests that validate the functionality of the module that is responsible for managing the config files of the
ISC DHCP server.
"""

from typing import TYPE_CHECKING, Any, Generator, List

import pytest

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System
from cobbler.modules.managers import in_tftpd
from cobbler.settings import Settings
from cobbler.tftpgen import TFTPGen

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="api_mock_tftp")
def fixture_api_mock_tftp(mocker: "MockerFixture") -> CobblerAPI:
    """
    TODO
    """
    api_mock_tftp = mocker.MagicMock(spec=CobblerAPI)
    settings_mock = mocker.MagicMock(
        name="in_tftpd_setting_mock", spec=Settings, autospec=True
    )
    settings_mock.server = "127.0.0.1"
    settings_mock.default_template_type = "cheetah"
    settings_mock.cheetah_import_whitelist = ["re"]
    settings_mock.always_write_dhcp_entries = True
    settings_mock.http_port = 80
    settings_mock.next_server_v4 = ""
    settings_mock.next_server_v6 = ""
    settings_mock.default_ownership = []
    settings_mock.default_virt_bridge = ""
    settings_mock.default_virt_type = "auto"
    settings_mock.default_virt_ram = 64
    settings_mock.restart_dhcp = True
    settings_mock.enable_ipxe = True
    settings_mock.enable_menu = True
    settings_mock.virt_auto_boot = True
    settings_mock.default_name_servers = []
    settings_mock.default_name_servers_search = []
    settings_mock.redhat_management_server = "xmlrpc.rhn.redhat.com"
    settings_mock.redhat_management_key = ""
    settings_mock.manage_dhcp_v4 = True
    settings_mock.manage_dhcp_v6 = True
    settings_mock.default_virt_disk_driver = "raw"
    settings_mock.tftpboot_location = "/var/lib/tftpboot"
    settings_mock.webdir = "/srv/www/cobbler"
    settings_mock.cache_enabled = False
    settings_mock.to_dict.return_value = {"server": "127.0.0.1"}
    api_mock_tftp.settings.return_value = settings_mock
    test_distro = Distro(api_mock_tftp)
    test_distro.name = "test"
    test_profile = Profile(api_mock_tftp)
    test_profile.name = "test"
    test_system = System(api_mock_tftp)
    test_system.name = "test"
    api_mock_tftp.find_system.return_value = test_system
    api_mock_tftp.distros = mocker.MagicMock(return_value=[test_distro])
    api_mock_tftp.profiles = mocker.MagicMock(return_value=[test_profile])
    api_mock_tftp.systems = mocker.MagicMock(return_value=[test_system])
    api_mock_tftp.repos = mocker.MagicMock(return_value=[])
    api_mock_tftp.tftpgen = mocker.MagicMock(spec=TFTPGen, autospec=True)
    return api_mock_tftp


@pytest.fixture(name="reset_singleton", scope="function", autouse=True)
def fixture_reset_singleton() -> Generator[Any, Any, Any]:
    """
    TODO
    """
    in_tftpd.MANAGER = None
    yield
    in_tftpd.MANAGER = None


def test_register():
    """
    TODO
    """
    # Arrange & Act
    result = in_tftpd.register()

    # Assert
    assert result == "manage"


def test_manager_what():
    """
    TODO
    """
    # pylint: disable=protected-access
    # Arrange & Act & Assert
    assert in_tftpd._InTftpdManager.what() == "in_tftpd"  # type: ignore[reportPrivateUsage]


def test_tftpd_singleton(mocker: "MockerFixture"):
    """
    TODO
    """
    # Arrange
    mcollection = mocker.Mock()

    # Act
    manager_1 = in_tftpd.get_manager(mcollection)
    manager_2 = in_tftpd.get_manager(mcollection)

    # Assert
    assert manager_1 == manager_2


def test_manager_write_boot_files_distro(api_mock_tftp: CobblerAPI):
    """
    TODO
    """
    # Arrange
    manager_obj = in_tftpd.get_manager(api_mock_tftp)

    # Act
    result = manager_obj.write_boot_files_distro(api_mock_tftp.distros()[0])  # type: ignore[reportUnknownArgumentType,index]

    # Assert
    assert result == 0


def test_manager_write_boot_files(mocker: "MockerFixture", api_mock_tftp: CobblerAPI):
    """
    TODO
    """
    # Arrange
    manager_obj = in_tftpd.get_manager(api_mock_tftp)
    mocker.patch.object(manager_obj, "write_boot_files_distro")

    # Act
    result = manager_obj.write_boot_files()

    # Assert
    # pylint: disable=no-member
    assert manager_obj.write_boot_files_distro.call_count == 1  # type: ignore[reportFunctionMemberAccess,attr-defined]
    assert result == 0


def test_manager_sync_single_system(api_mock_tftp: CobblerAPI):
    """
    TODO
    """
    # Arrange
    manager_obj = in_tftpd.get_manager(api_mock_tftp)
    tftpgen_mock = api_mock_tftp.tftpgen

    # Act
    manager_obj.sync_single_system(None, None)  # type: ignore[reportArgumentType,arg-type]

    # Assert
    # pylint: disable=no-member
    assert tftpgen_mock.write_all_system_files.call_count == 1  # type: ignore[reportFunctionMemberAccess,attr-defined]
    assert tftpgen_mock.write_templates.call_count == 1  # type: ignore[reportFunctionMemberAccess,attr-defined]


def test_manager_add_single_distro(mocker: "MockerFixture", api_mock_tftp: CobblerAPI):
    """
    TODO
    """
    # Arrange
    manager_obj = in_tftpd.get_manager(api_mock_tftp)
    tftpgen_mock = api_mock_tftp.tftpgen
    mocker.patch.object(manager_obj, "write_boot_files_distro")

    # Act
    manager_obj.add_single_distro(None)  # type: ignore[reportArgumentType,arg-type]

    # Assert
    # pylint: disable=no-member
    assert tftpgen_mock.copy_single_distro_files.call_count == 1  # type: ignore[reportFunctionMemberAccess,attr-defined]
    assert manager_obj.write_boot_files_distro.call_count == 1  # type: ignore[reportFunctionMemberAccess,attr-defined]


@pytest.mark.parametrize(
    "input_systems, input_verbose, expected_output",
    [(["t1.example.org"], True, "t1.example.org")],
)
def test_sync_systems(
    mocker: "MockerFixture",
    api_mock_tftp: CobblerAPI,
    input_systems: List[str],
    input_verbose: bool,
    expected_output: str,
):
    """
    TODO
    """
    # Arrange
    manager_obj = in_tftpd.get_manager(api_mock_tftp)
    tftpgen_mock = api_mock_tftp.tftpgen
    single_system_mock = mocker.patch.object(manager_obj, "sync_single_system")

    # Act
    manager_obj.sync_systems(input_systems, input_verbose)

    # Assert
    # pylint: disable=no-member
    assert tftpgen_mock.get_menu_items.call_count == 1  # type: ignore[reportFunctionMemberAccess,attr-defined]
    assert single_system_mock.call_count == 1
    assert tftpgen_mock.make_pxe_menu.call_count == 1  # type: ignore[reportFunctionMemberAccess,attr-defined]


def test_manager_sync(api_mock_tftp: CobblerAPI):
    """
    TODO
    """
    # Arrange
    manager_obj = in_tftpd.get_manager(api_mock_tftp)
    tftpgen_mock = api_mock_tftp.tftpgen

    # Act
    manager_obj.sync()

    # Assert
    # pylint: disable=no-member
    assert tftpgen_mock.copy_bootloaders.call_count == 1  # type: ignore[reportFunctionMemberAccess,attr-defined]
    assert tftpgen_mock.copy_single_distro_files.call_count == 1  # type: ignore[reportFunctionMemberAccess,attr-defined]
    assert tftpgen_mock.copy_images.call_count == 1  # type: ignore[reportFunctionMemberAccess,attr-defined]
    assert tftpgen_mock.get_menu_items.call_count == 1  # type: ignore[reportFunctionMemberAccess,attr-defined]
    assert tftpgen_mock.write_all_system_files.call_count == 1  # type: ignore[reportFunctionMemberAccess,attr-defined]
    assert tftpgen_mock.make_pxe_menu.call_count == 1  # type: ignore[reportFunctionMemberAccess,attr-defined]
