"""
Tests for the Cobbler V4.0.0 settings migration.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC
import glob
import json
import os
import pathlib
import shutil
import sqlite3
from typing import TYPE_CHECKING, Any, Dict

import pytest
import yaml

from cobbler.settings.migrations import V4_0_0

if TYPE_CHECKING:
    from pymongo.mongo_client import MongoClient

modules_conf_location = "/etc/cobbler/modules.conf"


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
    assert new_settings["modules"]["serializers"]["module"] == "serializers.sqlite"
    # "tftpd" is intentionally left at its default ("managers.in_tftpd" is the only
    # tftpd module implementation that exists) - key_drop_if_default() correctly
    # drops it entirely since every value in it matches the default.
    assert "tftpd" not in new_settings["modules"]
    # "httpd" did not exist as a modules.conf section in V3.3.7, so the fallback
    # default is always used here. Unlike "tftpd", it is not dropped by
    # key_drop_if_default() because the current Settings() defaults (see
    # cobbler/settings/__init__.py) do not have a "httpd" key to compare against.
    assert new_settings["modules"]["httpd"]["module"] == "managers.in_httpd"


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


def test_migrate_v4_0_0_iso_templates_known_files_tagged_active(tmp_path: pathlib.Path):
    # Arrange
    iso_dir = tmp_path / "iso"
    iso_dir.mkdir()
    (iso_dir / "buildiso.template").write_text("# buildiso", encoding="UTF-8")
    (iso_dir / "grub_menuentry.template").write_text(
        "# grub menuentry", encoding="UTF-8"
    )
    autoinstall_templates_dir = tmp_path / "autoinstall_templates"
    collections_dir = tmp_path / "collections"

    # Act
    V4_0_0.migrate_cobbler_iso_and_bootloader_templates(
        str(collections_dir),
        str(iso_dir),
        str(tmp_path / "nonexistent_boot_loader_conf"),
        str(autoinstall_templates_dir),
        "cheetah",
    )

    # Assert
    template_files = list((collections_dir / "templates").glob("*.json"))
    assert len(template_files) == 2
    by_tags = {
        tuple(sorted(json.loads(f.read_text(encoding="UTF-8"))["tags"])): json.loads(
            f.read_text(encoding="UTF-8")
        )
        for f in template_files
    }

    buildiso = by_tags[("active", "iso_buildiso")]
    assert buildiso["template_type"] == "cheetah"
    assert buildiso["uri"] == {"schema": "file", "path": "iso/buildiso.template"}
    assert buildiso["name"] == "iso:buildiso.template"
    assert (autoinstall_templates_dir / "iso" / "buildiso.template").read_text(
        encoding="UTF-8"
    ) == "# buildiso"

    grub = by_tags[("active", "iso_grub_menuentry")]
    assert grub["uri"] == {"schema": "file", "path": "iso/grub_menuentry.template"}


def test_migrate_v4_0_0_iso_templates_unknown_file_untagged(tmp_path: pathlib.Path):
    # Arrange
    iso_dir = tmp_path / "iso"
    iso_dir.mkdir()
    (iso_dir / "custom_extra.template").write_text("# custom", encoding="UTF-8")
    autoinstall_templates_dir = tmp_path / "autoinstall_templates"
    collections_dir = tmp_path / "collections"

    # Act
    V4_0_0.migrate_cobbler_iso_and_bootloader_templates(
        str(collections_dir),
        str(iso_dir),
        str(tmp_path / "nonexistent_boot_loader_conf"),
        str(autoinstall_templates_dir),
        "cheetah",
    )

    # Assert
    template_files = list((collections_dir / "templates").glob("*.json"))
    assert len(template_files) == 1
    data = json.loads(template_files[0].read_text(encoding="UTF-8"))
    assert "tags" not in data
    assert data["template_type"] == "cheetah"
    assert data["uri"] == {"schema": "file", "path": "iso/custom_extra.template"}


@pytest.mark.parametrize(
    "filename,tag", list(V4_0_0.BOOT_LOADER_CONF_TEMPLATE_TAGS.items())
)
def test_migrate_v4_0_0_bootloader_conf_templates_tagged_active(
    tmp_path: pathlib.Path, filename: str, tag: str
):
    # Arrange
    boot_loader_conf_dir = tmp_path / "boot_loader_conf"
    boot_loader_conf_dir.mkdir()
    (boot_loader_conf_dir / filename).write_text("# content", encoding="UTF-8")
    autoinstall_templates_dir = tmp_path / "autoinstall_templates"
    collections_dir = tmp_path / "collections"

    # Act
    V4_0_0.migrate_cobbler_iso_and_bootloader_templates(
        str(collections_dir),
        str(tmp_path / "nonexistent_iso"),
        str(boot_loader_conf_dir),
        str(autoinstall_templates_dir),
        "cheetah",
    )

    # Assert
    template_files = list((collections_dir / "templates").glob("*.json"))
    assert len(template_files) == 1
    data = json.loads(template_files[0].read_text(encoding="UTF-8"))
    assert sorted(data["tags"]) == sorted([tag, "active"])
    assert data["uri"] == {"schema": "file", "path": f"boot_loader_conf/{filename}"}
    assert data["template_type"] == "cheetah"


def test_migrate_v4_0_0_missing_legacy_template_dirs_are_noop(tmp_path: pathlib.Path):
    # Arrange
    collections_dir = tmp_path / "collections"
    collections_dir.mkdir()

    # Act
    V4_0_0.migrate_cobbler_iso_and_bootloader_templates(
        str(collections_dir),
        str(tmp_path / "no_iso"),
        str(tmp_path / "no_boot_loader_conf"),
        str(tmp_path / "autoinstall_templates"),
        "cheetah",
    )
    V4_0_0.migrate_cobbler_snippets_and_jinja_includes(
        str(collections_dir),
        str(tmp_path / "no_jinja2"),
        str(tmp_path / "no_snippets"),
        str(tmp_path / "autoinstall_templates"),
        "cheetah",
    )

    # Assert
    templates_dir = collections_dir / "templates"
    assert not templates_dir.exists() or list(templates_dir.glob("*.json")) == []


def test_migrate_v4_0_0_snippets_and_jinja_includes_creates_named_templates(
    tmp_path: pathlib.Path,
):
    # Arrange
    snippets_dir = tmp_path / "snippets"
    (snippets_dir / "kickstart").mkdir(parents=True)
    (snippets_dir / "kickstart" / "log_ks_post.template").write_text(
        "# snippet", encoding="UTF-8"
    )
    (snippets_dir / "network_config").write_text(
        "# top-level snippet", encoding="UTF-8"
    )
    jinja_dir = tmp_path / "jinja2"
    jinja_dir.mkdir()
    (jinja_dir / "header.jinja").write_text("# header", encoding="UTF-8")
    autoinstall_templates_dir = tmp_path / "autoinstall_templates"
    collections_dir = tmp_path / "collections"

    # Act
    V4_0_0.migrate_cobbler_snippets_and_jinja_includes(
        str(collections_dir),
        str(jinja_dir),
        str(snippets_dir),
        str(autoinstall_templates_dir),
        "cheetah",
    )

    # Assert
    template_files = list((collections_dir / "templates").glob("*.json"))
    assert len(template_files) == 3
    names = {json.loads(f.read_text(encoding="UTF-8"))["name"] for f in template_files}
    assert names == {
        "snippets:kickstart:log_ks_post.template",
        "snippets:network_config",
        "jinja2:header.jinja",
    }
    assert (
        autoinstall_templates_dir / "snippets" / "kickstart" / "log_ks_post.template"
    ).read_text(encoding="UTF-8") == "# snippet"
    assert (autoinstall_templates_dir / "jinja2" / "header.jinja").read_text(
        encoding="UTF-8"
    ) == "# header"
    for f in template_files:
        data = json.loads(f.read_text(encoding="UTF-8"))
        assert "tags" not in data


def test_migrate_v4_0_0_data_source_detection_file_only():
    # Arrange
    system_file = pathlib.Path("/var/lib/cobbler/collections/systems/fileonly.json")
    system_file.write_text(
        json.dumps({"uid": "s1", "name": "test", "mgmt_classes": "<<inherit>>"}),
        encoding="UTF-8",
    )
    settings_dict = {"modules": {"serializers": {"module": "serializers.file"}}}

    # Act
    V4_0_0.determine_and_migrate_collections_data(
        settings_dict,
        "/nonexistent_iso",
        "/nonexistent_boot_loader_conf",
        "/nonexistent_jinja2",
        "/nonexistent_snippets",
        "/var/lib/cobbler/templates",
        "cheetah",
    )

    # Assert
    migrated = json.loads(
        pathlib.Path("/var/lib/cobbler/collections/systems/s1.json").read_text(
            encoding="UTF-8"
        )
    )
    assert "mgmt_classes" not in migrated


def _cleanup_sqlite_test_artifacts(db_path: str) -> None:
    """
    Remove a test-created sqlite db and any backup files V4_0_0.py's sqlite
    backend may have created alongside it, so they don't leak into other tests.
    """
    if os.path.exists(db_path):
        os.remove(db_path)
    collections_dir = os.path.dirname(db_path)
    for backup_file in glob.glob(
        os.path.join(os.path.dirname(collections_dir), "collections.db.backup.*")
    ):
        os.remove(backup_file)


def test_migrate_v4_0_0_data_source_detection_sqlite_only():
    # Arrange
    db_path = "/var/lib/cobbler/collections/collections.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE systems(uid text primary key, item text)")
    connection.execute(
        "INSERT INTO systems(uid, item) VALUES (?, ?)",
        (
            "s1",
            json.dumps({"uid": "s1", "name": "test", "mgmt_classes": "<<inherit>>"}),
        ),
    )
    connection.commit()
    connection.close()
    settings_dict = {"modules": {"serializers": {"module": "serializers.sqlite"}}}

    try:
        # Act
        V4_0_0.determine_and_migrate_collections_data(
            settings_dict,
            "/nonexistent_iso",
            "/nonexistent_boot_loader_conf",
            "/nonexistent_jinja2",
            "/nonexistent_snippets",
            "/var/lib/cobbler/templates",
            "cheetah",
        )

        # Assert
        connection = sqlite3.connect(db_path)
        row = connection.execute(
            "SELECT item FROM systems WHERE uid = ?", ("s1",)
        ).fetchone()
        connection.close()
        data = json.loads(row[0])
        assert "mgmt_classes" not in data
    finally:
        _cleanup_sqlite_test_artifacts(db_path)


def test_migrate_v4_0_0_data_source_detection_refuses_multiple_sources():
    # Arrange
    system_file = pathlib.Path("/var/lib/cobbler/collections/systems/fileonly.json")
    system_file.write_text(json.dumps({"uid": "s1", "name": "test"}), encoding="UTF-8")
    db_path = "/var/lib/cobbler/collections/collections.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE systems(uid text primary key, item text)")
    connection.execute(
        "INSERT INTO systems(uid, item) VALUES (?, ?)",
        ("s2", json.dumps({"uid": "s2", "name": "test2"})),
    )
    connection.commit()
    connection.close()
    settings_dict = {"modules": {"serializers": {"module": "serializers.file"}}}

    try:
        # Act & Assert
        with pytest.raises(V4_0_0.AmbiguousDataSourceError):
            V4_0_0.determine_and_migrate_collections_data(
                settings_dict,
                "/nonexistent_iso",
                "/nonexistent_boot_loader_conf",
                "/nonexistent_jinja2",
                "/nonexistent_snippets",
                "/var/lib/cobbler/templates",
                "cheetah",
            )
    finally:
        _cleanup_sqlite_test_artifacts(db_path)


def test_migrate_v4_0_0_mongodb_declared_but_unreachable_raises():
    # Arrange
    settings_dict = {
        "modules": {"serializers": {"module": "serializers.mongodb"}},
        "mongodb": {"host": "nonexistent-host-for-test.invalid", "port": 27099},
    }

    # Act & Assert
    with pytest.raises(RuntimeError, match="MongoDB"):
        V4_0_0.determine_and_migrate_collections_data(
            settings_dict,
            "/nonexistent_iso",
            "/nonexistent_boot_loader_conf",
            "/nonexistent_jinja2",
            "/nonexistent_snippets",
            "/var/lib/cobbler/templates",
            "cheetah",
        )


def test_migrate_v4_0_0_sqlite_backend_full_pipeline():
    # Arrange
    db_path = "/var/lib/cobbler/collections/collections.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE distros(uid text primary key, item text)")
    connection.execute("CREATE TABLE profiles(uid text primary key, item text)")
    connection.execute(
        "INSERT INTO distros(uid, item) VALUES (?, ?)",
        ("d1", json.dumps({"uid": "d1", "name": "test-distro"})),
    )
    connection.execute(
        "INSERT INTO profiles(uid, item) VALUES (?, ?)",
        (
            "p1",
            json.dumps({"uid": "p1", "name": "test-profile", "distro": "test-distro"}),
        ),
    )
    connection.commit()
    connection.close()
    settings_dict = {"modules": {"serializers": {"module": "serializers.sqlite"}}}

    try:
        # Act
        V4_0_0.determine_and_migrate_collections_data(
            settings_dict,
            "/nonexistent_iso",
            "/nonexistent_boot_loader_conf",
            "/nonexistent_jinja2",
            "/nonexistent_snippets",
            "/var/lib/cobbler/templates",
            "cheetah",
        )

        # Assert - the profile's "distro" reference was rewritten from name to uid,
        # proving the full shared pipeline (not just a pass-through) ran against
        # the sqlite-sourced data.
        connection = sqlite3.connect(db_path)
        profile_row = connection.execute(
            "SELECT item FROM profiles WHERE uid = ?", ("p1",)
        ).fetchone()
        connection.close()
        profile_data = json.loads(profile_row[0])
        assert profile_data["distro"] == "d1"
    finally:
        _cleanup_sqlite_test_artifacts(db_path)


@pytest.mark.mongodb
def test_migrate_v4_0_0_mongodb_backend_full_pipeline():
    """
    Full round-trip against the real MongoDB service from docker/tests/compose.yml
    (hostname "mongo"), matching the existing convention in
    tests/modules/serializer/mongodb_test.py.
    """
    # pylint: disable-next=import-outside-toplevel
    import pymongo

    client: "MongoClient[Dict[str, Any]]" = pymongo.MongoClient(
        "mongo", 27017, serverSelectionTimeoutMS=3000
    )
    database = client["cobbler"]
    collection_types = V4_0_0.LEGACY_COLLECTION_TYPES + V4_0_0.NEW_COLLECTION_TYPES
    try:
        # Arrange
        for collection_type in collection_types:
            database[collection_type].delete_many({})
        database["distros"].insert_one({"uid": "d1", "name": "test-distro"})
        database["profiles"].insert_one(
            {"uid": "p1", "name": "test-profile", "distro": "test-distro"}
        )
        settings_dict = {
            "modules": {"serializers": {"module": "serializers.mongodb"}},
            "mongodb": {"host": "mongo", "port": 27017},
        }

        # Act
        V4_0_0.determine_and_migrate_collections_data(
            settings_dict,
            "/nonexistent_iso",
            "/nonexistent_boot_loader_conf",
            "/nonexistent_jinja2",
            "/nonexistent_snippets",
            "/var/lib/cobbler/templates",
            "cheetah",
        )

        # Assert - the profile's "distro" reference was rewritten from name to
        # uid, proving the full shared pipeline ran against the Mongo-sourced data.
        profile_doc = database["profiles"].find_one({"uid": "p1"})
        assert profile_doc is not None
        assert profile_doc["distro"] == "d1"
    finally:
        for collection_type in collection_types:
            database[collection_type].delete_many({})
        client.close()


@pytest.mark.mongodb
def test_migrate_v4_0_0_mongodb_declared_and_reachable_but_empty_is_noop():
    """
    If serializers.mongodb is declared and the server IS reachable, but holds no
    actual collection data, the migration must not raise - there's simply nothing
    to migrate (e.g. a fresh install that hasn't been used yet).
    """
    # pylint: disable-next=import-outside-toplevel
    import pymongo

    client: "MongoClient[Dict[str, Any]]" = pymongo.MongoClient(
        "mongo", 27017, serverSelectionTimeoutMS=3000
    )
    database = client["cobbler"]
    collection_types = V4_0_0.LEGACY_COLLECTION_TYPES + V4_0_0.NEW_COLLECTION_TYPES
    try:
        for collection_type in collection_types:
            database[collection_type].delete_many({})
        settings_dict = {
            "modules": {"serializers": {"module": "serializers.mongodb"}},
            "mongodb": {"host": "mongo", "port": 27017},
        }

        # Act & Assert - must not raise
        V4_0_0.determine_and_migrate_collections_data(
            settings_dict,
            "/nonexistent_iso",
            "/nonexistent_boot_loader_conf",
            "/nonexistent_jinja2",
            "/nonexistent_snippets",
            "/var/lib/cobbler/templates",
            "cheetah",
        )
    finally:
        for collection_type in collection_types:
            database[collection_type].delete_many({})
        client.close()


def test_normalize_v4_0_0_empty():
    # Arrange

    # Act
    settings = V4_0_0.normalize({})

    # Assert
    assert len(settings) == 0


def test_normalize_v4_0_0_partial():
    # Arrange
    old_settings_dict = {"server": "192.168.0.1"}

    # Act
    settings = V4_0_0.normalize(old_settings_dict)

    # Assert
    assert old_settings_dict == settings


def test_normalize_v4_0_0_full():
    # Arrange
    with open(
        "/code/tests/test_data/V4_0_0/settings.yaml", encoding="UTF-8"
    ) as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V4_0_0.normalize(old_settings_dict)

    # Assert
    assert "mongodb" in new_settings
    assert new_settings["mongodb"] == {"host": "localhost", "port": 27017}
    assert "cache_enabled" in new_settings
    assert new_settings["cache_enabled"] == False
    assert new_settings["lazy_start"] == False
    assert len(V4_0_0.normalize(new_settings)) == 135


def test_schema_v4_0_0_modules_httpd_missing_is_valid():
    """
    "modules.httpd" is Optional, like every other "modules" sub-key - a settings
    dict that omits it entirely must still validate.
    """
    # Arrange
    settings = {"modules": {"tftpd": {"module": "managers.in_tftpd"}}}

    # Act & Assert
    assert V4_0_0.validate(settings)


@pytest.mark.parametrize(
    "httpd_module", ["managers.in_httpd", "managers.dynamic_httpd"]
)
def test_schema_v4_0_0_modules_httpd_module_values(httpd_module: str):
    """
    "modules.httpd.module" is an unrestricted str, like the other manager
    categories - both the shipped default ("managers.in_httpd") and the
    dynamic_httpd manager added alongside it must validate.
    """
    # Arrange
    settings = {"modules": {"httpd": {"module": httpd_module}}}

    # Act & Assert
    assert V4_0_0.validate(settings)


@pytest.mark.parametrize("setting_name", ["xmlrpc_bind_address", "xmlrpc_host"])
def test_schema_v4_0_0_xmlrpc_split_container_settings_accept_str(setting_name: str):
    """
    Both new split-container settings (the daemon's bind address and the address the web
    service dials to reach it) must validate as plain strings, matching how ``xmlrpc_port``
    is already handled in this schema.
    """
    # Arrange
    settings_dict = {setting_name: "cobblerd"}

    # Act & Assert
    assert V4_0_0.validate(settings_dict)


@pytest.mark.parametrize("setting_name", ["xmlrpc_bind_address", "xmlrpc_host"])
def test_schema_v4_0_0_xmlrpc_split_container_settings_reject_non_str(
    setting_name: str,
):
    # Arrange
    settings_dict = {setting_name: 25151}

    # Act & Assert
    assert not V4_0_0.validate(settings_dict)


def test_schema_v4_0_0_default_settings_yaml_validates():
    """
    The shipped default settings.yaml must validate cleanly against the V4.0.0
    schema, including its "modules.httpd" entry.

    Reads the source file directly (not the installed /etc/cobbler/settings.yaml)
    since several migration tests in this same module intentionally overwrite the
    latter as a side effect of exercising update_settings_file()'s default
    filepath - the source file is the one this task actually changed and is never
    mutated by any test.
    """
    # Arrange
    with open(
        "/code/cobbler/data/config/cobbler/settings.yaml", encoding="UTF-8"
    ) as settings_file:
        shipped_settings = yaml.safe_load(settings_file.read())

    # Act & Assert
    assert V4_0_0.validate(shipped_settings)
    assert shipped_settings["modules"]["httpd"]["module"] == "managers.in_httpd"
    # Both new split-container settings must default to today's exact non-containerized
    # behavior - no default-behavior change is acceptable.
    assert shipped_settings["xmlrpc_bind_address"] == "127.0.0.1"
    assert shipped_settings["xmlrpc_host"] == "127.0.0.1"
