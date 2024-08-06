"""
Tests that validate the functionality of the module that is responsible for managing the djbdns config files.
"""

from typing import TYPE_CHECKING, Any

from cobbler.api import CobblerAPI
from cobbler.items.network_interface import NetworkInterface
from cobbler.items.system import System
from cobbler.modules.managers import ndjbdns
from cobbler.templar import Templar

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_register():
    # Arrange
    # Act
    result = ndjbdns.register()

    # Assert
    assert result == "manage"


def test_get_manager(cobbler_api: CobblerAPI):
    # Arrange & Act
    result = ndjbdns.get_manager(cobbler_api)

    # Assert
    # pylint: disable-next=protected-access
    isinstance(result, ndjbdns._NDjbDnsManager)  # type: ignore[reportPrivateUsage]


def test_manager_what():
    # Arrange & Act & Assert
    # pylint: disable-next=protected-access
    assert ndjbdns._NDjbDnsManager.what() == "ndjbdns"  # type: ignore[reportPrivateUsage]


class MockedPopen:
    """
    See https://stackoverflow.com/a/53793739
    """

    # pylint: disable=unused-argument,redefined-builtin

    def __init__(self, args: Any, **kwargs: Any):
        self.args = args
        self.returncode = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type: Any, value: Any, traceback: Any):
        pass

    def communicate(self, input: Any = None, timeout: Any = None):
        stdout = "output"
        stderr = "error"
        self.returncode = 0

        return stdout, stderr


def test_manager_write_configs(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    # Arrange
    mocker.patch("builtins.open", mocker.mock_open(read_data="test"))
    mocker.patch("subprocess.Popen", MockedPopen)
    mock_system = System(cobbler_api)
    mock_system.name = "test_manager_regen_hosts_system"
    mock_system.interfaces = {
        "default": NetworkInterface(cobbler_api, mock_system.name)
    }
    mock_system.interfaces["default"].dns_name = "host.example.org"
    mock_system.interfaces["default"].mac_address = "aa:bb:cc:dd:ee:ff"
    mock_system.interfaces["default"].ip_address = "192.168.1.2"
    mock_system.interfaces["default"].ipv6_address = "::1"
    ndjbdns.MANAGER = None
    test_manager = ndjbdns.get_manager(cobbler_api)
    test_manager.templar = mocker.MagicMock(spec=Templar, autospec=True)
    test_manager.systems = [mock_system]  # type: ignore[reportAttributeAccessIssue]

    # Act
    test_manager.write_configs()

    # Assert
    test_manager.templar.render.assert_called_once_with(
        "test", {"forward": [("host.example.org", "192.168.1.2")]}, "/etc/ndjbdns/data"
    )
