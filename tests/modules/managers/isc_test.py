"""
Test to verify the functionality of the isc DHCP module.
"""

import time
from typing import TYPE_CHECKING

import pytest

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import NetworkInterface, System
from cobbler.modules.managers import isc
from cobbler.settings import Settings

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="api_isc_mock")
def fixture_api_isc_mock(mocker: "MockerFixture"):
    """
    Mock to prevent the full creation of a CobblerAPI and Settings object.
    """
    settings_mock = mocker.MagicMock(name="isc_setting_mock", spec=Settings)
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
    settings_mock.allow_duplicate_hostnames = True
    settings_mock.allow_duplicate_macs = True
    settings_mock.allow_duplicate_ips = True
    settings_mock.autoinstall_snippets_dir = ""
    settings_mock.autoinstall_templates_dir = ""
    api_mock = mocker.MagicMock(autospec=True, spec=CobblerAPI)
    api_mock.settings.return_value = settings_mock  # type: ignore
    test_distro = Distro(api_mock)
    test_distro.name = "test"
    api_mock.distros.return_value = [test_distro]  # type: ignore
    test_profile = Profile(api_mock)
    test_profile.name = "test"
    # pylint: disable-next=protected-access
    test_profile._parent = test_distro.name  # type: ignore
    api_mock.profiles.return_value = [test_profile]  # type: ignore
    mocker.patch(
        "cobbler.items.system.System.interfaces",
        new_callable=mocker.PropertyMock(
            return_value={
                "default": NetworkInterface(
                    api=api_mock,
                    system_uid="not-empty",
                    name="default",
                    ipv4={"address": "192.168.1.2"},
                    ipv6={"address": "::1"},
                    dns={"name": "host.example.org"},
                    mac_address="aa:bb:cc:dd:ee:ff",
                )
            }
        ),
    )
    test_system = System(api_mock)
    test_system.name = "test"
    # pylint: disable-next=protected-access
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
    # pylint: disable-next=protected-access
    assert isinstance(result, isc._IscManager)  # type: ignore


def test_manager_what():
    """
    Test if the manager identifies itself correctly.
    """
    # Arrange & Act & Assert
    # pylint: disable-next=protected-access
    assert isc._IscManager.what() == "isc"  # type: ignore


def test_manager_write_v4_config(mocker: "MockerFixture", api_isc_mock: CobblerAPI):
    """
    Test if the manager is able to correctly generate the IPv4 isc dhcpd conf file.
    """
    # Arrange
    mocker.patch("builtins.open", mocker.mock_open(read_data="test"))
    isc.MANAGER = None
    manager = isc.get_manager(api_isc_mock)
    mocked_templar = mocker.patch.object(manager, "templar", autospec=True)
    mock_server_config = {  # type: ignore
        "cobbler_server": "127.0.0.1:80",
        "date": "Mon Jan  1 00:00:00 2000",
        "dhcp_tags": {"default": {}},
        "next_server_v4": "127.0.0.1",
    }

    # Act
    manager.write_v4_config(mock_server_config)  # type: ignore

    # Assert
    assert mocked_templar.render.call_count == 1  # type: ignore
    mocked_templar.render.assert_called_with(  # type: ignore
        "test",
        mock_server_config,
        "/etc/dhcpd.conf",
    )


