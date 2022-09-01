import pytest

from cobbler.actions import status


def test_collect_logfiles():
    # Arrange
    # Act
    status.CobblerStatusReport.collect_logfiles()

    # Assert
    assert False


def test_scan_logfiles(mocker, cobbler_api):
    # Arrange
    test_status = status.CobblerStatusReport(cobbler_api, "text")
    mocker.patch.object(test_status, "collect_logfiles", return_value=[])

    # Act
    test_status.scan_logfiles()

    # Assert
    assert False


def test_catalog(cobbler_api):
    # Arrange
    test_status = status.CobblerStatusReport(cobbler_api, "text")

    # Act
    test_status.catalog("system", "test", None, "", 0.0)

    # Assert
    assert False


def test_process_results(cobbler_api):
    # Arrange
    test_status = status.CobblerStatusReport(cobbler_api, "text")

    # Act
    test_status.process_results()

    # Assert
    assert False


def test_get_printable_results(cobbler_api):
    # Arrange
    test_status = status.CobblerStatusReport(cobbler_api, "text")

    # Act
    result = test_status.get_printable_results()

    # Assert
    assert False


@pytest.mark.parametrize(
    "input_mode,expected_result", [("text", str), ("non-text", dict)]
)
def test_run(mocker, cobbler_api, input_mode, expected_result):
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
