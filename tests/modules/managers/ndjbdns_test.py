"""
Tests that validate the functionality of the module that is responsible for managing the djbdns config files.
"""

from typing import TYPE_CHECKING, Any

import pytest

from cobbler.api import CobblerAPI
from cobbler.items.network_interface import NetworkInterface
from cobbler.items.system import System
from cobbler.modules.managers import ndjbdns

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_register():
    """
    Test that will assert if the return value of the register method is correct.
    """
    # Arrange
    # Act
    result = ndjbdns.register()

    # Assert
    assert result == "manage"


def test_get_manager(cobbler_api: CobblerAPI):
    """
    Test if the singleton is correctly initialized.
    """
    # Arrange & Act
    result = ndjbdns.get_manager(cobbler_api)

    # Assert
    # pylint: disable-next=protected-access
    isinstance(result, ndjbdns._NDjbDnsManager)  # type: ignore[reportPrivateUsage]


def test_manager_what():
    """
    Test if the manager identifies itself correctly.
    """
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
        """
        Mock implementation for the communicate method.
        """
        stdout = "output"
        stderr = "error"
        self.returncode = 0

        return stdout, stderr


def test_manager_write_configs(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test if the manager is able to correctly write the configuration files.
    """
    # Arrange
    search_result = cobbler_api.find_template(False, False, name="built-in-ndjbdns")
    if search_result is None or isinstance(search_result, list):
        pytest.fail("Couldn't find ndjbdns template for test arrange")
    # pylint: disable-next=protected-access
    search_result._Template__content = "test"  # type: ignore
    mocker.patch("subprocess.Popen", MockedPopen)
    mocker.patch(
        "cobbler.items.system.System.interfaces",
        new_callable=mocker.PropertyMock(
            return_value={
                "default": NetworkInterface(
                    api=cobbler_api,
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
    mock_system = System(cobbler_api)
    mock_system.name = "test_manager_regen_hosts_system"
    ndjbdns.MANAGER = None
    test_manager = ndjbdns.get_manager(cobbler_api)
    test_manager.systems = [mock_system]  # type: ignore[reportAttributeAccessIssue,assignment]
    templar_mock = mocker.MagicMock()
    mocker.patch.object(test_manager.api, "templar", new=templar_mock)

    # Act
    test_manager.write_configs()

    # Assert
    templar_mock.render.assert_called_once_with(
        "test", {"forward": [("host.example.org", "192.168.1.2")]}, "/etc/ndjbdns/data"
    )
