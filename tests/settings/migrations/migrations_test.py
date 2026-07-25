"""
Tests for the Cobbler settings migrations
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC
import json
import pathlib
import shutil
from typing import TYPE_CHECKING, Dict

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
    V4_0_0,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

modules_conf_location = "/etc/cobbler/modules.conf"


@pytest.fixture(scope="function", autouse=True)
def delete_modules_conf():
    yield
    modules_conf_path = pathlib.Path(modules_conf_location)
    if modules_conf_path.exists():
        modules_conf_path.unlink()
    mongodb_conf_path = pathlib.Path("/etc/cobbler/mongodb.conf")
    if mongodb_conf_path.exists():
        mongodb_conf_path.unlink()


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


def test_migrate_v4_0_0():
    """
    Test to validate that a migrations of the settings from Cobbler 3.3.7 to 4.0.0 is working as expected.
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
    new_settings = V4_0_0.migrate(old_settings_dict)

    # Assert
    # We cannot assert that the collection migration has succeeded as the code inside network_interface.py
    # might change over time (aka we are not loading the 4.0.0 Network Interface model but the current one).
    assert V4_0_0.validate(new_settings)
    assert not pathlib.Path("/etc/cobbler/mongodb.conf").exists()
    assert not pathlib.Path(modules_conf_location).exists()
    # windows_template_dir was removed without replacement in V4.0.0.
    assert "windows_template_dir" not in new_settings
    # A bootloader architecture with no corresponding V4.0.0 default (arm-uboot) must survive
    # key_drop_if_default() rather than being dropped or raising a KeyError.
    assert new_settings["bootloaders_formats"]["arm-uboot"] == {
        "binary_name": "arm-boot.efi"
    }
    # The system JSON should have been renamed to <uid>.json and lost its embedded interfaces.
    migrated_system_file = pathlib.Path(
        "/var/lib/cobbler/collections/systems/9c885c2d49bf477795858d58cc101b9e.json"
    )
    assert migrated_system_file.exists()
    migrated_system = json.loads(migrated_system_file.read_text(encoding="UTF-8"))
    assert "interfaces" not in migrated_system


def test_migrate_v4_0_0_modules_conf_propagation():
    """
    Regression test: the modules.conf migration used to accidentally re-read the
    mongodb.conf path, which silently discarded a real install's customized module
    configuration and replaced it with the hardcoded fallback defaults.
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
    new_settings = V4_0_0.migrate(old_settings_dict)

    # Assert
    # Fixture values (see tests/test_data/V3_3_7/modules.conf) are intentionally different
    # from V4_0_0.py's hardcoded fallback defaults so this assertion is not vacuous.
    assert new_settings["modules"]["authentication"]["module"] == "authentication.ldap"
    assert new_settings["modules"]["authentication"]["hash_algorithm"] == "sha2_256"
    assert (
        new_settings["modules"]["authorization"]["module"] == "authorization.ownership"
    )
    assert new_settings["modules"]["dns"]["module"] == "managers.dnsmasq"
    assert new_settings["modules"]["dhcp"]["module"] == "managers.dnsmasq"
    assert new_settings["modules"]["serializers"]["module"] == "serializers.mongodb"
    # "tftpd" is intentionally left at its default ("managers.in_tftpd" is the only
    # tftpd module implementation that exists) - key_drop_if_default() correctly
    # drops it entirely since every value in it matches the default.
    assert "tftpd" not in new_settings["modules"]


def test_migrate_v4_0_0_mongodb_conf_propagation():
    """
    Regression test: mongodb.conf values must land in the migrated settings as-is,
    not the hardcoded fallback defaults.
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
    new_settings = V4_0_0.migrate(old_settings_dict)

    # Assert
    assert new_settings["mongodb"] == {
        "host": "mongo-test.example.com",
        "port": 27018,
    }


