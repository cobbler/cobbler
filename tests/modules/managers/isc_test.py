"""
Test to verify the functionallity of the isc DHCP module.
"""

import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System
from cobbler.modules.managers import isc
from cobbler.settings import Settings

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def api_isc_mock():
    """
    Mock to prevent the full creation of a CobblerAPI and Settings object.
    """
    settings_mock = MagicMock(name="isc_setting_mock", spec=Settings)
    settings_mock.server = "127.0.0.1"
    settings_mock.default_template_type = "cheetah"
    settings_mock.cheetah_import_whitelist = ["re"]
    settings_mock.always_write_dhcp_entries = True
    settings_mock.http_port = 80
    settings_mock.next_server_v4 = "127.0.0.1"
    settings_mock.next_server_v6 = "::1"
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
    settings_mock.manage_dhcp_v4 = True
    settings_mock.manage_dhcp_v6 = True
    settings_mock.jinja2_includedir = ""
    settings_mock.default_virt_disk_driver = "raw"
    settings_mock.cache_enabled = False
    api_mock = MagicMock(autospec=True, spec=CobblerAPI)
    api_mock.settings.return_value = settings_mock  # type: ignore
    test_distro = Distro(api_mock)
    test_distro.name = "test"
    api_mock.distros.return_value = [test_distro]  # type: ignore
    test_profile = Profile(api_mock)
    test_profile.name = "test"
    test_profile._parent = test_distro.name  # type: ignore
    api_mock.profiles.return_value = [test_profile]  # type: ignore
    test_system = System(api_mock)
    test_system.name = "test"
    test_system._parent = test_profile.name  # type: ignore
    api_mock.systems.return_value = [test_system]  # type: ignore
    api_mock.repos.return_value = []  # type: ignore
    return api_mock


@pytest.fixture(scope="function", autouse=True)
def reset_singleton():
    """
    Helper fixture to reset the isc singleton before and after a test.
    """
    isc.MANAGER = None
    yield
    isc.MANAGER = None


def test_register():
    """
    Test if the manager registers with the correct ID.
    """
    # Arrange & Act
    result = isc.register()

    # Assert
    assert result == "manage"


def test_get_manager(api_isc_mock: CobblerAPI):
    """
    Test if the singleton is correctly initialized.
    """
    # Arrange
    isc.MANAGER = None

    # Act
    result = isc.get_manager(api_isc_mock)

    # Assert
    assert isinstance(result, isc._IscManager)  # type: ignore


def test_manager_what():
    """
    Test if the manager identifies itself correctly.
    """
    # Arrange & Act & Assert
    assert isc._IscManager.what() == "isc"  # type: ignore


def test_manager_write_v4_config(mocker: "MockerFixture", api_isc_mock: CobblerAPI):
    """
    Test if the manager is able to correctly generate the IPv4 isc dhcpd conf file.
    """
    # Arrange
    mocker.patch("builtins.open", mocker.mock_open(read_data="test"))
    mocker.patch(
        "time.gmtime",
        return_value=time.struct_time((2000, 1, 1, 0, 0, 0, 0, 1, 1)),
    )
    isc.MANAGER = None
    manager = isc.get_manager(api_isc_mock)
    mocked_templar = mocker.patch.object(manager, "templar", autospec=True)

    # Act
    manager.write_v4_config()

    # Assert
    assert mocked_templar.render.call_count == 1  # type: ignore
    mocked_templar.render.assert_called_with(  # type: ignore
        "test",
        {
            "cobbler_server": "127.0.0.1:80",
            "date": "Mon Jan  1 00:00:00 2000",
            "dhcp_tags": {"default": {}},
            "next_server_v4": "127.0.0.1",
        },
        "/etc/dhcpd.conf",
    )


def test_manager_write_v6_config(mocker: "MockerFixture", api_isc_mock: CobblerAPI):
    """
    Test if the manager is able to correctly generate the IPv6 isc dhcpd conf file.
    """
    # Arrange
    mocker.patch("builtins.open", mocker.mock_open(read_data="test"))
    mocker.patch(
        "time.gmtime",
        return_value=time.struct_time((2000, 1, 1, 0, 0, 0, 0, 1, 1)),
    )
    isc.MANAGER = None
    manager = isc.get_manager(api_isc_mock)
    mocked_templar = mocker.patch.object(manager, "templar", autospec=True)

    # Act
    manager.write_v6_config()

    # Assert
    assert mocked_templar.render.call_count == 1  # type: ignore
    mocked_templar.render.assert_called_with(  # type: ignore
        "test",
        {
            "date": "Mon Jan  1 00:00:00 2000",
            "next_server_v6": "::1",
            "dhcp_tags": {"default": {}},
        },
        "/etc/dhcpd6.conf",
    )


def test_manager_restart_dhcp(mocker: "MockerFixture", api_isc_mock: CobblerAPI):
    """
    Test if the manager correctly restart the daemon.
    """
    # Arrange
    isc.MANAGER = None
    mocked_subprocess = mocker.patch(
        "cobbler.utils.subprocess_call", autospec=True, return_value=0
    )
    mocked_service_restart = mocker.patch(
        "cobbler.utils.process_management.service_restart",
        autospec=True,
        return_value=0,
    )
    manager = isc.get_manager(api_isc_mock)

    # Act
    result = manager.restart_dhcp("dhcpd", 4)

    # Assert
    assert mocked_subprocess.call_count == 1
    mocked_subprocess.assert_called_with(
        ["/usr/sbin/dhcpd", "-4", "-t", "-q"], shell=False
    )
    assert mocked_service_restart.call_count == 1
    mocked_service_restart.assert_called_with("dhcpd")
    assert result == 0


def test_manager_write_configs(mocker: "MockerFixture", api_isc_mock: CobblerAPI):
    """
    Test if the manager is able to correctly kick of generation of the v4 and v6 configs.
    """
    # Arrange
    isc.MANAGER = None
    manager = isc.get_manager(api_isc_mock)
    mocked_v4 = mocker.patch.object(manager, "write_v4_config", autospec=True)
    mocked_v6 = mocker.patch.object(manager, "write_v6_config", autospec=True)

    # Act
    manager.write_configs()

    # Assert
    assert mocked_v4.call_count == 1
    assert mocked_v6.call_count == 1


def test_manager_restart_service(mocker: "MockerFixture", api_isc_mock: CobblerAPI):
    """
    Test if the manager is able to correctly handle restarting the dhcpd server on different distros.
    """
    # Arrange
    isc.MANAGER = None
    manager = isc.get_manager(api_isc_mock)
    mocked_restart = mocker.patch.object(
        manager, "restart_dhcp", autospec=True, return_value=0
    )
    mocked_service_name = mocker.patch(
        "cobbler.utils.dhcp_service_name", autospec=True, return_value="dhcpd"
    )

    # Act
    result = manager.restart_service()

    # Assert
    assert mocked_service_name.call_count == 1
    assert mocked_restart.call_count == 2
    assert result == 0
