"""
Tests that validate the functionality of the module that is responsible for synchronizing the different daemons
with each other.
"""

import pathlib
import shutil
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from cobbler.actions import sync
from cobbler.api import CobblerAPI
from cobbler.items.system import System

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _make_sync(
    cobbler_api: CobblerAPI,
    tmp_path: pathlib.Path,
    httpd_what: str = "in_httpd",
    tftpd_what: str = "in_tftpd",
) -> sync.CobblerSync:
    """
    Build a CobblerSync instance rooted at real, empty temp directories (never the real
    /var/www/cobbler or /srv/tftpboot), with mock dhcp/dns/tftpd/httpd managers whose ``what()``
    can be controlled per test.
    """
    webdir = tmp_path / "webdir"
    tftpboot = tmp_path / "tftpboot"
    webdir.mkdir()
    tftpboot.mkdir()
    cobbler_api.settings().webdir = str(webdir)
    cobbler_api.settings().tftpboot_location = str(tftpboot)

    dhcp = MagicMock()
    dns = MagicMock()
    tftpd = MagicMock()
    tftpd.what.return_value = tftpd_what
    httpd = MagicMock()
    httpd.what.return_value = httpd_what

    return sync.CobblerSync(cobbler_api, dhcp=dhcp, dns=dns, tftpd=tftpd, httpd=httpd)


def test_init_does_not_touch_filesystem(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path, mocker: "MockerFixture"
):
    """
    Constructing CobblerSync must not have any filesystem side effects. Directory bootstrapping
    only happens via the explicit bootstrap_dirs(), called by run() (the full-sync entry point) -
    not on construction, since every per-item "quick sync" also constructs a CobblerSync.
    """
    # Arrange
    create_web_dirs = mocker.patch(
        "cobbler.actions.sync.filesystem_helpers.create_web_dirs"
    )
    create_tftpboot_dirs = mocker.patch(
        "cobbler.actions.sync.filesystem_helpers.create_tftpboot_dirs"
    )

    # Act
    _make_sync(cobbler_api, tmp_path)

    # Assert
    create_web_dirs.assert_not_called()
    create_tftpboot_dirs.assert_not_called()


def test_bootstrap_dirs_skips_directory_creation_for_dynamic_modules(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path, mocker: "MockerFixture"
):
    """
    bootstrap_dirs() must not materialize webdir/tftpboot skeleton directories when the
    corresponding manager is a dynamic (copy-free) one.
    """
    # Arrange
    create_web_dirs = mocker.patch(
        "cobbler.actions.sync.filesystem_helpers.create_web_dirs"
    )
    create_tftpboot_dirs = mocker.patch(
        "cobbler.actions.sync.filesystem_helpers.create_tftpboot_dirs"
    )
    sync_obj = _make_sync(
        cobbler_api, tmp_path, httpd_what="dynamic_httpd", tftpd_what="dynamic_tftp"
    )

    # Act
    sync_obj.bootstrap_dirs()

    # Assert
    create_web_dirs.assert_not_called()
    create_tftpboot_dirs.assert_not_called()


def test_bootstrap_dirs_creates_directories_for_default_modules(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path, mocker: "MockerFixture"
):
    """
    The default (non-dynamic) managers must get their directory skeletons created when
    bootstrap_dirs() is called.
    """
    # Arrange
    create_web_dirs = mocker.patch(
        "cobbler.actions.sync.filesystem_helpers.create_web_dirs"
    )
    create_tftpboot_dirs = mocker.patch(
        "cobbler.actions.sync.filesystem_helpers.create_tftpboot_dirs"
    )
    sync_obj = _make_sync(
        cobbler_api, tmp_path, httpd_what="in_httpd", tftpd_what="in_tftpd"
    )

    # Act
    sync_obj.bootstrap_dirs()

    # Assert
    create_web_dirs.assert_called_once()
    create_tftpboot_dirs.assert_called_once()


def test_run_calls_bootstrap_dirs(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path, mocker: "MockerFixture"
):
    """
    run() (the full-sync entry point) must (re-)bootstrap the directory skeletons.
    """
    # Arrange
    sync_obj = _make_sync(cobbler_api, tmp_path)
    bootstrap_dirs = mocker.patch.object(sync_obj, "bootstrap_dirs")
    mocker.patch.object(sync_obj, "_CobblerSync__common_run")
    mocker.patch.object(sync_obj, "clean_trees")
    sync_obj.distros = []  # type: ignore[assignment]
    sync_obj.settings.manage_dhcp_v4 = False
    sync_obj.settings.manage_dhcp_v6 = False
    sync_obj.settings.manage_dns = False
    sync_obj.settings.manage_tftpd = False
    sync_obj.settings.manage_rsync = False

    # Act
    sync_obj.run()

    # Assert
    bootstrap_dirs.assert_called_once()


def test_run_bootstraps_dirs_before_common_run(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path, mocker: "MockerFixture"
):
    """
    run() must call bootstrap_dirs() BEFORE __common_run(), not after.

    __common_run() dies if ``tftpboot_location`` doesn't exist on disk and does not create it
    itself - calling bootstrap_dirs() after __common_run() would make a full sync die() on a
    system where tftpboot_location doesn't yet exist (a fresh install, or a dynamic_tftp setup
    being switched to static tftp) before bootstrap_dirs() ever gets a chance to create it.
    """
    # Arrange
    test_sync = _make_sync(cobbler_api, tmp_path)
    mocker.patch.object(sync.utils, "run_triggers")
    mocker.patch.object(cobbler_api, "distros", return_value=[])
    tftpboot = pathlib.Path(cobbler_api.settings().tftpboot_location)
    shutil.rmtree(tftpboot)
    assert not tftpboot.exists()

    # Act
    test_sync.run()

    # Assert
    assert tftpboot.is_dir()


