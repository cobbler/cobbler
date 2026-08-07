"""
Tests that validate the functionality of the ``cobbler import`` action (``Importer``), in particular the
copy-free ("direct source") scan-in-place behavior that applies when ``modules.httpd.module`` is set to
``managers.dynamic_httpd``.
"""

import logging
import os
import pathlib
from typing import Any

import pytest
from pytest_mock import MockerFixture

from cobbler.actions.importer import Importer
from cobbler.api import CobblerAPI


def _stub_import_manager(mocker: MockerFixture, cobbler_api: CobblerAPI) -> Any:
    """
    Replace the real "managers.import_signatures" module lookup with a stub whose ``get_import_manager()`` returns
    a ``MagicMock``, so tests can assert exactly what ``Importer.run()`` hands off to the import manager without
    actually walking a filesystem tree looking for distributions.

    :return: The mocked import manager (i.e. what ``import_module.get_import_manager(api)`` returns).
    """
    manager_mock = mocker.MagicMock()
    import_module_mock = mocker.MagicMock()
    import_module_mock.get_import_manager.return_value = manager_mock
    mocker.patch.object(
        cobbler_api, "get_module_by_name", return_value=import_module_mock
    )
    return manager_mock


def test_run_direct_source_skips_rsync_for_local_dynamic_httpd(
    cobbler_api: CobblerAPI, mocker: MockerFixture, tmp_path: pathlib.Path
):
    """
    With ``managers.dynamic_httpd`` selected, no ``network_root``, and a local, existing, absolute ``mirror_url``,
    the rsync copy must be skipped entirely, and ``import_manager.run()`` must be called with ``mirror_url``
    itself (not the ``distro_mirror`` destination path) and ``direct_source=True``.
    """
    # Arrange
    cobbler_api.settings().modules["httpd"] = {"module": "managers.dynamic_httpd"}
    manager_mock = _stub_import_manager(mocker, cobbler_api)
    mkdir_mock = mocker.patch("cobbler.actions.importer.filesystem_helpers.mkdir")
    subprocess_mock = mocker.patch("cobbler.actions.importer.utils.subprocess_call")
    importer = Importer(cobbler_api)
    source_dir = str(tmp_path)

    # Act
    result = importer.run(source_dir, "test_direct_import")

    # Assert
    assert result is True
    mkdir_mock.assert_not_called()
    subprocess_mock.assert_not_called()
    manager_mock.run.assert_called_once_with(
        source_dir,
        "test_direct_import",
        None,
        None,
        None,
        None,
        None,
        direct_source=True,
    )


def test_run_remote_source_falls_back_to_rsync_with_dynamic_httpd(
    cobbler_api: CobblerAPI,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
):
    """
    With ``managers.dynamic_httpd`` selected but a remote/non-local source, direct (copy-free) import must not
    apply: the existing rsync-based behavior must run unchanged, and an info-level log message must explain why
    dynamic mode didn't take effect.
    """
    # Arrange
    caplog.set_level(logging.INFO)
    cobbler_api.settings().modules["httpd"] = {"module": "managers.dynamic_httpd"}
    manager_mock = _stub_import_manager(mocker, cobbler_api)
    mocker.patch("cobbler.actions.importer.filesystem_helpers.mkdir")
    subprocess_mock = mocker.patch(
        "cobbler.actions.importer.utils.subprocess_call", return_value=0
    )
    importer = Importer(cobbler_api)
    mirror_url = "user@remotehost:/remote/path"
    expected_path = os.path.normpath(
        f"{cobbler_api.settings().webdir}/distro_mirror/test_remote_import"
    )

    # Act
    result = importer.run(mirror_url, "test_remote_import")

    # Assert
    assert result is True
    subprocess_mock.assert_called_once()
    assert "falling back to the regular rsync copy" in caplog.text
    manager_mock.run.assert_called_once_with(
        expected_path,
        "test_remote_import",
        None,
        None,
        None,
        None,
        None,
        direct_source=False,
    )


