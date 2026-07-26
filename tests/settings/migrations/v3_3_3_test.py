"""
Tests for the Cobbler V3.3.3 settings migration.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC
import yaml

from cobbler.settings.migrations import V3_3_3


def test_migrate_v3_3_3():
    # Arrange
    with open(
        "/code/tests/test_data/V3_3_2/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_3.migrate(old_settings_dict)

    # Assert
    assert V3_3_3.validate(new_settings)
    # Migration of default_virt_file_size to float is working
    assert isinstance(new_settings.get("default_virt_file_size", None), float)


def test_normalize_v3_3_3():
    # Arrange
    with open(
        "/code/tests/test_data/V3_3_3/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_3.normalize(old_settings_dict)

    # Assert
    assert len(new_settings) == 131
    # Migration of default_virt_file_size to float is working
    assert isinstance(new_settings.get("default_virt_file_size", None), float)
