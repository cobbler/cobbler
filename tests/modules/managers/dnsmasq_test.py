"""
Test to verify the functionallity of the dnsmasq module.
"""

import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.network_interface import NetworkInterface
from cobbler.items.profile import Profile
from cobbler.items.system import System
from cobbler.modules.managers import dnsmasq
from cobbler.templar import Templar

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_register():
    """
    Test if the manager registers with the correct ID.
    """
    # Arrange & Act
    result = dnsmasq.register()

    # Assert
    assert result == "manage"


def test_manager_what():
    """
    Test if the manager identifies itself correctly.
    """
    # Arrange & Act & Assert
    # pylint: disable=protected-access
    assert dnsmasq._DnsmasqManager.what() == "dnsmasq"  # type: ignore


def test_get_manager(cobbler_api: CobblerAPI):
    """
    Test if the singleton is correctly initialized.
    """
    # Arrange & Act
    # pylint: disable=protected-access
    result = dnsmasq.get_manager(cobbler_api)

    # Assert
    isinstance(result, dnsmasq._DnsmasqManager)  # type: ignore


def test_manager_write_configs(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test if the manager is able to correctly write the configuration files.
    """
    # Arrange
    mocker.patch(
        "time.gmtime",
        return_value=time.struct_time((2000, 1, 1, 0, 0, 0, 0, 1, 1)),
    )
    mocker.patch("builtins.open", mocker.mock_open(read_data="test"))
    mock_distro = Distro(cobbler_api)
    mock_distro.arch = "x86_64"
    mock_profile = Profile(cobbler_api)
    mock_system = System(cobbler_api)
    mock_system.name = "test_manager_regen_hosts_system"
    mock_system.interfaces = {"default": NetworkInterface(cobbler_api)}
    mock_system.interfaces["default"].dns_name = "host.example.org"
    mock_system.interfaces["default"].mac_address = "aa:bb:cc:dd:ee:ff"
    mock_system.interfaces["default"].ip_address = "192.168.1.2"
    mock_system.interfaces["default"].ipv6_address = "::1"
    mocker.patch.object(mock_system, "get_conceptual_parent", return_value=mock_profile)
    mocker.patch.object(mock_profile, "get_conceptual_parent", return_value=mock_distro)
    dnsmasq.MANAGER = None
    test_manager = dnsmasq.get_manager(cobbler_api)
    # Type can be ignored because in this case we just loop over the systems.
    test_manager.systems = [mock_system]  # type: ignore
    test_manager.templar = MagicMock(spec=Templar, autospec=True)

    # Act
    test_manager.write_configs()

    # Assert
    test_manager.templar.render.assert_called_once_with(
        "test",
        {
            "insert_cobbler_system_definitions": "dhcp-host=net:x86_64,aa:bb:cc:dd:ee:ff,host.example.org,192.168.1.2,[::1]\n",
            "date": "Mon Jan  1 00:00:00 2000",
            "cobbler_server": "192.168.1.1",
            "next_server_v4": "192.168.1.1",
            "next_server_v6": "::1",
        },
        "/etc/dnsmasq.conf",
    )


def test_manager_regen_ethers(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test that the ethers file is correctly regenerated.
    """
    # Arrange
    mock_builtins_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_system = System(cobbler_api)
    mock_system.name = "test_manager_regen_ethers_system"
    mock_system.interfaces = {"default": NetworkInterface(cobbler_api)}
    mock_system.interfaces["default"].dns_name = "host.example.org"
    mock_system.interfaces["default"].mac_address = "aa:bb:cc:dd:ee:ff"
    mock_system.interfaces["default"].ip_address = "192.168.1.2"
    mock_system.interfaces["default"].ipv6_address = "::1"
    dnsmasq.MANAGER = None
    test_manager = dnsmasq.get_manager(cobbler_api)
    # Type can be ignored because in this case we just loop over the systems.
    test_manager.systems = [mock_system]  # type: ignore

    # Act
    test_manager.regen_ethers()

    # Assert
    mock_builtins_open.assert_called_once_with("/etc/ethers", "w", encoding="UTF-8")
    write_handle = mock_builtins_open()
    write_handle.write.assert_called_once_with("AA:BB:CC:DD:EE:FF\t192.168.1.2\n")


def test_manager_regen_hosts(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test that the hosts file is correctly overwritten.
    """
    # Arrange
    mock_builtins_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_system = System(cobbler_api)
    mock_system.name = "test_manager_regen_hosts_system"
    mock_system.interfaces = {"default": NetworkInterface(cobbler_api)}
    mock_system.interfaces["default"].dns_name = "host.example.org"
    mock_system.interfaces["default"].mac_address = "AA:BB:CC:DD:EE:FF"
    mock_system.interfaces["default"].ip_address = "192.168.1.2"
    mock_system.interfaces["default"].ipv6_address = "::1"
    dnsmasq.MANAGER = None
    test_manager = dnsmasq.get_manager(cobbler_api)
    # Type can be ignored because in this case we just loop over the systems.
    test_manager.systems = [mock_system]  # type: ignore

    # Act
    test_manager.regen_hosts()

    # Assert
    mock_builtins_open.assert_called_once_with(
        "/var/lib/cobbler/cobbler_hosts", "w", encoding="UTF-8"
    )
    write_handle = mock_builtins_open()
    write_handle.write.assert_called_once_with("::1\thost.example.org\n")


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
