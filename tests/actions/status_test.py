"""
Test module to test the functionallity of generating the installation log summary.
"""

import pytest
from pytest_mock import MockerFixture

from cobbler.actions import status
from cobbler.actions.status import InstallStatus
from cobbler.api import CobblerAPI


def test_collect_logfiles(mocker: MockerFixture):
    """
    Test that validates the collect_logfiles subroutine.
    """
    # Arrange
    mocker.patch(
        "glob.glob",
        return_value=[
            "/var/log/cobbler/install.log",
            "/var/log/cobbler/install.log1",
            "/var/log/cobbler/install.log.1",
        ],
    )
    expected_result = [
        "/var/log/cobbler/install.log.1",
        "/var/log/cobbler/install.log",
    ]

    # Act
    result = status.CobblerStatusReport.collect_logfiles()

    # Assert
    assert result == expected_result


def test_scan_logfiles(mocker: MockerFixture, cobbler_api: CobblerAPI):
    """
    Test that validates the scan_logfiles subroutine.
    """
    # Arrange
    mocker.patch("gzip.open", mocker.mock_open(read_data="test test test test 0.0"))
    mocker.patch("builtins.open", mocker.mock_open(read_data="test test test test 0.0"))
    test_status = status.CobblerStatusReport(cobbler_api, "text")
    mocker.patch.object(
        test_status, "collect_logfiles", return_value=["/test/test", "/test/test.gz"]
    )
    mock_catalog = mocker.patch.object(test_status, "catalog")

    # Act
    test_status.scan_logfiles()

    # Assert
    assert mock_catalog.call_count == 2


def test_catalog(cobbler_api: CobblerAPI):
    """
    Test that validates the catalog subroutine.
    """
    # Arrange
    test_status = status.CobblerStatusReport(cobbler_api, "text")
    expected_result = InstallStatus()
    expected_result.most_recent_start = 0
    expected_result.most_recent_stop = -1
    expected_result.most_recent_target = "system:test"
    expected_result.seen_start = 0
    expected_result.seen_stop = -1
    expected_result.state = "?"

    # Act
    test_status.catalog("system", "test", "192.168.0.1", "start", 0.0)

    # Assert
    assert "192.168.0.1" in test_status.ip_data
    assert test_status.ip_data["192.168.0.1"] == expected_result


@pytest.mark.parametrize(
    "input_start,input_stop,expected_status",
    [
        (0, 5, "finished"),
        (50, 0, "unknown/stalled"),
        (99900, 0, "installing (1m 40s)"),
    ],
)
def test_process_results(
    mocker: MockerFixture,
    cobbler_api: CobblerAPI,
    input_start: int,
    input_stop: int,
    expected_status: str,
):
    """
    Test that validates the process_results subroutine.
    """
    # Arrange
    mocker.patch("time.time", return_value=100000)
    test_status = status.CobblerStatusReport(cobbler_api, "text")
    new_status = InstallStatus()
    new_status.most_recent_start = input_start
    new_status.most_recent_stop = input_stop
    new_status.most_recent_target = ""
    new_status.seen_start = -1
    new_status.seen_stop = -1
    new_status.state = "?"
    test_status.ip_data["192.168.0.1"] = new_status

    # Act
    test_status.process_results()

    # Assert
    assert test_status.ip_data["192.168.0.1"].state == expected_status


def test_get_printable_results(cobbler_api: CobblerAPI):
    """
    Test that validates the get_printable_results subroutine.
    """
    # Arrange
    test_status = status.CobblerStatusReport(cobbler_api, "text")

    # Act
    result = test_status.get_printable_results()

    # Assert
    result_list = result.split("\n")
    assert len(result_list) == 1


@pytest.mark.parametrize(
    "input_mode,expected_result", [("text", str), ("non-text", dict)]  # type: ignore
)
def test_run(
    mocker: MockerFixture,
    cobbler_api: CobblerAPI,
    input_mode: str,
    expected_result: type,
):
    """
    Test that validates the class that generates the report as a whole.
    """
    # Arrange
    test_status = status.CobblerStatusReport(cobbler_api, input_mode)
    mocker.patch.object(test_status, "scan_logfiles")
    if input_mode == "text":
        mocker.patch.object(test_status, "process_results", return_value="")
    else:
        mocker.patch.object(test_status, "process_results", return_value={})

    # Act
    result = test_status.run()

    # Assert
    assert isinstance(result, expected_result)
