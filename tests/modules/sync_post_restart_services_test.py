from unittest.mock import MagicMock

from cobbler.api import CobblerAPI
from cobbler.modules import sync_post_restart_services


def test_register():
    # Arrange & Act
    result = sync_post_restart_services.register()

    # Assert
    assert result == "/var/lib/cobbler/triggers/sync/post/*"


def test_run(mocker):
    # Arrange
    restart_mock = mocker.patch("cobbler.utils.service_restart", return_value=0)
    api = MagicMock(spec=CobblerAPI)
    api.get_module_name_from_file.side_effect = ["managers.isc", "managers.bind"]
    args = None

    # Act
    result = sync_post_restart_services.run(api, args)

    # Assert
    # FIXME improve assert
    assert restart_mock.call_count == 2
    assert result == 0
