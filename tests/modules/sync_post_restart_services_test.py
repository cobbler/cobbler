"""
Tests that validate the functionality of the module that is responsible for restarting services after config file
regeneration.
"""

from typing import TYPE_CHECKING, List

from cobbler.api import CobblerAPI
from cobbler.modules import sync_post_restart_services

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_register():
    # Arrange & Act
    result = sync_post_restart_services.register()

    # Assert
    assert result == "/var/lib/cobbler/triggers/sync/post/*"


def test_run(mocker: "MockerFixture"):
    # Arrange
    api = mocker.MagicMock(spec=CobblerAPI)
    api.get_module_name_from_file.side_effect = ["managers.isc", "managers.bind"]  # type: ignore
    restart_mock = api.get_process_management_module.return_value.restart_service  # type: ignore
    restart_mock.return_value = 0
    args: List[str] = []

    # Act
    result = sync_post_restart_services.run(api, args)

    # Assert
    # FIXME improve assert
    assert restart_mock.call_count == 1
    assert result == 0
