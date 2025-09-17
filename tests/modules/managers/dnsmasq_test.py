"""
Test to verify the functionality of the dnsmasq DHCP & DNS module.
"""

import time

import pytest
from pytest_mock.plugin import MockerFixture

from cobbler import utils
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.network_interface import NetworkInterface
from cobbler.items.profile import Profile
from cobbler.items.system import System
from cobbler.modules.managers import dnsmasq
from cobbler.settings import Settings
from cobbler.templar import Templar


@pytest.fixture(name="cobbler_api")
def fixture_cobbler_api(mocker: "MockerFixture") -> CobblerAPI:
    """
    Mock to prevent the full creation of a CobblerAPI and Settings object.
    """
    settings_mock = mocker.MagicMock(name="cobbler_api_mock", spec=Settings)
    settings_mock.server = "192.168.1.1"
    settings_mock.next_server_v4 = "192.168.1.1"
    settings_mock.next_server_v6 = "::1"
    settings_mock.default_virt_type = "auto"
    settings_mock.restart_dhcp = True
    settings_mock.default_virt_disk_driver = "raw"
    settings_mock.cache_enabled = False
    settings_mock.allow_duplicate_hostnames = True
    settings_mock.allow_duplicate_macs = True
    settings_mock.allow_duplicate_ips = True
    settings_mock.dnsmasq_hosts_file = "/var/lib/cobbler/cobbler_hosts"
    settings_mock.dnsmasq_ethers_file = "/etc/ethers"
    api_mock = mocker.MagicMock(autospec=True, spec=CobblerAPI)
    api_mock.settings.return_value = settings_mock
    return api_mock


@pytest.fixture(name="generate_test_system")
def fixture_generate_test_system(
    mocker: "MockerFixture", cobbler_api: CobblerAPI
) -> System:
    """
    Fixture to generate a test system for the dnsmasq tests.
    """
    test_network_interface = NetworkInterface(
        api=cobbler_api,
        system_uid="not-empty",
        name="default",
        ipv4={"address": "192.168.1.2"},
        ipv6={"address": "::1"},
        dns={"name": "host.example.org"},
        mac_address="AA:BB:CC:DD:EE:FF",
    )
    mocker.patch(
        "cobbler.items.system.System.interfaces",
        new_callable=mocker.PropertyMock(
            return_value={"default": test_network_interface}
        ),
    )
    mock_system = System(cobbler_api)
    mock_system.name = "test_manager_regen_ethers_system"  # type: ignore[method-assign]
    return mock_system


def test_register():
    """
    Test that will assert if the return value of the register method is correct.
    """
    # Arrange & Act
    result = dnsmasq.register()

    # Assert
    assert result == "manage"


def test_manager_what():
    """
    Test if the manager identifies itself correctly.
    """
    # pylint: disable=protected-access
    # Arrange & Act & Assert
    assert dnsmasq._DnsmasqManager.what() == "dnsmasq"  # type: ignore


def test_get_manager(cobbler_api: CobblerAPI):
    """
    Test if the singleton is correctly initialized.
    """
    # pylint: disable=protected-access
    # Arrange & Act
    result = dnsmasq.get_manager(cobbler_api)

    # Assert
    assert isinstance(result, dnsmasq._DnsmasqManager)  # type: ignore


