"""
Test module to test the functionality of generating the installation log summary.
"""

import lzma

from cobbler.actions import status


def test_scan_logfiles(mocker, cobbler_api):
    """
    Test that validates the scan_logfiles subroutine reads gz/bz2/xz/plain logs.
    """
    # Arrange
    mocker.patch(
        "cobbler.actions.status.gzip.open",
        mocker.mock_open(read_data="test test test test 0.0"),
    )
    mocker.patch(
        "cobbler.actions.status.bz2.open",
        mocker.mock_open(read_data="test test test test 0.0"),
    )
    mocker.patch(
        "cobbler.actions.status.lzma.open",
        mocker.mock_open(read_data="test test test test 0.0"),
    )
    mocker.patch(
        "builtins.open", mocker.mock_open(read_data="test test test test 0.0")
    )
    mocker.patch(
        "cobbler.actions.status.glob.glob",
        return_value=[
            "/var/log/cobbler/install.log.1.gz",
            "/var/log/cobbler/install.log.2.bz2",
            "/var/log/cobbler/install.log.3.xz",
            "/var/log/cobbler/install.log",
        ],
    )
    test_status = status.CobblerStatusReport(cobbler_api, "text")
    mock_catalog = mocker.patch.object(test_status, "catalog")

    # Act
    test_status.scan_logfiles()

    # Assert
    assert mock_catalog.call_count == 4


def test_scan_logfiles_skips_unreadable_file(mocker, cobbler_api):
    """
    Test that scan_logfiles skips unreadable compressed files instead of raising.
    """
    # Arrange
    mocker.patch(
        "builtins.open", mocker.mock_open(read_data="test test test test 0.0")
    )
    mocker.patch(
        "cobbler.actions.status.lzma.open",
        side_effect=lzma.LZMAError("Corrupted data"),
    )
    mock_warning = mocker.patch("cobbler.actions.status.LOGGER.warning")
    mocker.patch(
        "cobbler.actions.status.glob.glob",
        return_value=[
            "/var/log/cobbler/install.log.1.xz",
            "/var/log/cobbler/install.log",
        ],
    )
    test_status = status.CobblerStatusReport(cobbler_api, "text")
    mock_catalog = mocker.patch.object(test_status, "catalog")

    # Act
    test_status.scan_logfiles()

    # Assert
    assert mock_catalog.call_count == 1
    mock_warning.assert_called_once()
