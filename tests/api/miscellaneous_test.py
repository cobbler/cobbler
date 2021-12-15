from unittest.mock import create_autospec

from cobbler.api import CobblerAPI
from cobbler.actions.buildiso.netboot import NetbootBuildiso
from cobbler.actions.buildiso.standalone import StandaloneBuildiso


def test_buildiso(mocker):
    # Arrange
    netboot_stub = create_autospec(spec=NetbootBuildiso)
    standalone_stub = create_autospec(spec=StandaloneBuildiso)
    mocker.patch("cobbler.api.StandaloneBuildiso", return_value=standalone_stub)
    mocker.patch("cobbler.api.NetbootBuildiso", return_value=netboot_stub)
    cobbler_api = CobblerAPI()

    # Act
    cobbler_api.build_iso()

    # Assert
    assert netboot_stub.run.call_count == 1
    assert standalone_stub.run.call_count == 0
