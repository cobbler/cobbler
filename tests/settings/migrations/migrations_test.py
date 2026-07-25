"""
Tests for the Cobbler settings migrations framework (cobbler.settings.migrations).
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC
from typing import TYPE_CHECKING

import pytest

from cobbler import settings
from cobbler.settings import migrations

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_cobbler_version_logic():
    # Arrange
    v285 = migrations.CobblerVersion()
    v285.major = 2
    v285.minor = 8
    v285.patch = 5
    v330 = migrations.CobblerVersion()
    v330.major = 3
    v330.minor = 3
    v330.patch = 0

    # Arrange
    bigger = v330 > v285
    smaller = v285 < v330
    not_equal = v330 != v285

    # Assert
    assert bigger
    assert smaller
    assert not_equal


def test_discover_migrations():
    # Arrange
    migrations.VERSION_LIST = {}
    # Act
    migrations.discover_migrations()
    # Assert
    assert migrations.VERSION_LIST is not None  # type: ignore


def test_get_installed_version(mocker: "MockerFixture"):
    """get_installed_version reads __version__ from cobbler._version."""
    mocker.patch(
        "cobbler.settings.migrations.__version__",
        "3.3.7",
        create=True,
    )

    result = migrations.get_installed_version()

    assert isinstance(result, migrations.CobblerVersion)
    assert result.major == 3
    assert result.minor == 3
    assert result.patch == 7


def test_get_installed_version_dev_build(mocker: "MockerFixture"):
    """get_installed_version strips the dev suffix and local segment."""
    mocker.patch(
        "cobbler.settings.migrations.__version__",
        "4.0.0.dev3",
        create=True,
    )

    result = migrations.get_installed_version()

    assert result.major == 4
    assert result.minor == 0
    assert result.patch == 0


def test_get_installed_version_fallback_on_import_error(mocker: "MockerFixture"):
    """get_installed_version raises an error when cobbler._version is missing."""
    mocker.patch(
        "cobbler.settings.migrations.__version__",
        None,
        create=True,
    )

    with pytest.raises(RuntimeError):
        migrations.get_installed_version()


def test_get_settings_file_version():
    # Arrange
    old_settings_dict = settings.read_yaml_file(
        "/code/tests/test_data/V2_8_5/settings.yaml"
    )
    v285 = migrations.CobblerVersion(2, 8, 5)

    # Act
    result = migrations.get_settings_file_version(old_settings_dict)

    # Assert
    assert result == v285


def test_get_settings_file_version_prefers_newest_matching_version():
    """
    Regression test: V3.3.5/V3.3.6/V3.3.7 share an identical schema, so a
    settings dict valid for one validates against all three. This must resolve
    to the highest (newest) matching version, not whichever happens to be
    first in VERSION_LIST's (unordered) iteration order.
    """
    # Arrange
    old_settings_dict = settings.read_yaml_file(
        "/code/tests/test_data/V3_3_6/settings.yaml"
    )

    # Act
    result = migrations.get_settings_file_version(old_settings_dict)

    # Assert
    assert result == migrations.CobblerVersion(3, 3, 7)