def test_manager_write_configs(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test if the manager is able to correctly write the configuration files.
    """
    # Arrange
    system_dns = "host.example.org"
    system_mac = "aa:bb:cc:dd:ee:ff"
    system_ip4 = "192.168.1.2"
    system_ip6 = "::1"
    mocker.patch(
        "time.gmtime",
        return_value=time.struct_time((2000, 1, 1, 0, 0, 0, 0, 1, 1)),
    )
    mocker.patch("builtins.open", mocker.mock_open(read_data="test"))
    mock_distro = Distro(cobbler_api)
    mock_distro.arch = "x86_64"  # type: ignore[method-assign]
    mock_profile = Profile(cobbler_api)
    mocker.patch(
        "cobbler.items.system.System.interfaces",
        new_callable=mocker.PropertyMock(
            return_value={
                "default": NetworkInterface(
                    api=cobbler_api,
                    system_uid="not-empty",
                    name="default",
                    ipv4={"address": system_ip4},
                    ipv6={"address": system_ip6},
                    dns={"name": system_dns},
                    mac_address=system_mac,
                )
            }
        ),
    )
    mock_system = System(cobbler_api)
    mock_system.name = "test_manager_regen_hosts_system"  # type: ignore[method-assign]
    mocker.patch.object(mock_system, "get_conceptual_parent", return_value=mock_profile)
    mocker.patch.object(mock_profile, "get_conceptual_parent", return_value=mock_distro)
    dnsmasq.MANAGER = None
    test_manager = dnsmasq.get_manager(cobbler_api)
    test_manager.systems = [mock_system]  # type: ignore
    test_manager.templar = mocker.MagicMock(spec=Templar, autospec=True)

    # Act
    test_manager.write_configs()

    # Assert
    test_manager.templar.render.assert_called_once_with(  # type: ignore
        "test",
        {
            "insert_cobbler_system_definitions": f"dhcp-host=net:x86_64,{system_mac},{system_dns},{system_ip4},[{system_ip6}]\n",
            "date": "Mon Jan  1 00:00:00 2000",
            "cobbler_server": cobbler_api.settings().server,
            "next_server_v4": cobbler_api.settings().next_server_v4,
            "next_server_v6": cobbler_api.settings().next_server_v6,
            "addn_host_file": cobbler_api.settings().dnsmasq_hosts_file,
        },
        "/etc/dnsmasq.conf",
    )


def test_manager_sync_single_system(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, generate_test_system: System
):
    """
    Verify that the configuration for a single system can be re-synchronized.
    """
    # Arrange
    mock_system_definition = (
        "dhcp-host=net:x86_64,bb:bb:cc:dd:ee:ff,test.example.org,192.168.1.3,[::1]\n"
    )
    mock_config = {
        "insert_cobbler_system_definitions": mock_system_definition,
        "date": "Mon Jan  1 00:00:00 2000",
        "cobbler_server": cobbler_api.settings().server,
        "next_server_v4": cobbler_api.settings().next_server_v4,
        "next_server_v6": cobbler_api.settings().next_server_v6,
        "addn_host_file": cobbler_api.settings().dnsmasq_hosts_file,
    }
    mocker.patch(
        "time.gmtime",
        return_value=time.struct_time((2000, 1, 1, 0, 0, 0, 0, 1, 1)),
    )
    mocker.patch("builtins.open", mocker.mock_open(read_data="test"))
    mock_distro = Distro(cobbler_api)
    mock_distro.arch = "x86_64"  # type: ignore[method-assign]
    mock_profile = Profile(cobbler_api)
    mock_system = generate_test_system
    mocker.patch.object(mock_system, "get_conceptual_parent", return_value=mock_profile)
    mocker.patch.object(mock_profile, "get_conceptual_parent", return_value=mock_distro)
    dnsmasq.MANAGER = None
    test_manager = dnsmasq.get_manager(cobbler_api)
    mock_write_configs = mocker.MagicMock()
    mock_sync_single_ethers_entry = mocker.MagicMock()
    # pylint: disable-next=protected-access
    test_manager._write_configs = mock_write_configs  # type: ignore[method-assign]
    test_manager.sync_single_ethers_entry = mock_sync_single_ethers_entry  # type: ignore[method-assign]
    test_manager.restart_service = mocker.MagicMock()  # type: ignore[method-assign]
    test_manager.config = mock_config
    system_mac = mock_system.interfaces["default"].mac_address
    system_dns = mock_system.interfaces["default"].dns.name
    system_ip4 = mock_system.interfaces["default"].ipv4.address
    system_ip6 = mock_system.interfaces["default"].ipv6.address

    expected_config = mock_config.copy()
    expected_config[
        "insert_cobbler_system_definitions"
    ] += f"dhcp-host=net:x86_64,{system_mac},{system_dns},{system_ip4},[{system_ip6}]\n"

    # Act
    test_manager.sync_single_system(mock_system)

    # Assert
    mock_sync_single_ethers_entry.assert_called_with(mock_system, [])
    mock_write_configs.assert_called_with(expected_config)


def test_manager_regen_ethers(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, generate_test_system: System
):
    """
    Test to verify that the Ethers configuration can be successfully regnerated.
    """
    # Arrange
    mock_builtins_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_system = generate_test_system
    dnsmasq.MANAGER = None
    test_manager = dnsmasq.get_manager(cobbler_api)
    test_manager.systems = [mock_system]  # type: ignore
    system_mac = mock_system.interfaces["default"].mac_address.upper()
    system_ip4 = mock_system.interfaces["default"].ipv4.address

    # Act
    test_manager.regen_ethers()

    # Assert
    mock_builtins_open.assert_called_once_with(
        cobbler_api.settings().dnsmasq_ethers_file, "w", encoding="UTF-8"
    )
    write_handle = mock_builtins_open()
    write_handle.write.assert_called_once_with(f"{system_mac}\t{system_ip4}\n")


def test_manager_remove_single_ethers_entry(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, generate_test_system: System
):
    """
    Test to verify that a single entry can be removed from the ethers file.
    """
    # Arrange
    mock_remove_line_in_file = mocker.MagicMock()
    mock_system = generate_test_system
    dnsmasq.MANAGER = None
    test_manager = dnsmasq.get_manager(cobbler_api)
    utils.remove_lines_in_file = mock_remove_line_in_file  # type: ignore
    system_mac = mock_system.interfaces["default"].mac_address.upper()

    # Act
    test_manager.remove_single_ethers_entry(mock_system)

    # Assert
    mock_remove_line_in_file.assert_called_once_with(
        cobbler_api.settings().dnsmasq_ethers_file, [system_mac]
    )


def test_manager_remove_single_hosts_entry(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, generate_test_system: System
):
    """
    Test to verify that a single host can be removed from the hosts file.
    """
    # Arrange
    mock_remove_line_in_file = mocker.MagicMock()
    mock_system = generate_test_system
    dnsmasq.MANAGER = None
    test_manager = dnsmasq.get_manager(cobbler_api)
    utils.remove_lines_in_file = mock_remove_line_in_file  # type: ignore
    system_ip_addr = mock_system.interfaces["default"].ipv6.address
    system_dns = mock_system.interfaces["default"].dns.name

    # Act
    test_manager.remove_single_hosts_entry(mock_system)

    # Assert
    mock_remove_line_in_file.assert_called_once_with(
        cobbler_api.settings().dnsmasq_hosts_file, [f"{system_ip_addr}\t{system_dns}\n"]
    )


def test_manager_sync_single_ethers_entry(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, generate_test_system: System
):
    """
    Test to verify that a single entry can be added to the ethers file.
    """
    # Arrange
    mock_builtins_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_system = generate_test_system
    dnsmasq.MANAGER = None
    test_manager = dnsmasq.get_manager(cobbler_api)
    system_mac = mock_system.interfaces["default"].mac_address.upper()
    system_ip4 = mock_system.interfaces["default"].ipv4.address

    # Act
    test_manager.sync_single_ethers_entry(mock_system)

    # Assert
    mock_builtins_open.assert_called_once_with(
        cobbler_api.settings().dnsmasq_ethers_file, "a", encoding="UTF-8"
    )
    write_handle = mock_builtins_open()
    write_handle.write.assert_called_once_with(f"{system_mac}\t{system_ip4}\n")


def test_manager_regen_hosts(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, generate_test_system: System
):
    """
    Test to verify that the hosts file can be successfully regenerated.
    """
    # Arrange
    mock_builtins_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_system = generate_test_system
    dnsmasq.MANAGER = None
    test_manager = dnsmasq.get_manager(cobbler_api)
    test_manager.systems = [mock_system]  # type: ignore
    system_dns = mock_system.interfaces["default"].dns.name
    system_ip6 = mock_system.interfaces["default"].ipv6.address

    # Act
    test_manager.regen_hosts()

    # Assert
    mock_builtins_open.assert_called_once_with(
        cobbler_api.settings().dnsmasq_hosts_file, "w", encoding="UTF-8"
    )
    write_handle = mock_builtins_open()
    write_handle.write.assert_called_once_with(f"{system_ip6}\t{system_dns}\n")


def test_manager_add_single_hosts_entry(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, generate_test_system: System
):
    """
    Test to verify that a single host can be added to the hosts file.
    """
    # Arrange
    mock_builtins_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_system = generate_test_system
    dnsmasq.MANAGER = None
    test_manager = dnsmasq.get_manager(cobbler_api)
    system_dns = mock_system.interfaces["default"].dns.name
    system_ip6 = mock_system.interfaces["default"].ipv6.address

    # Act
    test_manager.add_single_hosts_entry(mock_system)

    # Assert
    mock_builtins_open.assert_called_with(
        cobbler_api.settings().dnsmasq_hosts_file, "a", encoding="UTF-8"
    )
    write_handle = mock_builtins_open()
    write_handle.write.assert_called_with(f"{system_ip6}\t{system_dns}\n")


def test_manager_remove_single_system(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, generate_test_system: System
):
    """
    Verifies that a single system can be successfully removed from the ISC DHCP configuration.
    """
    # Arrange
    mocker.patch(
        "time.gmtime",
        return_value=time.struct_time((2000, 1, 1, 0, 0, 0, 0, 1, 1)),
    )
    mock_system = generate_test_system
    mock_profile = Profile(cobbler_api)
    mock_distro = Distro(cobbler_api)
    mock_distro.arch = "x86_64"  # type: ignore[method-assign]
    dnsmasq.MANAGER = None
    test_manager = dnsmasq.get_manager(cobbler_api)
    test_manager.systems = [mock_system]  # type: ignore
    mock_write_configs = mocker.MagicMock()
    mock_remove_single_ethers_entry = mocker.MagicMock()
    # pylint: disable-next=protected-access
    test_manager._write_configs = mock_write_configs  # type: ignore
    test_manager.remove_single_ethers_entry = mock_remove_single_ethers_entry  # type: ignore[method-assign]
    mocker.patch.object(mock_system, "get_conceptual_parent", return_value=mock_profile)
    mocker.patch.object(mock_profile, "get_conceptual_parent", return_value=mock_distro)

    # Act
    test_manager.remove_single_system(mock_system)

    # Assert
    mock_write_configs.assert_called_once_with(
        {
            "insert_cobbler_system_definitions": "",
            "date": "Mon Jan  1 00:00:00 2000",
            "cobbler_server": cobbler_api.settings().server,
            "next_server_v4": cobbler_api.settings().next_server_v4,
            "next_server_v6": cobbler_api.settings().next_server_v6,
            "addn_host_file": cobbler_api.settings().dnsmasq_hosts_file,
        }
    )
    mock_remove_single_ethers_entry.assert_called_with(mock_system)


def test_manager_restart_service(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test if the manager is able to correctly handle restarting the dnsmasq server on different distros.
    """
    # Arrange
    mock_service_restart = mocker.patch(
        "cobbler.utils.process_management.service_restart", return_value=0
    )
    dnsmasq.MANAGER = None
    test_manager = dnsmasq.get_manager(cobbler_api)

    # Act
    result = test_manager.restart_service()

    # Assert
    assert mock_service_restart.call_count == 1
    mock_service_restart.assert_called_with("dnsmasq")
    assert result == 0