def test_manager_write_v6_config(mocker: "MockerFixture", api_isc_mock: CobblerAPI):
    """
    Test if the manager is able to correctly generate the IPv6 isc dhcpd conf file.
    """
    # Arrange
    mocker.patch("builtins.open", mocker.mock_open(read_data="test"))
    isc.MANAGER = None
    manager = isc.get_manager(api_isc_mock)
    mocked_templar = mocker.patch.object(manager, "templar", autospec=True)
    mock_server_config = {  # type: ignore
        "dhcp_tags": {"default": {}},
        "next_server_v4": "127.0.0.1",
        "next_server_v6": "::1",
    }

    # Act
    manager.write_v6_config(mock_server_config)  # type: ignore

    # Assert
    assert mocked_templar.render.call_count == 1  # type: ignore
    mocked_templar.render.assert_called_with(  # type: ignore
        "test",
        mock_server_config,
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
    mocker.patch.object(manager, "gen_full_config")

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


def test_manager_gen_full_config(mocker: "MockerFixture", api_isc_mock: CobblerAPI):
    """
    Verifies that the DHCP configuration for all systems can be generated successfully.
    """
    # pylint: disable=protected-access
    # Arrange
    isc.MANAGER = None
    manager = isc.get_manager(api_isc_mock)
    mock_distro = Distro(api_isc_mock)
    mock_distro.redhat_management_key = ""
    mock_profile = Profile(api_isc_mock)
    mock_profile.autoinstall = ""
    mock_profile._distro = mock_distro.uid  # type: ignore
    mock_profile.proxy = ""
    mock_profile.virt.file_size = ""  # type: ignore
    mock_system = System(api_isc_mock)
    mock_system.name = "test_manager_regen_hosts_system"
    mock_system._profile = mock_profile.uid  # type: ignore
    mock_interface = NetworkInterface(api_isc_mock, mock_system.uid)
    mock_interface._dns._name = "host.example.org"  # type: ignore
    mock_interface._mac_address = "aa:bb:cc:dd:ee:ff"  # type: ignore
    mock_interface._ipv4._address = "192.168.1.2"  # type: ignore
    mock_interface._ipv6._address = "::1"  # type: ignore
    mock_system._interfaces = {"default": mock_interface}  # type: ignore
    mocker.patch.object(mock_system, "get_conceptual_parent", return_value=mock_profile)
    mocker.patch.object(mock_profile, "get_conceptual_parent", return_value=mock_distro)
    manager.systems = [mock_system]  # type: ignore

    # Act
    result = manager.gen_full_config()

    # Assert
    assert mock_interface.mac_address in result["dhcp_tags"]["default"]
    result_dhcp_tags = result["dhcp_tags"]["default"][mock_interface.mac_address]
    assert result_dhcp_tags["dns"]["name"] == mock_interface.dns.name
    assert result_dhcp_tags["mac_address"] == mock_interface.mac_address
    assert result_dhcp_tags["ipv4"]["address"] == mock_interface.ipv4.address
    assert result_dhcp_tags["ipv6"]["address"] == mock_interface.ipv6.address


def _get_mock_config():  # type: ignore
    config = {  # type: ignore
        "cobbler_server": "127.0.0.1:80",
        "date": "Tue Jun 11 16:19:49 2024",
        "dhcp_tags": {
            "default": {
                "aa:bb:cc:dd:ee:ff": {
                    "dhcp_tag": "",
                    "distro": {
                        "arch": "x86_64",
                    },
                    "dns_name": "host.example.org",
                    "interface_type": "na",
                    "ip_address": "192.168.1.2",
                    "ipv6_address": "::1",
                    "mac_address": "aa:bb:cc:dd:ee:ff",
                    "name": "host.example.org-default",
                    "next_server_v4": "127.0.0.1",
                    "next_server_v6": "::1",
                    "owner": "test_manager_regen_hosts_system",
                    "profile": {},
                    "static": False,
                    "static_routes": [],
                    "virt_bridge": "<<inherit>>",
                },
            },
        },
        "next_server_v4": "127.0.0.1",
        "next_server_v6": "::1",
    }

    return config  # type: ignore


def test_manager_remove_single_system(
    mocker: "MockerFixture", api_isc_mock: CobblerAPI
):
    """
    Verifies that a single system can be successfully removed from the ISC DHCP configuration.
    """
    # pylint: disable=protected-access
    # Arrange
    mocker.patch(
        "time.gmtime",
        return_value=time.struct_time((2000, 1, 1, 0, 0, 0, 0, 1, 1)),
    )
    isc.MANAGER = None
    manager = isc.get_manager(api_isc_mock)
    mock_distro = Distro(api_isc_mock)
    mock_distro.redhat_management_key = ""
    mock_profile = Profile(api_isc_mock)
    mock_profile.autoinstall = ""
    mock_profile._distro = mock_distro.uid  # type: ignore
    mock_profile.proxy = ""
    mock_profile.virt.file_size = ""  # type: ignore
    mock_system = System(api_isc_mock)
    mock_system.name = "test_manager_regen_hosts_system"
    mock_system._profile = mock_profile.uid  # type: ignore
    mock_interface = NetworkInterface(api_isc_mock, mock_system.uid)
    mock_interface._dns_name = "host.example.org"  # type: ignore
    mock_interface._mac_address = "aa:bb:cc:dd:ee:ff"  # type: ignore
    mock_interface._ip_address = "192.168.1.2"  # type: ignore
    mock_interface._ipv6_address = "::1"  # type: ignore
    mock_system._interfaces = {"default": mock_interface}  # type: ignore
    mocker.patch.object(mock_system, "get_conceptual_parent", return_value=mock_profile)
    mocker.patch.object(mock_profile, "get_conceptual_parent", return_value=mock_distro)
    manager.config = _get_mock_config()
    manager.restart_service = mocker.MagicMock()  # type: ignore[method-assign]
    mock_write_configs = mocker.MagicMock()
    manager._write_configs = mock_write_configs  # type: ignore

    # Act
    manager.remove_single_system(mock_system)

    # Assert
    mock_write_configs.assert_called_with(
        {
            "cobbler_server": "127.0.0.1:80",
            "date": "Mon Jan  1 00:00:00 2000",
            "dhcp_tags": {
                "default": {},
            },
            "next_server_v4": "127.0.0.1",
            "next_server_v6": "::1",
        }
    )


def test_manager_sync_single_system(mocker: "MockerFixture", api_isc_mock: CobblerAPI):
    """
    Verify that the configuration for a single system can be re-synchronized.
    """
    # pylint: disable=protected-access
    # Arrange
    mocker_mac_address = "bb:bb:cc:dd:ee:ff"
    mocker.patch(
        "time.gmtime",
        return_value=time.struct_time((2000, 1, 1, 0, 0, 0, 0, 1, 1)),
    )
    isc.MANAGER = None
    manager = isc.get_manager(api_isc_mock)
    mock_distro = Distro(api_isc_mock)
    mock_distro.redhat_management_key = ""
    mock_profile = Profile(api_isc_mock)
    mock_profile.autoinstall = ""
    mock_profile._distro = mock_distro.uid  # type: ignore
    mock_profile.proxy = ""
    mock_profile.virt.file_size = ""  # type: ignore
    mocker.patch(
        "cobbler.items.system.System.interfaces",
        new_callable=mocker.PropertyMock(
            return_value={
                "default": NetworkInterface(
                    api=api_isc_mock,
                    system_uid="not-zero",
                    dns={"name": "host.example.org"},
                    mac_address=mocker_mac_address,
                    ipv4={"address": "192.168.1.2"},
                    ipv6={"address": "::1"},
                )
            }
        ),
    )
    mock_system = System(api_isc_mock)
    mock_system.name = "test_manager_regen_hosts_system"
    mock_system._profile = mock_profile.uid  # type: ignore
    mocker.patch.object(mock_system, "get_conceptual_parent", return_value=mock_profile)
    mocker.patch.object(mock_profile, "get_conceptual_parent", return_value=mock_distro)
    manager.config = _get_mock_config()
    manager.restart_service = mocker.MagicMock()  # type: ignore[method-assign]
    mock_write_configs = mocker.MagicMock()
    manager._write_configs = mock_write_configs  # type: ignore

    # Act
    manager.sync_single_system(mock_system)
    systems_config = manager.config["dhcp_tags"]["default"]  # type: ignore

    # Assert
    assert len(systems_config) == 2  # type: ignore
    assert mocker_mac_address in systems_config  # type: ignore
