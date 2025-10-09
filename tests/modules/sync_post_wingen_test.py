"""
Test module to verify the functionality of the sync_post_wingen plugin module.
"""

from typing import TYPE_CHECKING

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.template import Template
from cobbler.modules import sync_post_wingen
from cobbler.settings import Settings
from cobbler.templates import Templar
from cobbler.tftpgen import TFTPGen

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_register():
    """
    Test if the module registers with the correct ID.
    """
    # Arrange & Act
    result = sync_post_wingen.register()

    # Assert
    assert result == "/var/lib/cobbler/triggers/sync/post/*"


def test_run(mocker: "MockerFixture"):
    """
    Test that the module can be executed sucessfully if all dependencies are available.
    """
    # Arrange
    settings_mock = mocker.MagicMock(
        name="sync_post_wingen_run_setting_mock", spec=Settings
    )
    settings_mock.windows_enabled = True
    settings_mock.windows_template_dir = "/etc/cobbler/windows"
    settings_mock.tftpboot_location = ""
    settings_mock.webdir = ""
    api = mocker.MagicMock(spec=CobblerAPI)
    test_template = Template(
        api,
        tags={
            enums.TemplateTag.ACTIVE.value,
            enums.TemplateTag.WINDOWS_ANSWERFILE.value,
            enums.TemplateTag.WINDOWS_POST_INST_CMD.value,
            enums.TemplateTag.WINDOWS_POST_INST_CMD.value,
        },
    )
    test_template._Template__content = "test"  # type: ignore
    api.find_template.return_value = [test_template]
    api.templar = mocker.MagicMock(autospec=True, spec=Templar)
    api.tftpgen = mocker.MagicMock(spec=TFTPGen, autospec=True)
    api.settings.return_value = settings_mock
    args = None

    # Act
    result = sync_post_wingen.run(api, args)

    # Assert
    # FIXME improve assert
    assert result == 0
