"""
Test module to verify the functionality of the sync_post_wingen plugin module.
"""

import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, TextIO, Union

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.template import Template
from cobbler.modules import sync_post_wingen
from cobbler.settings import Settings
from cobbler.templates import Templar
from cobbler.tftpgen import TFTPGen

if TYPE_CHECKING:
    import pathlib

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


# --------------------------------------------------------------------------------------------
# run() / gen_win_files() -- distro_dir creation
# --------------------------------------------------------------------------------------------


def test_run_creates_tftpboot_images_dir_when_missing(
    mocker: "MockerFixture", tmp_path: "pathlib.Path"
):
    """
    Regression guard: under managers.dynamic_tftp, write_boot_files() (which normally creates
    "tftpboot_location/images/<name>" earlier in the same sync run) is a no-op, since TFTP content
    is served on demand instead of being materialized. gen_win_files() still unconditionally wrote
    into that directory (the answerfile, the patched bootmgr/loader, winpe.wim, etc.) without ever
    creating it itself, so every such write failed with FileNotFoundError the first time a sync ran
    under the dynamic TFTP manager. Exercise just the vulnerable path (an "answerfile" write, the
    first file gen_win_files() writes into distro_dir) against a tftpboot_location that does not
    already contain the distro's images directory.
    """
    # Arrange
    tftpboot_location = tmp_path / "tftpboot"
    webdir = tmp_path / "webdir"
    distro_source = tmp_path / "distro_mirror" / "win11-x86_64"
    distro_source.mkdir(parents=True)
    assert not (tftpboot_location / "images" / "win11-x86_64").exists()

    settings_mock = mocker.MagicMock(
        name="sync_post_wingen_run_setting_mock", spec=Settings
    )
    settings_mock.windows_enabled = True
    settings_mock.windows_template_dir = "/etc/cobbler/windows"
    settings_mock.tftpboot_location = str(tftpboot_location)
    settings_mock.webdir = str(webdir)
    settings_mock.cache_enabled = False

    api = mocker.MagicMock(spec=CobblerAPI)
    api.settings.return_value = settings_mock

    answerfile_template = Template(
        api,
        tags={
            enums.TemplateTag.ACTIVE.value,
            enums.TemplateTag.WINDOWS_ANSWERFILE.value,
        },
    )
    answerfile_template._Template__content = "rendered answerfile"  # type: ignore
    post_inst_template = Template(
        api,
        tags={
            enums.TemplateTag.ACTIVE.value,
            enums.TemplateTag.WINDOWS_POST_INST_CMD.value,
        },
    )
    post_inst_template._Template__content = "rendered post-install"  # type: ignore
    startnet_template = Template(
        api,
        tags={
            enums.TemplateTag.ACTIVE.value,
            enums.TemplateTag.WINDOWS_STARTNET.value,
        },
    )
    startnet_template._Template__content = "rendered startnet"  # type: ignore

    def _find_template(_active: bool, _default: bool, tags: str) -> List[Template]:
        if tags == enums.TemplateTag.WINDOWS_ANSWERFILE.value:
            return [answerfile_template]
        if tags == enums.TemplateTag.WINDOWS_POST_INST_CMD.value:
            return [post_inst_template]
        if tags == enums.TemplateTag.WINDOWS_STARTNET.value:
            return [startnet_template]
        return []

    api.find_template.side_effect = _find_template
    api.templar = mocker.MagicMock(autospec=True, spec=Templar)

    def _render(
        data_input: Union[TextIO, str],
        search_table: Dict[str, Any],
        out_path: Optional[str],
    ) -> str:
        return data_input if isinstance(data_input, str) else data_input.read()

    api.templar.render.side_effect = _render
    api.tftpgen = mocker.MagicMock(spec=TFTPGen, autospec=True)

    distro = mocker.MagicMock()
    distro.name = "win11-x86_64"
    distro.breed = "windows"
    distro.os_version = "11"
    distro.kernel = str(tftpboot_location / "wimboot")
    distro.source_tree_path = str(distro_source)
    distro.find_distro_path.return_value = str(distro_source)

    profile = mocker.MagicMock()
    profile.name = "win11-x86_64"
    profile.get_conceptual_parent.return_value = distro

    api.profiles.return_value = [profile]
    api.systems.return_value = []

    mocker.patch(
        "cobbler.modules.sync_post_wingen.utils.blender",
        return_value={"autoinstall_meta": {"answerfile": "autounattended.xml"}},
    )

    # Act
    result = sync_post_wingen.run(api, None)

    # Assert
    assert result == 0
    answerfile_path = (
        tftpboot_location / "images" / "win11-x86_64" / "autounattended.xml"
    )
    assert answerfile_path.is_file()
    assert answerfile_path.read_text(encoding="UTF-8") == "rendered answerfile"
