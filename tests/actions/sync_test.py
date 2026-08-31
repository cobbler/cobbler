"""
Tests that validate the functionality of the module that is responsible for synchronizing the different daemons
with each other.
"""

import pathlib
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


def test_init_skips_directory_creation_for_dynamic_modules(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path, mocker: "MockerFixture"
):
    """
    Constructing CobblerSync must not materialize webdir/tftpboot skeleton directories when the
    corresponding manager is a dynamic (copy-free) one.
    """
    # Arrange
    create_web_dirs = mocker.patch(
        "cobbler.actions.sync.filesystem_helpers.create_web_dirs"
    )
    create_tftpboot_dirs = mocker.patch(
        "cobbler.actions.sync.filesystem_helpers.create_tftpboot_dirs"
    )

    # Act
    _make_sync(
        cobbler_api, tmp_path, httpd_what="dynamic_httpd", tftpd_what="dynamic_tftp"
    )

    # Assert
    create_web_dirs.assert_not_called()
    create_tftpboot_dirs.assert_not_called()


def test_init_creates_directories_for_default_modules(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path, mocker: "MockerFixture"
):
    """
    Regression guard: the default (non-dynamic) managers must still get their directory
    skeletons created as before.
    """
    # Arrange
    create_web_dirs = mocker.patch(
        "cobbler.actions.sync.filesystem_helpers.create_web_dirs"
    )
    create_tftpboot_dirs = mocker.patch(
        "cobbler.actions.sync.filesystem_helpers.create_tftpboot_dirs"
    )

    # Act
    _make_sync(cobbler_api, tmp_path, httpd_what="in_httpd", tftpd_what="in_tftpd")

    # Assert
    create_web_dirs.assert_called_once()
    create_tftpboot_dirs.assert_called_once()


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
