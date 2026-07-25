"""
Tests for the Cobbler V3.2.1 settings migration.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC
import yaml

from cobbler.settings.migrations import V3_2_1


def test_migrate_v3_2_1():
    # Arrange
    with open(
        "/code/tests/test_data/V3_2_0/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_2_1.migrate(old_settings_dict)

    # Assert
    assert V3_2_1.validate(new_settings)
    # manage_tftp removed
    assert "manage_tftp" not in new_settings


def test_normalize_v3_2_1():
    # Arrange
    with open(
        "/code/tests/test_data/V3_2_1/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_2_1.normalize(old_settings_dict)

    # Assert
    assert len(V3_2_1.normalize(new_settings)) == 112
