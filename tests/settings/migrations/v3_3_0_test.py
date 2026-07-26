"""
Tests for the Cobbler V3.3.0 settings migration.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC
import yaml

from cobbler.settings.migrations import V3_3_0


def test_migrate_v3_3_0():
    # Arrange
    with open(
        "/code/tests/test_data/V3_2_1/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_0.migrate(old_settings_dict)

    # Assert
    assert V3_3_0.validate(new_settings)
    # We had a bug where the @@ values were incorrectly present in the final code.
    # Thus checking that this is not the case anymore.
    assert new_settings.get("bind_zonefile_path") == "/var/lib/named"
    # gpxe -> ipxe renaming
    assert "enable_ipxe" in new_settings
    assert "enable_gpxe" not in new_settings
    # ipmitool -> ipmilanplus
    assert "power_management_default_type" in new_settings
    assert new_settings["power_management_default_type"] == "ipmilanplus"


def test_normalize_v3_3_0():
    # Arrange
    with open(
        "/code/tests/test_data/V3_3_0/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_0.normalize(old_settings_dict)

    # Assert
    assert len(V3_3_0.normalize(new_settings)) == 122
