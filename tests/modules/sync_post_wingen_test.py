"""
Test module to verify the functionality of the sync_post_wingen plugin module.
"""

import os
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


# --------------------------------------------------------------------------------------------
# _resolve_boot_file()
# --------------------------------------------------------------------------------------------


def test_resolve_boot_file_classic_import_uses_links_boot_dir(mocker: "MockerFixture"):
    """
    With no ``source_tree_path`` set (a classic, mirrored import), both derived and non-derived
    files must be resolved under ``webdir/links/<name>/boot``, exactly as before this feature.
    """
    # Arrange
    settings = mocker.MagicMock(spec=Settings)
    settings.webdir = "/var/www/cobbler"
    distro = mocker.MagicMock()
    distro.name = "mydistro"
    distro.source_tree_path = ""

    # Act
    derived_result = sync_post_wingen._resolve_boot_file(  # type: ignore[reportPrivateUsage]
        settings, distro, "bootmgr.exe", derived=True
    )
    non_derived_result = sync_post_wingen._resolve_boot_file(  # type: ignore[reportPrivateUsage]
        settings, distro, "bcd", derived=False
    )

    # Assert
    expected_derived = os.path.join(
        settings.webdir, "links", distro.name, "boot", "bootmgr.exe"
    )
    expected_non_derived = os.path.join(
        settings.webdir, "links", distro.name, "boot", "bcd"
    )
    assert derived_result == expected_derived
    assert non_derived_result == expected_non_derived


def test_resolve_boot_file_direct_source_derived_file_uses_overlay_resolution(
    mocker: "MockerFixture",
):
    """
    For a direct_source distro, a derived file (e.g. ``winpe.wim``) must be resolved through
    ``filesystem_helpers.resolve_distro_overlay_read_path()``.
    """
    # Arrange
    settings = mocker.MagicMock(spec=Settings)
    distro = mocker.MagicMock()
    distro.name = "mydistro"
    distro.source_tree_path = "/some/root"
    overlay_resolve = mocker.patch(
        "cobbler.modules.sync_post_wingen.filesystem_helpers.resolve_distro_overlay_read_path",
        return_value="/some/root/overlay/boot/winpe.wim",
    )

    # Act
    result = sync_post_wingen._resolve_boot_file(  # type: ignore[reportPrivateUsage]
        settings, distro, "winpe.wim", derived=True
    )

    # Assert
    overlay_resolve.assert_called_once_with(
        "/some/root", os.path.join("boot", "winpe.wim")
    )
    assert result == "/some/root/overlay/boot/winpe.wim"


def test_resolve_boot_file_direct_source_non_derived_file_always_uses_original_source_root(
    mocker: "MockerFixture",
):
    """
    For a direct_source distro, a non-derived file (e.g. ``bcd``) must always come from the
    original ``source_tree_path``, never through the overlay -- Cobbler never writes it.
    """
    # Arrange
    settings = mocker.MagicMock(spec=Settings)
    distro = mocker.MagicMock()
    distro.name = "mydistro"
    distro.source_tree_path = "/some/root"
    overlay_resolve = mocker.patch(
        "cobbler.modules.sync_post_wingen.filesystem_helpers.resolve_distro_overlay_read_path"
    )

    # Act
    result = sync_post_wingen._resolve_boot_file(  # type: ignore[reportPrivateUsage]
        settings, distro, "bcd", derived=False
    )

    # Assert
    assert result == os.path.join("/some/root", "boot", "bcd")
    overlay_resolve.assert_not_called()
