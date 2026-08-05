"""
Tests that validate the functionality of the module that performs sanity checks on a Cobbler installation
(the code behind "cobbler check").
"""

from typing import TYPE_CHECKING

from cobbler.actions import check
from cobbler.api import CobblerAPI

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_run_warns_on_dynamic_tftp_with_manage_tftpd_enabled(
    mocker: "MockerFixture", cobbler_api: CobblerAPI
):
    """
    Test that "cobbler check" warns when the 'dynamic_tftp' TFTP manager is selected while manage_tftpd is still
    enabled, since that combination leaves cobbler-tftp's own service unmanaged/conflicting with Cobbler.
    """
    # Arrange
    cobbler_api.settings().manage_tftpd = True
    sync_mock = mocker.MagicMock()
    sync_mock.tftpd.what.return_value = "dynamic_tftp"
    mocker.patch.object(cobbler_api, "get_sync", return_value=sync_mock)
    test_check = check.CobblerCheck(cobbler_api)

    # Act
    status = test_check.run()

    # Assert
    assert any("dynamic_tftp" in message for message in status)


def test_run_does_not_warn_when_manage_tftpd_disabled(
    mocker: "MockerFixture", cobbler_api: CobblerAPI
):
    """
    Test that no warning is emitted for the 'dynamic_tftp' TFTP manager when manage_tftpd is correctly disabled.
    """
    # Arrange
    cobbler_api.settings().manage_tftpd = False
    sync_mock = mocker.MagicMock()
    sync_mock.tftpd.what.return_value = "dynamic_tftp"
    mocker.patch.object(cobbler_api, "get_sync", return_value=sync_mock)
    test_check = check.CobblerCheck(cobbler_api)

    # Act
    status = test_check.run()

    # Assert
    assert not any("dynamic_tftp" in message for message in status)


def test_run_does_not_warn_for_in_tftpd_manager(
    mocker: "MockerFixture", cobbler_api: CobblerAPI
):
    """
    Test that the new guard doesn't fire for the classic 'in_tftpd' manager, regardless of manage_tftpd.
    """
    # Arrange
    cobbler_api.settings().manage_tftpd = True
    sync_mock = mocker.MagicMock()
    sync_mock.tftpd.what.return_value = "in_tftpd"
    mocker.patch.object(cobbler_api, "get_sync", return_value=sync_mock)
    test_check = check.CobblerCheck(cobbler_api)

    # Act
    status = test_check.run()

    # Assert
    assert not any("dynamic_tftp" in message for message in status)
