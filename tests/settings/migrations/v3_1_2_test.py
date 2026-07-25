"""
Tests for the Cobbler V3.1.2 settings migration.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC
import yaml

from cobbler.settings.migrations import V3_1_2


def test_migrate_v3_1_2():
    # Arrange
    with open(
        "/code/tests/test_data/V3_1_1/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_1_2.migrate(old_settings_dict)

    # Assert
    assert V3_1_2.validate(new_settings)


def test_normalize_v3_1_2():
    # Arrange
    with open(
        "/code/tests/test_data/V3_1_2/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_1_2.normalize(old_settings_dict)

    # Assert
    assert len(V3_1_2.normalize(new_settings)) == 111
