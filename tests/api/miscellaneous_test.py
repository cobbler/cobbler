import logging
from unittest.mock import create_autospec

import pytest

from cobbler import settings
from cobbler.api import CobblerAPI
from cobbler.actions.buildiso.netboot import NetbootBuildiso
from cobbler.actions.buildiso.standalone import StandaloneBuildiso


@pytest.mark.parametrize("input_automigration,result_migrate_count,result_validate_count", [
    (None, 0, 3),
    (True, 1, 2),
    (False, 0, 3),
])
def test_settings_migration(caplog, mocker, input_automigration, result_migrate_count, result_validate_count):
    # Arrange
    caplog.set_level(logging.DEBUG)
    # TODO: Create test where the YAML is missing the key
    spy_migrate = mocker.spy(settings, "migrate")
    spy_validate = mocker.spy(settings, "validate_settings")
    # Override private class variables to have a clean slate on all runs
    CobblerAPI._CobblerAPI__shared_state = {}
    CobblerAPI._CobblerAPI__has_loaded = False

    # Act
    CobblerAPI(execute_settings_automigration=input_automigration)

    # Assert
    assert len(caplog.records) > 0
    if input_automigration is not None:
        assert 'Daemon flag overwriting other possible values from "settings.yaml" for automigration!' in caplog.text
    assert spy_migrate.call_count == result_migrate_count
    assert spy_validate.call_count == result_validate_count


def test_buildiso(mocker, cobbler_api):
    # Arrange
    netboot_stub = create_autospec(spec=NetbootBuildiso)
    standalone_stub = create_autospec(spec=StandaloneBuildiso)
    mocker.patch("cobbler.api.StandaloneBuildiso", return_value=standalone_stub)
    mocker.patch("cobbler.api.NetbootBuildiso", return_value=netboot_stub)

    # Act
    cobbler_api.build_iso()

    # Assert
    assert netboot_stub.run.call_count == 1
    assert standalone_stub.run.call_count == 0
