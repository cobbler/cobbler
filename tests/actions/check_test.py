"""
Tests that validate the functionality of the module that performs sanity checks on a Cobbler installation
(the code behind "cobbler check").
"""

from typing import TYPE_CHECKING, List

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


def test_check_collection_load_errors_surfaces_startup_load_failures(
    mocker: "MockerFixture", cobbler_api: CobblerAPI
):
    """
    Regression test: an item that failed to load from disk at startup used to only be logged at
    ERROR level in cobbler.log, with no other actionable signal. "cobbler check" must surface it.
    """
    # Arrange
    mocker.patch.object(
        cobbler_api,
        "get_collection_load_errors",
        return_value=[
            {
                "collection_type": "distro",
                "name": "broken-distro",
                "uid": "deadbeefdeadbeefdeadbeefdeadbeef",
                "error": "os_version 'bogus' is not a valid os_version for breed 'suse'",
            }
        ],
    )
    test_check = check.CobblerCheck(cobbler_api)
    status: List[str] = []

    # Act
    test_check.check_collection_load_errors(status)

    # Assert
    assert len(status) == 1
    assert "distro" in status[0]
    assert "broken-distro" in status[0]
    assert "deadbeefdeadbeefdeadbeefdeadbeef" in status[0]
    assert "os_version 'bogus' is not a valid os_version for breed 'suse'" in status[0]


def test_check_service_systemd_probe_does_not_log_stderr_as_error(
    mocker: "MockerFixture", cobbler_api: CobblerAPI
):
    """
    Regression test: "systemctl is-active --quiet" returning non-zero for a service that is simply
    not running is an expected, benign result, not an operational error -- check_service() must not
    let it be logged at ERROR level in cobbler.log.
    """
    # Arrange
    mocker.patch("cobbler.actions.check.detection.is_supervisord", return_value=False)
    mocker.patch("cobbler.actions.check.detection.is_systemd", return_value=True)
    subprocess_call_mock = mocker.patch(
        "cobbler.actions.check.utils.subprocess_call", return_value=1
    )
    test_check = check.CobblerCheck(cobbler_api)
    status: List[str] = []

    # Act
    test_check.check_service(status, "dhcpd")

    # Assert
    subprocess_call_mock.assert_called_once_with(
        ["systemctl", "is-active", "--quiet", "dhcpd"],
        shell=False,
        log_stderr_as_error=False,
    )


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
