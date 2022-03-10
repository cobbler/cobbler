from unittest.mock import MagicMock

import pytest

from cobbler.cexceptions import CX
from cobbler.api import CobblerAPI
from cobbler.modules import scm_track
from cobbler.settings import Settings


def test_register():
    # Arrange & Act
    result = scm_track.register()

    # Assert
    assert result == "/var/lib/cobbler/triggers/change/*"


def test_run_unsupported():
    # Arrange
    settings_mock = MagicMock(name="scm_track_unsupported_setting_mock", spec=Settings)
    settings_mock.scm_track_enabled = True
    settings_mock.scm_track_mode = "not-allowed"
    settings_mock.scm_track_author = "Cobbler Project <cobbler.project@gmail.com>"
    settings_mock.scm_push_script = "/bin/true"
    api = MagicMock(spec=CobblerAPI)
    api.settings.return_value = settings_mock
    args = None

    # Act & Assert
    with pytest.raises(CX):
        result = scm_track.run(api, args)


def test_run_git():
    # Arrange
    settings_mock = MagicMock(name="scm_track_git_setting_mock", spec=Settings)
    settings_mock.scm_track_enabled = True
    settings_mock.scm_track_mode = "git"
    settings_mock.scm_track_author = "Cobbler Project <cobbler.project@gmail.com>"
    settings_mock.scm_push_script = "/bin/true"
    api = MagicMock(spec=CobblerAPI)
    api.settings.return_value = settings_mock
    args = None

    # Act
    result = scm_track.run(api, args)

    # Assert
    # FIXME improve assert
    assert result == 0


def test_run_hg(mocker):
    # Arrange
    settings_mock = MagicMock(name="scm_track_hg_setting_mock", spec=Settings)
    settings_mock.scm_track_enabled = True
    settings_mock.scm_track_mode = "hg"
    settings_mock.scm_track_author = "Cobbler Project <cobbler.project@gmail.com>"
    settings_mock.scm_push_script = "/bin/true"
    api = MagicMock(spec=CobblerAPI)
    api.settings.return_value = settings_mock
    args = None
    subprocess_call = mocker.patch("cobbler.utils.subprocess_call")

    # Act
    result = scm_track.run(api, args)

    # Assert
    subprocess_call.assert_has_calls(
        [mocker.call(["hg", "init"], shell=False),
         mocker.call(["hg", "add collections"], shell=False),
         mocker.call(["hg", "add templates"], shell=False),
         mocker.call(["hg", "add snippets"], shell=False),
         mocker.call(["hg", "commit", "-m", "API", "update", "--user", settings_mock.scm_track_author], shell=False),
         mocker.call(["/bin/true"], shell=False)]
    )
    assert result == 0
