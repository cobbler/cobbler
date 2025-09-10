"""
Tests for the Cobbler settings migrations
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC
import pathlib
import shutil

import pytest
import yaml

from cobbler import settings
from cobbler.settings import migrations
from cobbler.settings.migrations import (
    V3_0_0,
    V3_0_1,
    V3_1_0,
    V3_1_1,
    V3_1_2,
    V3_2_0,
    V3_2_1,
    V3_3_0,
    V3_3_1,
    V3_3_2,
    V3_3_3,
    V3_3_4,
    V3_3_5,
    V3_3_6,
    V3_3_7,
    V3_4_0,
)

modules_conf_location = "/etc/cobbler/modules.conf"


@pytest.fixture(scope="function", autouse=True)
def delete_modules_conf():
    yield
    modules_conf_path = pathlib.Path(modules_conf_location)
    if modules_conf_path.exists():
        modules_conf_path.unlink()


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


def test_get_installed_version():
    # Arrange
    # Act
    version = migrations.get_installed_version()

    # Assert
    assert isinstance(version, migrations.CobblerVersion)
    assert version.major >= 3


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


def test_migrate_v3_0_0():
    # Arrange
    with open(
        "/code/tests/test_data/V2_8_5/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_0_0.migrate(old_settings_dict)

    # Assert
    assert V3_0_0.validate(new_settings)


def test_migrate_v3_0_1():
    # Arrange
    with open(
        "/code/tests/test_data/V3_0_0/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())
    shutil.copy("/code/tests/test_data/V3_0_0/modules.conf", modules_conf_location)

    # Act
    new_settings = V3_0_1.migrate(old_settings_dict)

    # Read migrated modules.conf
    with open("/etc/cobbler/modules.conf", encoding="UTF-8") as modules_conf:
        new_modules_conf_content = modules_conf.readlines()

    # Assert
    assert V3_0_1.validate(new_settings)
    assert all(
        line not in ("authn_", "authz_", "manage_") for line in new_modules_conf_content
    )


def test_migrate_v3_1_0():
    # Arrange
    with open(
        "/code/tests/test_data/V3_0_1/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_1_0.migrate(old_settings_dict)

    # Assert
    assert V3_1_0.validate(new_settings)


def test_migrate_v3_1_1():
    # Arrange
    with open(
        "/code/tests/test_data/V3_1_0/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_1_1.migrate(old_settings_dict)

    # Assert
    assert V3_1_1.validate(new_settings)


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


def test_migrate_v3_2_0():
    # Arrange
    with open(
        "/code/tests/test_data/V3_1_2/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_2_0.migrate(old_settings_dict)

    # Assert
    assert V3_2_0.validate(new_settings)


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


def test_migrate_v3_3_1():
    # Arrange
    with open(
        "/code/tests/test_data/V3_3_0/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_1.migrate(old_settings_dict)

    # Assert
    assert V3_3_1.validate(new_settings)
    # We had a bug where the @@ values were incorrectly present in the final code.
    # Thus checking that this is not the case anymore.
    assert new_settings.get("syslinux_dir") == "/usr/share/syslinux"


def test_migrate_v3_3_2():
    # Arrange
    with open(
        "/code/tests/test_data/V3_3_1/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_2.migrate(old_settings_dict)

    # Assert
    assert V3_3_2.validate(new_settings)


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


def test_migrate_v3_3_4():
    """
    Test to validate that a migrations of the settings from Cobbler 3.3.3 to 3.3.4 is working as expected.
    """
    # Arrange
    with open(
        "/code/tests/test_data/V3_3_3/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_4.migrate(old_settings_dict)

    # Assert
    assert V3_3_4.validate(new_settings)


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


def test_migrate_v3_3_6():
    """
    Test to validate that a migrations of the settings from Cobbler 3.3.5 to 3.3.6 is working as expected.
    """
    # Arrange
    with open(
        "/code/tests/test_data/V3_3_5/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_6.migrate(old_settings_dict)

    # Assert
    assert V3_3_6.validate(new_settings)


def test_migrate_v3_3_7():
    """
    Test to validate that a migrations of the settings from Cobbler 3.3.6 to 3.3.7 is working as expected.
    """
    # Arrange
    with open(
        "/code/tests/test_data/V3_3_6/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_7.migrate(old_settings_dict)

    # Assert
    assert V3_3_7.validate(new_settings)


def test_migrate_v3_4_0():
    """
    Test to validate that a migrations of the settings from Cobbler 3.3.7 to 3.4.0 is working as expected.
    """
    # Arrange
    with open(
        "/code/tests/test_data/V3_3_7/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())
    shutil.copy("/code/tests/test_data/V3_3_7/modules.conf", modules_conf_location)
    shutil.copy(
        "/code/tests/test_data/V3_3_7/mongodb.conf", "/etc/cobbler/mongodb.conf"
    )
    shutil.copy(
        "/code/tests/test_data/V3_3_7/collections/systems/host.example.org.json",
        "/var/lib/cobbler/collections/systems/host.example.org.json",
    )

    # Act
    new_settings = V3_4_0.migrate(old_settings_dict)

    # Assert
    # We cannot assert that the collection migration has succeeded as the code inside network_interface.py
    # might change over time (aka we are not loading the 3.4.0 Network Interface model but the current one).
    assert V3_4_0.validate(new_settings)
    assert not pathlib.Path("/etc/cobbler/mongodb.conf").exists()
    assert not pathlib.Path(modules_conf_location).exists()
