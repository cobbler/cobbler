from unittest.mock import MagicMock

from cobbler.api import CobblerAPI
from cobbler.modules import sync_post_wingen
from cobbler.settings import Settings


def test_register():
    # Arrange & Act
    result = sync_post_wingen.register()

    # Assert
    assert result == "/var/lib/cobbler/triggers/sync/post/*"


def test_run():
    # Arrange
    settings_mock = MagicMock(name="sync_post_wingen_run_setting_mock", spec=Settings)
    settings_mock.windows_enabled = True
    settings_mock.windows_template_dir = "/etc/cobbler/windows"
    settings_mock.tftpboot_location = ""
    settings_mock.webdir = ""
    api = MagicMock(spec=CobblerAPI)
    api.settings.return_value = settings_mock
    args = None

    # Act
    result = sync_post_wingen.run(api, args)

    # Assert
    # FIXME improve assert
    assert result == 0
