"""
Tests that validate the functionality of the default/backward-compatible process management module, which
restarts services the traditional way: via supervisord, systemd or SysV.
"""

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from cobbler.modules.process_management import service

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_register():
    # Arrange & Act
    result = service.register()

    # Assert
    assert result == "process_management"


def test_restart_service_no_manager(mocker: "MockerFixture"):
    # Arrange
    mocker.patch(
        "cobbler.modules.process_management.service.detection.is_supervisord",
        autospec=True,
        return_value=False,
    )
    mocker.patch(
        "cobbler.modules.process_management.service.detection.is_systemd",
        autospec=True,
        return_value=False,
    )
    mocker.patch(
        "cobbler.modules.process_management.service.detection.is_service",
        autospec=True,
        return_value=False,
    )
    api_handle = MagicMock()

    # Act
    result = service.restart_service(api_handle, "testservice")

    # Assert
    assert result == 1


def test_restart_service_supervisord(mocker: "MockerFixture"):
    # Arrange
    mocker.patch(
        "cobbler.modules.process_management.service.detection.is_supervisord",
        autospec=True,
        return_value=True,
    )
    mocked_supervisor_restart = mocker.patch(
        "cobbler.modules.process_management.service.supervisor.restart_service",
        autospec=True,
        return_value=0,
    )
    api_handle = MagicMock()

    # Act
    result = service.restart_service(api_handle, "dhcpd")

    # Assert
    assert result == 0
    mocked_supervisor_restart.assert_called_once_with(api_handle, "dhcpd")


def test_restart_service_systemctl(mocker: "MockerFixture"):
    # Arrange
    mocker.patch(
        "cobbler.modules.process_management.service.detection.is_supervisord",
        autospec=True,
        return_value=False,
    )
    mocker.patch(
        "cobbler.modules.process_management.service.detection.is_systemd",
        autospec=True,
        return_value=True,
    )
    mocked_systemd_restart = mocker.patch(
        "cobbler.modules.process_management.service.systemd.restart_service",
        autospec=True,
        return_value=0,
    )
    api_handle = MagicMock()

    # Act
    result = service.restart_service(api_handle, "testservice")

    # Assert
    assert result == 0
    mocked_systemd_restart.assert_called_once_with(api_handle, "testservice")


def test_restart_service_service(mocker: "MockerFixture"):
    # Arrange
    mocker.patch(
        "cobbler.modules.process_management.service.detection.is_supervisord",
        autospec=True,
        return_value=False,
    )
    mocker.patch(
        "cobbler.modules.process_management.service.detection.is_systemd",
        autospec=True,
        return_value=False,
    )
    mocker.patch(
        "cobbler.modules.process_management.service.detection.is_service",
        autospec=True,
        return_value=True,
    )
    subprocess_mock = mocker.patch(
        "cobbler.modules.process_management.service.utils.subprocess_call",
        autospec=True,
        return_value=0,
    )
    api_handle = MagicMock()

    # Act
    result = service.restart_service(api_handle, "testservice")

    # Assert
    assert result == 0
    subprocess_mock.assert_called_with(
        ["service", "testservice", "restart"], shell=False
    )
