"""
Tests that validate the shipped logging_config.conf, in particular the dedicated "nsupdate" logger.
"""

import configparser

LOGGING_CONFIG_PATH = "/code/cobbler/data/config/cobbler/logging_config.conf"


def _read_logging_config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read(LOGGING_CONFIG_PATH)
    return parser


def test_nsupdate_logger_is_declared():
    # Arrange
    config = _read_logging_config()

    # Act & Assert
    assert "nsupdate" in config["loggers"]["keys"].split(",")
    assert config["logger_nsupdate"]["qualname"] == "nsupdate"


def test_nsupdate_logger_does_not_propagate_to_root():
    """
    The nsupdate logger must not propagate to the root logger, so dynamic DNS update activity stays out of
    cobbler.log and only appears in its own dedicated file (and on stdout).
    """
    # Arrange
    config = _read_logging_config()

    # Act & Assert
    assert config["logger_nsupdate"]["propagate"] == "0"


def test_nsupdate_logger_has_a_dedicated_file_handler_and_stdout():
    # Arrange
    config = _read_logging_config()
    handler_keys = [
        key.strip() for key in config["logger_nsupdate"]["handlers"].split(",")
    ]

    # Act & Assert
    assert "NsupdateFileLogger" in handler_keys
    assert "stdout" in handler_keys
    assert "NsupdateFileLogger" in config["handlers"]["keys"].split(",")
    assert config["handler_NsupdateFileLogger"]["class"] == "FileHandler"
    args = config["handler_NsupdateFileLogger"]["args"]
    assert "/var/log/cobbler/nsupdate.log" in args
