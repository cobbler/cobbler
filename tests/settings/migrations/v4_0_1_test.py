"""
Tests for the Cobbler V4.0.1 settings migration.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC
import yaml

from cobbler.settings.migrations import V4_0_1


def test_migrate_v4_0_1():
    """
    Test to validate that a migrations of the settings from Cobbler 4.0.0 to 4.0.1 is working as expected.
    """
    # Arrange
    with open(
        "/code/tests/test_data/V4_0_0/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V4_0_1.migrate(old_settings_dict)

    # Assert
    assert V4_0_1.validate(new_settings)


def test_normalize_v4_0_1():
    # Arrange
    with open(
        "/code/tests/test_data/V4_0_1/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V4_0_1.normalize(old_settings_dict)

    # Assert
    assert len(new_settings) == 134