def test_run_network_root_set_ignores_dynamic_httpd(
    cobbler_api: CobblerAPI, mocker: MockerFixture, tmp_path: pathlib.Path
):
    """
    Orthogonality regression guard: even with ``managers.dynamic_httpd`` selected and a local, existing, absolute
    ``mirror_url``, setting ``network_root`` (``--available-as``) must keep today's ``network_root`` behavior
    completely untouched (rsync still runs, ``direct_source`` stays False).
    """
    # Arrange
    cobbler_api.settings().modules["httpd"] = {"module": "managers.dynamic_httpd"}
    manager_mock = _stub_import_manager(mocker, cobbler_api)
    mocker.patch("cobbler.actions.importer.filesystem_helpers.mkdir")
    subprocess_mock = mocker.patch(
        "cobbler.actions.importer.utils.subprocess_call", return_value=0
    )
    importer = Importer(cobbler_api)
    source_dir = str(tmp_path)
    expected_path = os.path.normpath(
        f"{cobbler_api.settings().webdir}/distro_mirror/test_network_root_import"
    )

    # Act
    result = importer.run(
        source_dir,
        "test_network_root_import",
        network_root="http://boot.example.com/os",
    )

    # Assert
    assert result is True
    subprocess_mock.assert_called_once()
    manager_mock.run.assert_called_once_with(
        expected_path,
        "test_network_root_import",
        "http://boot.example.com/os/",
        None,
        None,
        None,
        None,
        direct_source=False,
    )


def test_run_default_httpd_module_behaves_as_before(
    cobbler_api: CobblerAPI, mocker: MockerFixture, tmp_path: pathlib.Path
):
    """
    Regression guard: with the default ``managers.in_httpd`` httpd module selected (i.e. nothing changed in
    settings), ``Importer.run()`` must behave exactly as it did before this feature: rsync always runs, and
    ``direct_source`` is always False.
    """
    # Arrange
    manager_mock = _stub_import_manager(mocker, cobbler_api)
    mkdir_mock = mocker.patch("cobbler.actions.importer.filesystem_helpers.mkdir")
    subprocess_mock = mocker.patch(
        "cobbler.actions.importer.utils.subprocess_call", return_value=0
    )
    importer = Importer(cobbler_api)
    source_dir = str(tmp_path)
    expected_path = os.path.normpath(
        f"{cobbler_api.settings().webdir}/distro_mirror/test_default_import"
    )

    # Act
    result = importer.run(source_dir, "test_default_import")

    # Assert
    assert result is True
    mkdir_mock.assert_called_once_with(expected_path)
    subprocess_mock.assert_called_once()
    manager_mock.run.assert_called_once_with(
        expected_path,
        "test_default_import",
        None,
        None,
        None,
        None,
        None,
        direct_source=False,
    )


def test_is_local_directory_source(tmp_path: pathlib.Path):
    """
    Unit-level coverage of the helper that decides whether a mirror_url qualifies for direct (copy-free) import.
    """
    # Arrange
    local_dir = str(tmp_path)
    nonexistent_dir = str(tmp_path / "does-not-exist")

    # Act & Assert
    assert Importer._is_local_directory_source(local_dir) is True  # type: ignore[reportPrivateUsage]
    assert (
        Importer._is_local_directory_source(nonexistent_dir) is False  # type: ignore[reportPrivateUsage]
    )
    assert (
        Importer._is_local_directory_source("relative/path") is False  # type: ignore[reportPrivateUsage]
    )
    assert (
        Importer._is_local_directory_source("http://example.com/path") is False  # type: ignore[reportPrivateUsage]
    )
    assert (
        Importer._is_local_directory_source("https://example.com/path") is False  # type: ignore[reportPrivateUsage]
    )
    assert Importer._is_local_directory_source("ftp://example.com/path") is False  # type: ignore[reportPrivateUsage]
    assert Importer._is_local_directory_source("nfs://example.com/path") is False  # type: ignore[reportPrivateUsage]
    assert (
        Importer._is_local_directory_source("rsync://example.com/path") is False  # type: ignore[reportPrivateUsage]
    )
    assert (
        Importer._is_local_directory_source("user@host:/remote/path") is False  # type: ignore[reportPrivateUsage]
    )