def test_migrate_v4_0_0_interface_type_na(tmp_path: pathlib.Path):
    # Arrange
    systems_dir = tmp_path / "systems"
    systems_dir.mkdir()
    system_file = systems_dir / "system1.example.com.json"
    shutil.copy(
        "/code/tests/test_data/V3_3_7/collections_multi/systems/system1.example.com.json",
        system_file,
    )

    # Act
    V4_0_0.migrate_cobbler_collections(str(tmp_path))

    # Assert
    data = json.loads(system_file.read_text(encoding="UTF-8"))
    assert data["interfaces"]["default"]["interface_type"] == "NA"


def test_migrate_v4_0_0_boot_files_merge(tmp_path: pathlib.Path):
    # Arrange
    systems_dir = tmp_path / "systems"
    systems_dir.mkdir()
    system_file = systems_dir / "system3.example.com.json"
    shutil.copy(
        "/code/tests/test_data/V3_3_7/collections_multi/systems/system3.example.com.json",
        system_file,
    )

    # Act
    V4_0_0.migrate_cobbler_collections(str(tmp_path))

    # Assert
    data = json.loads(system_file.read_text(encoding="UTF-8"))
    assert "boot_files" not in data
    assert "fetchable_files" not in data
    # template_files gains every boot_files key; on conflict, boot_files wins.
    assert data["template_files"] == {
        "foo": "bar",
        "pxe": "pxe_file",
        "shared_key": "from_boot_files",
    }


def test_migrate_v4_0_0_boot_files_inherit_not_merged(tmp_path: pathlib.Path):
    """
    A ``boot_files`` value of the literal string "<<inherit>>" must be dropped
    without being merged into ``template_files``.
    """
    # Arrange
    systems_dir = tmp_path / "systems"
    systems_dir.mkdir()
    system_file = systems_dir / "host.example.org.json"
    shutil.copy(
        "/code/tests/test_data/V3_3_7/collections/systems/host.example.org.json",
        system_file,
    )

    # Act
    V4_0_0.migrate_cobbler_collections(str(tmp_path))

    # Assert
    data = json.loads(system_file.read_text(encoding="UTF-8"))
    assert "boot_files" not in data
    assert data["template_files"] == {}


@pytest.mark.parametrize(
    "fetchable_files_value", [{"somefile": "/path/to/file"}, "<<inherit>>"]
)
def test_migrate_v4_0_0_fetchable_files_removed(
    tmp_path: pathlib.Path, fetchable_files_value: object
):
    # Arrange
    systems_dir = tmp_path / "systems"
    systems_dir.mkdir()
    system_file = systems_dir / "system.json"
    system_file.write_text(
        json.dumps({"uid": "abc", "fetchable_files": fetchable_files_value}),
        encoding="UTF-8",
    )

    # Act
    V4_0_0.migrate_cobbler_collections(str(tmp_path))

    # Assert
    data = json.loads(system_file.read_text(encoding="UTF-8"))
    assert "fetchable_files" not in data


def test_migrate_v4_0_0_network_interfaces_multi(tmp_path: pathlib.Path):
    # Arrange
    systems_dir = tmp_path / "systems"
    systems_dir.mkdir()
    for name in (
        "system1.example.com",
        "system2.example.com",
        "system3.example.com",
    ):
        shutil.copy(
            f"/code/tests/test_data/V3_3_7/collections_multi/systems/{name}.json",
            systems_dir / f"{name}.json",
        )
    (tmp_path / "network_interfaces").mkdir()

    # Act
    V4_0_0.migrate_cobbler_json_files(tmp_path)
    V4_0_0.migrate_cobbler_network_interfaces(tmp_path)

    # Assert
    system_files = list(systems_dir.glob("*.json"))
    assert len(system_files) == 3
    for system_file in system_files:
        data = json.loads(system_file.read_text(encoding="UTF-8"))
        assert "interfaces" not in data

    interface_files = list((tmp_path / "network_interfaces").glob("*.json"))
    expected_interface_counts = {
        "11111111111111111111111111111111": 1,
        "22222222222222222222222222222222": 2,
        "33333333333333333333333333333333": 1,
    }
    counts: Dict[str, int] = {}
    for interface_file in interface_files:
        data = json.loads(interface_file.read_text(encoding="UTF-8"))
        assert "uid" in data
        assert "name" in data
        assert "system_uid" in data
        counts[data["system_uid"]] = counts.get(data["system_uid"], 0) + 1
    assert counts == expected_interface_counts


