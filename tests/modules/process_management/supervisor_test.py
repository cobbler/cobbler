"""
Tests that validate the functionality of the supervisord-backed process management module.
"""

from typing import TYPE_CHECKING
from unittest.mock import MagicMock
from xmlrpc.client import Fault

from cobbler.modules.process_management import supervisor

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _mock_server_proxy(mocker: "MockerFixture") -> MagicMock:
    """
    Replace supervisor.ServerProxy with a stub whose context-manager protocol returns a MagicMock standing in
    for the XML-RPC connection, so tests can configure supervisor.getProcessInfo/stopProcess/startProcess
    without a real supervisord instance.
    """
    server = MagicMock()
    server_proxy = MagicMock()
    server_proxy.__enter__.return_value = server
    mocker.patch(
        "cobbler.modules.process_management.supervisor.ServerProxy",
        return_value=server_proxy,
    )
    return server


def test_register():
    # Arrange & Act
    result = supervisor.register()

    # Assert
    assert result == "process_management"


def test_restart_service_running_process_is_stopped_and_started(
    mocker: "MockerFixture",
):
    # Arrange
    server = _mock_server_proxy(mocker)
    server.supervisor.getProcessInfo.return_value = {"state": 20}
    server.supervisor.startProcess.return_value = True
    api_handle = MagicMock()

    # Act
    result = supervisor.restart_service(api_handle, "dhcpd")

    # Assert
    assert result == 0
    server.supervisor.stopProcess.assert_called_once_with("dhcpd")
    server.supervisor.startProcess.assert_called_once_with("dhcpd")


def test_restart_service_stopped_process_is_only_started(mocker: "MockerFixture"):
    # Arrange
    server = _mock_server_proxy(mocker)
    server.supervisor.getProcessInfo.return_value = {"state": 0}
    server.supervisor.startProcess.return_value = True
    api_handle = MagicMock()

    # Act
    result = supervisor.restart_service(api_handle, "dhcpd")

    # Assert
    assert result == 0
    server.supervisor.stopProcess.assert_not_called()


def test_restart_service_start_failure(mocker: "MockerFixture"):
    # Arrange
    server = _mock_server_proxy(mocker)
    server.supervisor.getProcessInfo.return_value = {"state": 0}
    server.supervisor.startProcess.return_value = False
    api_handle = MagicMock()

    # Act
    result = supervisor.restart_service(api_handle, "dhcpd")

    # Assert
    assert result == 1


def test_restart_service_xmlrpc_fault(mocker: "MockerFixture"):
    # Arrange
    server = _mock_server_proxy(mocker)
    server.supervisor.getProcessInfo.side_effect = Fault(1, "boom")
    api_handle = MagicMock()

    # Act
    result = supervisor.restart_service(api_handle, "dhcpd")

    # Assert
    assert result == 1