def test_clean_trees_skips_webdir_when_dynamic_httpd(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path
):
    """
    clean_trees() must not touch webdir at all when dynamic_httpd is selected, even though the
    (unrelated) tftp side is still cleaned normally.
    """
    # Arrange
    test_sync = _make_sync(
        cobbler_api, tmp_path, httpd_what="dynamic_httpd", tftpd_what="in_tftpd"
    )
    webdir = pathlib.Path(cobbler_api.settings().webdir)
    marker = webdir / "some-admin-file.txt"
    marker.write_text("do not touch")
    stray_dir = webdir / "not-in-whitelist"
    stray_dir.mkdir()

    # Act
    test_sync.clean_trees()

    # Assert
    assert marker.exists()
    assert marker.read_text() == "do not touch"
    assert stray_dir.exists()
    # The (non-dynamic) tftp side must still have been cleaned/recreated as normal.
    assert pathlib.Path(test_sync.grub_dir).is_dir()


def test_clean_trees_skips_tftp_when_dynamic_tftp(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path
):
    """
    clean_trees() must not touch tftpboot_location at all when dynamic_tftp is selected, even
    though the (unrelated) webdir side is still cleaned normally.
    """
    # Arrange
    test_sync = _make_sync(
        cobbler_api, tmp_path, httpd_what="in_httpd", tftpd_what="dynamic_tftp"
    )
    test_sync.bootstrap_dirs()
    tftpboot = pathlib.Path(cobbler_api.settings().tftpboot_location)
    marker = tftpboot / "some-admin-file.txt"
    marker.write_text("do not touch")

    # Act
    test_sync.clean_trees()

    # Assert
    assert marker.exists()
    assert marker.read_text() == "do not touch"
    # The (non-dynamic) webdir side must still have been cleaned/recreated as normal.
    assert pathlib.Path(cobbler_api.settings().webdir, "distro_mirror").is_dir()


def test_run_skips_distro_webdir_copy_when_dynamic_httpd(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path, mocker: "MockerFixture"
):
    """
    A full sync() must not copy any distro's kernel/initrd into webdir, or render its
    templates, when dynamic_httpd is selected.
    """
    # Arrange
    test_sync = _make_sync(
        cobbler_api, tmp_path, httpd_what="dynamic_httpd", tftpd_what="dynamic_tftp"
    )
    mocker.patch.object(sync.utils, "run_triggers")
    fake_distro = MagicMock()
    fake_distro.name = "fake-distro"
    # __common_run() re-reads self.distros from the API at the top of run(), so the fake distro
    # must be injected there rather than assigned directly on the CobblerSync instance.
    mocker.patch.object(cobbler_api, "distros", return_value=[fake_distro])
    copy_single_distro_files = mocker.patch.object(
        test_sync.api.tftpgen, "copy_single_distro_files"
    )
    write_templates = mocker.patch.object(test_sync.api.tftpgen, "write_templates")

    # Act
    test_sync.run()

    # Assert
    copy_single_distro_files.assert_not_called()
    write_templates.assert_not_called()


def test_run_copies_distro_to_webdir_for_in_httpd(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path, mocker: "MockerFixture"
):
    """
    Regression guard: the default in_httpd manager must still copy distro kernel/initrd into
    webdir during a full sync, as before.
    """
    # Arrange
    test_sync = _make_sync(
        cobbler_api, tmp_path, httpd_what="in_httpd", tftpd_what="dynamic_tftp"
    )
    mocker.patch.object(sync.utils, "run_triggers")
    fake_distro = MagicMock()
    fake_distro.name = "fake-distro"
    # __common_run() re-reads self.distros from the API at the top of run(), so the fake distro
    # must be injected there rather than assigned directly on the CobblerSync instance.
    mocker.patch.object(cobbler_api, "distros", return_value=[fake_distro])
    copy_single_distro_files = mocker.patch.object(
        test_sync.api.tftpgen, "copy_single_distro_files"
    )
    write_templates = mocker.patch.object(test_sync.api.tftpgen, "write_templates")

    # Act
    test_sync.run()

    # Assert
    copy_single_distro_files.assert_called_once()
    write_templates.assert_called_once()


@pytest.mark.skip("TODO")
def test_run_sync_systems(cobbler_api: CobblerAPI):
    # Arrange
    # mock os.path.exists()
    # mock file access (run_triggers)
    # mock collections (distro, profile, etc.)
    # mock tftpd module
    # mock dns module
    # mock dhcp module
    test_sync = sync.CobblerSync(cobbler_api)

    # Act
    test_sync.run_sync_systems([System(cobbler_api)])
    # Assert
    # correct order with correct parameters
    assert False


@pytest.mark.skip("TODO")
def test_clean_link_cache():
    # Arrange
    # Act
    # Assert
    assert False


@pytest.mark.skip("TODO")
def test_rsync_gen():
    # Arrange
    # Act
    # Assert
    assert False