def test_migrate_v4_0_0_json_filename_migration_multi_collection(
    tmp_path: pathlib.Path,
):
    # Arrange
    systems_dir = tmp_path / "systems"
    profiles_dir = tmp_path / "profiles"
    systems_dir.mkdir()
    profiles_dir.mkdir()
    # These collection types were removed in V4.0.0 and are always empty on a real
    # 3.3.x -> 4.0.0 upgrade - confirm they're left untouched, not a crash source.
    for legacy in ("packages", "mgmtclasses", "files"):
        (tmp_path / legacy).mkdir()

    (systems_dir / "system1.example.com.json").write_text(
        json.dumps({"uid": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}), encoding="UTF-8"
    )
    (profiles_dir / "profile1.json").write_text(
        json.dumps({"uid": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}), encoding="UTF-8"
    )

    # Act
    V4_0_0.migrate_cobbler_json_files(tmp_path)

    # Assert
    assert [f.name for f in systems_dir.glob("*.json")] == [
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json"
    ]
    assert [f.name for f in profiles_dir.glob("*.json")] == [
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.json"
    ]
    for legacy in ("packages", "mgmtclasses", "files"):
        assert list((tmp_path / legacy).iterdir()) == []


def test_migrate_v4_0_0_include_directory_cleanup(tmp_path: pathlib.Path):
    """
    Regression test: "include" holds glob patterns (e.g.
    "/etc/cobbler/settings.d/*.settings"), not literal directory paths - the
    settings.d directory itself (the pattern's parent) must actually be
    removed once empty, not silently left behind.
    """
    # Arrange
    with open(
        "/code/tests/test_data/V3_3_7/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())
    settings_d_dir = tmp_path / "settings.d"
    settings_d_dir.mkdir()
    old_settings_dict["include"] = [str(settings_d_dir / "*.settings")]
    shutil.copy("/code/tests/test_data/V3_3_7/modules.conf", modules_conf_location)
    shutil.copy(
        "/code/tests/test_data/V3_3_7/mongodb.conf", "/etc/cobbler/mongodb.conf"
    )
    shutil.copy(
        "/code/tests/test_data/V3_3_7/collections/systems/host.example.org.json",
        "/var/lib/cobbler/collections/systems/host.example.org.json",
    )

    # Act
    V4_0_0.migrate(old_settings_dict)

    # Assert
    assert not settings_d_dir.exists()


def test_migrate_v4_0_0_include_directory_not_removed_if_not_empty(
    tmp_path: pathlib.Path,
):
    # Arrange
    with open(
        "/code/tests/test_data/V3_3_7/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())
    settings_d_dir = tmp_path / "settings.d"
    settings_d_dir.mkdir()
    (settings_d_dir / "leftover.settings").write_text("foo: bar", encoding="UTF-8")
    old_settings_dict["include"] = [str(settings_d_dir / "*.settings")]
    shutil.copy("/code/tests/test_data/V3_3_7/modules.conf", modules_conf_location)
    shutil.copy(
        "/code/tests/test_data/V3_3_7/mongodb.conf", "/etc/cobbler/mongodb.conf"
    )
    shutil.copy(
        "/code/tests/test_data/V3_3_7/collections/systems/host.example.org.json",
        "/var/lib/cobbler/collections/systems/host.example.org.json",
    )

    # Act
    V4_0_0.migrate(old_settings_dict)

    # Assert
    assert settings_d_dir.exists()


def test_migrate_v4_0_0_uid_references(tmp_path: pathlib.Path):
    # Arrange
    distros_dir = tmp_path / "distros"
    profiles_dir = tmp_path / "profiles"
    systems_dir = tmp_path / "systems"
    menus_dir = tmp_path / "menus"
    repos_dir = tmp_path / "repos"
    for directory in (distros_dir, profiles_dir, systems_dir, menus_dir, repos_dir):
        directory.mkdir()

    (distros_dir / "distro1.json").write_text(
        json.dumps({"uid": "d1", "name": "test-distro", "parent": ""}),
        encoding="UTF-8",
    )
    (menus_dir / "menu1.json").write_text(
        json.dumps({"uid": "m1", "name": "test-menu", "parent": ""}),
        encoding="UTF-8",
    )
    (repos_dir / "repo1.json").write_text(
        json.dumps({"uid": "r1", "name": "test-repo", "parent": ""}),
        encoding="UTF-8",
    )
    (profiles_dir / "profile1.json").write_text(
        json.dumps(
            {
                "uid": "p1",
                "name": "test-profile",
                "distro": "test-distro",
                "menu": "test-menu",
                "parent": "",
                "repos": ["test-repo"],
            }
        ),
        encoding="UTF-8",
    )
    (profiles_dir / "profile2.json").write_text(
        json.dumps(
            {
                "uid": "p2",
                "name": "child-profile",
                "distro": "<<inherit>>",
                "menu": "",
                "parent": "test-profile",
                "repos": [],
            }
        ),
        encoding="UTF-8",
    )
    (systems_dir / "system1.json").write_text(
        json.dumps(
            {
                "uid": "s1",
                "name": "test-system",
                "profile": "test-profile",
                "image": "",
                "parent": "",
            }
        ),
        encoding="UTF-8",
    )

    # Act
    V4_0_0.migrate_cobbler_uid_references(str(tmp_path))

    # Assert
    profile1 = json.loads((profiles_dir / "profile1.json").read_text(encoding="UTF-8"))
    assert profile1["distro"] == "d1"
    assert profile1["menu"] == "m1"
    assert profile1["repos"] == ["r1"]

    profile2 = json.loads((profiles_dir / "profile2.json").read_text(encoding="UTF-8"))
    assert profile2["distro"] == "<<inherit>>"
    assert profile2["menu"] == ""
    assert profile2["parent"] == "p1"

    system1 = json.loads((systems_dir / "system1.json").read_text(encoding="UTF-8"))
    assert system1["profile"] == "p1"
    assert system1["image"] == ""


def test_migrate_v4_0_0_item_options_reshape(tmp_path: pathlib.Path):
    # Arrange
    systems_dir = tmp_path / "systems"
    distros_dir = tmp_path / "distros"
    repos_dir = tmp_path / "repos"
    for directory in (systems_dir, distros_dir, repos_dir):
        directory.mkdir()

    system_file = systems_dir / "system1.json"
    system_file.write_text(
        json.dumps(
            {
                "uid": "s1",
                "name": "test-system",
                "power_address": "power.example.com",
                "power_id": "1",
                "power_pass": "secret",
                "power_type": "ipmilanplus",
                "power_user": "admin",
                "power_options": "",
                "power_identity_file": "",
                "virt_auto_boot": True,
                "virt_type": "kvm",
                "name_servers": ["192.0.2.1"],
                "name_servers_search": [],
                "next_server_v4": "192.0.2.2",
                "next_server_v6": "",
                "mgmt_classes": "<<inherit>>",
                "mgmt_parameters": {"from_cobbler": True},
            }
        ),
        encoding="UTF-8",
    )
    # A distro has none of these fields - must be left completely untouched.
    distro_file = distros_dir / "distro1.json"
    distro_file.write_text(
        json.dumps({"uid": "d1", "name": "test-distro"}), encoding="UTF-8"
    )
    repo_file = repos_dir / "repo1.json"
    repo_file.write_text(
        json.dumps(
            {
                "uid": "r1",
                "name": "test-repo",
                "apt_components": ["main"],
                "apt_dists": ["stable"],
            }
        ),
        encoding="UTF-8",
    )

    # Act
    V4_0_0.migrate_cobbler_item_options(str(tmp_path))

    # Assert
    data = json.loads(system_file.read_text(encoding="UTF-8"))
    assert "power_address" not in data
    assert data["power"] == {
        "address": "power.example.com",
        "id": "1",
        "password": "secret",
        "type": "ipmilanplus",
        "user": "admin",
        "options": "",
        "identity_file": "",
    }
    assert data["virt"] == {"auto_boot": True, "type": "kvm"}
    assert data["dns"] == {"name_servers": ["192.0.2.1"], "name_servers_search": []}
    assert data["tftp"] == {"next_server_v4": "192.0.2.2", "next_server_v6": ""}
    assert "mgmt_classes" not in data
    assert "mgmt_parameters" not in data

    distro_data = json.loads(distro_file.read_text(encoding="UTF-8"))
    assert "power" not in distro_data
    assert "virt" not in distro_data

    repo_data = json.loads(repo_file.read_text(encoding="UTF-8"))
    assert repo_data["apt"] == {"components": ["main"], "dists": ["stable"]}


def test_migrate_v4_0_0_network_interface_option_reshape(tmp_path: pathlib.Path):
    # Arrange
    systems_dir = tmp_path / "systems"
    systems_dir.mkdir()
    (tmp_path / "network_interfaces").mkdir()
    (systems_dir / "system1.json").write_text(
        json.dumps(
            {
                "uid": "s1",
                "name": "test-system",
                "interfaces": {
                    "default": {
                        "interface_type": "na",
                        "ip_address": "192.0.2.10",
                        "netmask": "255.255.255.0",
                        "mtu": "1500",
                        "static_routes": ["192.0.2.0/24"],
                        "ipv6_address": "2001:db8::1",
                        "ipv6_prefix": "64",
                        "ipv6_secondaries": ["2001:db8::2"],
                        "dns_name": "test-system.example.com",
                        "cnames": ["alias.example.com"],
                        "mac_address": "aa:bb:cc:dd:ee:ff",
                    }
                },
            }
        ),
        encoding="UTF-8",
    )

    # Act
    V4_0_0.migrate_cobbler_json_files(tmp_path)
    V4_0_0.migrate_cobbler_network_interfaces(tmp_path)

    # Assert
    interface_files = list((tmp_path / "network_interfaces").glob("*.json"))
    assert len(interface_files) == 1
    data = json.loads(interface_files[0].read_text(encoding="UTF-8"))
    assert data["ipv4"] == {
        "address": "192.0.2.10",
        "netmask": "255.255.255.0",
        "mtu": "1500",
        "static_routes": ["192.0.2.0/24"],
    }
    assert data["ipv6"] == {
        "address": "2001:db8::1",
        "prefix": "64",
        "secondaries": ["2001:db8::2"],
    }
    assert data["dns"] == {
        "name": "test-system.example.com",
        "common_names": ["alias.example.com"],
    }
    assert data["mac_address"] == "aa:bb:cc:dd:ee:ff"
    for old_key in (
        "ip_address",
        "netmask",
        "mtu",
        "static_routes",
        "ipv6_address",
        "ipv6_prefix",
        "ipv6_secondaries",
        "dns_name",
        "cnames",
    ):
        assert old_key not in data


def test_migrate_v4_0_0_autoinstall_templates_creates_and_rewrites(
    tmp_path: pathlib.Path,
):
    # Arrange
    templates_source_dir = tmp_path / "autoinstall_templates"
    templates_source_dir.mkdir()
    (templates_source_dir / "custom.ks").write_text("# kickstart", encoding="UTF-8")

    collections_dir = tmp_path / "collections"
    profiles_dir = collections_dir / "profiles"
    systems_dir = collections_dir / "systems"
    profiles_dir.mkdir(parents=True)
    systems_dir.mkdir()

    (profiles_dir / "profile1.json").write_text(
        json.dumps({"uid": "p1", "name": "profile1", "autoinstall": "custom.ks"}),
        encoding="UTF-8",
    )
    (systems_dir / "system1.json").write_text(
        json.dumps({"uid": "s1", "name": "system1", "autoinstall": "custom.ks"}),
        encoding="UTF-8",
    )
    (systems_dir / "system2.json").write_text(
        json.dumps({"uid": "s2", "name": "system2", "autoinstall": "missing.ks"}),
        encoding="UTF-8",
    )
    (systems_dir / "system3.json").write_text(
        json.dumps({"uid": "s3", "name": "system3", "autoinstall": "<<inherit>>"}),
        encoding="UTF-8",
    )
    settings_dict: Dict[str, str] = {"autoinstall": "custom.ks"}

    # Act
    V4_0_0.migrate_cobbler_autoinstall_templates(
        str(collections_dir), str(templates_source_dir), "cheetah", settings_dict
    )

    # Assert
    template_files = list((collections_dir / "templates").glob("*.json"))
    assert len(template_files) == 1  # deduped across profile1/system1/settings
    template_data = json.loads(template_files[0].read_text(encoding="UTF-8"))
    assert template_data["uri"] == {"schema": "file", "path": "custom.ks"}
    assert template_data["template_type"] == "cheetah"
    assert template_data["name"] == "custom.ks"

    profile1 = json.loads((profiles_dir / "profile1.json").read_text(encoding="UTF-8"))
    system1 = json.loads((systems_dir / "system1.json").read_text(encoding="UTF-8"))
    system2 = json.loads((systems_dir / "system2.json").read_text(encoding="UTF-8"))
    system3 = json.loads((systems_dir / "system3.json").read_text(encoding="UTF-8"))

    assert profile1["autoinstall"] == template_data["uid"]
    assert system1["autoinstall"] == template_data["uid"]
    assert system2["autoinstall"] == ""  # dangling reference dropped, not fatal
    assert system3["autoinstall"] == "<<inherit>>"  # untouched
    assert settings_dict["autoinstall"] == template_data["uid"]


def test_migrate_v4_0_0_autoinstall_templates_sanitizes_name(tmp_path: pathlib.Path):
    """
    Item names may only contain [a-zA-Z0-9_-.:] - a legacy autoinstall path with
    subdirectories (containing "/") must not be used verbatim as the
    synthesized Template's name.
    """
    # Arrange
    templates_source_dir = tmp_path / "autoinstall_templates"
    (templates_source_dir / "subdir").mkdir(parents=True)
    (templates_source_dir / "subdir" / "custom.ks").write_text("# ks", encoding="UTF-8")

    collections_dir = tmp_path / "collections"
    profiles_dir = collections_dir / "profiles"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "profile1.json").write_text(
        json.dumps(
            {"uid": "p1", "name": "profile1", "autoinstall": "subdir/custom.ks"}
        ),
        encoding="UTF-8",
    )

    # Act
    V4_0_0.migrate_cobbler_autoinstall_templates(
        str(collections_dir), str(templates_source_dir), "cheetah", {}
    )

    # Assert
    template_files = list((collections_dir / "templates").glob("*.json"))
    assert len(template_files) == 1
    template_data = json.loads(template_files[0].read_text(encoding="UTF-8"))
    assert template_data["name"] == "subdir:custom.ks"
    assert template_data["uri"]["path"] == "subdir/custom.ks"
