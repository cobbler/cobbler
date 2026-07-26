"""
Tests for the Cobbler V3.3.5 settings migration.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC
import yaml

from cobbler.settings.migrations import V3_3_5


def test_migrate_v3_3_5():
    """
    Test to validate that a migrations of the settings from Cobbler 3.3.4 to 3.3.5 is working as expected.
    """
    # Arrange
    with open(
        "/code/tests/test_data/V3_3_4/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_5.migrate(old_settings_dict)

    # Assert
    assert V3_3_5.validate(new_settings)


def test_normalize_v3_3_5():
    # Arrange
    with open(
        "/code/tests/test_data/V3_3_4/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_5.normalize(old_settings_dict)

    # Assert
    assert len(new_settings) == 132
