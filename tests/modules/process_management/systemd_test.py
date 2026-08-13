"""
Tests that validate the functionality of the systemd-backed process management module.
"""

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from cobbler.modules.process_management import systemd

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_register():
    # Arrange & Act
    result = systemd.register()

    # Assert
    assert result == "process_management"


def test_restart_service_success(mocker: "MockerFixture"):
    # Arrange
    subprocess_mock = mocker.patch(
        "cobbler.modules.process_management.systemd.utils.subprocess_call",
        autospec=True,
        return_value=0,
    )
    api_handle = MagicMock()

    # Act
    result = systemd.restart_service(api_handle, "testservice")

    # Assert
    assert result == 0
    subprocess_mock.assert_called_with(
        ["systemctl", "restart", "testservice"], shell=False
    )


def test_restart_service_failure(mocker: "MockerFixture"):
    # Arrange
    mocker.patch(
        "cobbler.modules.process_management.systemd.utils.subprocess_call",
        autospec=True,
        return_value=1,
    )
    api_handle = MagicMock()

    # Act
    result = systemd.restart_service(api_handle, "testservice")

    # Assert
    assert result == 1
