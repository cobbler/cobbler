"""
Tests for the Cobbler settings migrations
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC

import os
import pathlib
import shutil
import pytest
import yaml

from cobbler import settings
from cobbler.settings import migrations
from cobbler.settings.migrations import V3_3_0, V3_2_1, V3_2_0, V3_1_2, V3_1_1, V3_1_0, V3_0_1, V3_0_0, V3_3_1


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
    assert migrations.VERSION_LIST is not None


def test_get_installed_version():
    # Arrange
    # Act
    version = migrations.get_installed_version()

    # Assert
    assert isinstance(version, migrations.CobblerVersion)
    assert version.major >= 3


def test_get_settings_file_version():
    # Arrange
    old_settings_dict = settings.read_yaml_file("/code/tests/test_data/V2_8_5/settings.yaml")
    v285 = migrations.CobblerVersion(2, 8, 5)

    # Act
    result = migrations.get_settings_file_version(old_settings_dict)

    # Assert
    assert result == v285


def test_settingsfile_migrate_gpxe_ipxe():
    # Arrange
    new_settings = "/etc/cobbler/settings.yaml"
    old_settings = "/code/tests/test_data/settings_old"  # adjust for test container %s/code/test_dir/

    # Act
    with open(new_settings) as main_settingsfile:
        content_new = yaml.safe_load(main_settingsfile.read())
    with open(old_settings) as old_settingsfile:
        content_old = yaml.safe_load(old_settingsfile.read())

    new_settings_file = settings.read_settings_file(new_settings)

    # Assert
    assert isinstance(content_old, dict) and "enable_gpxe" in content_old
    assert isinstance(content_new, dict) and "enable_ipxe" in content_new
    assert "enable_gpxe" not in content_new
    assert isinstance(new_settings_file, dict) and "enable_ipxe" in new_settings_file
    assert "enable_gpxe" not in new_settings_file


def test_migrate_v3_0_0():
    # Arrange
    with open("/code/tests/test_data/V2_8_5/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_0_0.migrate(old_settings_dict)

    # Assert
    assert V3_0_0.validate(new_settings)


def test_normalize_v3_0_0():
    # Arrange
    with open("/code/tests/test_data/V3_0_0/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_0_0.normalize(old_settings_dict)

    # Assert
    assert len(V3_0_0.normalize(new_settings)) == 111


def test_migrate_v3_0_1():
    # Arrange
    with open("/code/tests/test_data/V3_0_0/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_0_1.migrate(old_settings_dict)

    # Assert
    assert V3_0_1.validate(new_settings)


def test_normalize_v3_0_1():
    # Arrange
    with open("/code/tests/test_data/V3_0_1/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_0_1.normalize(old_settings_dict)

    # Assert
    assert len(V3_0_1.normalize(new_settings)) == 111


def test_migrate_v3_1_0():
    # Arrange
    with open("/code/tests/test_data/V3_0_1/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_1_0.migrate(old_settings_dict)

    # Assert
    assert V3_1_0.validate(new_settings)


def test_normalize_v3_1_0():
    # Arrange
    with open("/code/tests/test_data/V3_1_0/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_1_0.normalize(old_settings_dict)

    # Assert
    assert len(V3_1_0.normalize(new_settings)) == 111


def test_migrate_v3_1_1():
    # Arrange
    with open("/code/tests/test_data/V3_1_0/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_1_1.migrate(old_settings_dict)

    # Assert
    assert V3_1_1.validate(new_settings)


def test_normalize_v3_1_1():
    # Arrange
    with open("/code/tests/test_data/V3_1_1/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_1_1.normalize(old_settings_dict)

    # Assert
    assert len(V3_1_1.normalize(new_settings)) == 111


def test_migrate_v3_1_2():
    # Arrange
    with open("/code/tests/test_data/V3_1_1/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_1_2.migrate(old_settings_dict)

    # Assert
    assert V3_1_2.validate(new_settings)


def test_normalize_v3_1_2():
    # Arrange
    with open("/code/tests/test_data/V3_1_2/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_1_2.normalize(old_settings_dict)

    # Assert
    assert len(V3_1_2.normalize(new_settings)) == 110


def test_migrate_v3_2_0():
    # Arrange
    with open("/code/tests/test_data/V3_1_2/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_2_0.migrate(old_settings_dict)

    # Assert
    assert V3_2_0.validate(new_settings)


def test_normalize_v3_2_0():
    # Arrange
    with open("/code/tests/test_data/V3_2_0/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_2_0.normalize(old_settings_dict)

    # Assert
    assert len(V3_2_0.normalize(new_settings)) == 112


def test_migrate_v3_2_1():
    # Arrange
    with open("/code/tests/test_data/V3_2_0/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_2_1.migrate(old_settings_dict)

    # Assert
    assert V3_2_1.validate(new_settings)


def test_normalize_v3_2_1():
    # Arrange
    with open("/code/tests/test_data/V3_2_1/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_2_1.normalize(old_settings_dict)

    # Assert
    assert len(V3_2_1.normalize(new_settings)) == 111


def test_migrate_v3_3_0():
    # Arrange
    with open("/code/tests/test_data/V3_2_1/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_0.migrate(old_settings_dict)

    # Assert
    assert V3_3_0.validate(new_settings)


def test_normalize_v3_3_0():
    # Arrange
    with open("/code/tests/test_data/V3_3_0/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_0.normalize(old_settings_dict)

    # Assert
    assert len(V3_3_0.normalize(new_settings)) == 121


def test_migrate_v3_3_1():
    # Arrange
    with open("/code/tests/test_data/V3_3_0/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_1.migrate(old_settings_dict)

    # Assert
    assert V3_3_1.validate(new_settings)


def test_normalize_v3_3_1():
    # Arrange
    with open("/code/tests/test_data/V3_3_1/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_1.normalize(old_settings_dict)

    # Assert
    assert len(V3_3_1.normalize(new_settings)) == 129
