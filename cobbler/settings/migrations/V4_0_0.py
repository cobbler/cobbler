"""
Migration from V3.3.3 to V4.0.0
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2022 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC

import configparser
import glob
import json
import logging
import os
import pathlib
import uuid
from configparser import ConfigParser
from typing import Any, Dict

from schema import Optional, Schema, SchemaError  # type: ignore

from cobbler.settings.migrations import V3_3_7, helper

logger = logging.getLogger()

schema = Schema(
    {
        Optional("auto_migrate_settings"): bool,
        Optional("allow_duplicate_hostnames"): bool,
        Optional("allow_duplicate_ips"): bool,
        Optional("allow_duplicate_macs"): bool,
        Optional("allow_dynamic_settings"): bool,
        Optional("always_write_dhcp_entries"): bool,
        Optional("anamon_enabled"): bool,
        Optional("auth_token_expiration"): int,
        Optional("authn_pam_service"): str,
        Optional("autoinstall_templates_dir"): str,
        Optional("bind_chroot_path"): str,
        Optional("bind_zonefile_path"): str,
        Optional("bind_master"): str,
        Optional("bootloaders_dir"): str,
        Optional("bootloaders_formats"): dict,
        Optional("bootloaders_modules"): list,
        Optional("bootloaders_shim_folder"): str,
        Optional("bootloaders_shim_file"): str,
        Optional("secure_boot_grub_folder"): str,
        Optional("secure_boot_grub_file"): str,
        Optional("bootloaders_ipxe_folder"): str,
        Optional("syslinux_dir"): str,
        Optional("syslinux_memdisk_folder"): str,
        Optional("syslinux_pxelinux_folder"): str,
        Optional("genders_settings_file"): str,
        Optional("grub2_mod_dir"): str,
        Optional("grubconfig_dir"): str,
        Optional("build_reporting_enabled"): bool,
        Optional("build_reporting_email"): [str],
        Optional("build_reporting_ignorelist"): [str],
        Optional("build_reporting_sender"): str,
        Optional("build_reporting_smtp_server"): str,
        Optional("build_reporting_subject"): str,
        Optional("buildisodir"): str,
        Optional("cheetah_import_whitelist"): [str],
        Optional("client_use_https"): bool,
        Optional("client_use_localhost"): bool,
        Optional("cobbler_master"): str,
        Optional("convert_server_to_ip"): bool,
        Optional("createrepo_flags"): str,
        Optional("autoinstall"): str,
        Optional("default_name_servers"): [str],
        Optional("default_name_servers_search"): [str],
        Optional("default_ownership"): [str],
        Optional("default_password_crypted"): str,
        Optional("default_template_type"): str,
        Optional("default_virt_bridge"): str,
        Optional("default_virt_disk_driver"): str,
        Optional("default_virt_file_size"): float,
        Optional("default_virt_ram"): int,
        Optional("default_virt_type"): str,
        Optional("dnsmasq_ethers_file"): str,
        Optional("dnsmasq_hosts_file"): str,
        Optional("dnsmasq_settings_file"): str,
        Optional("enable_ipxe"): bool,
        Optional("enable_menu"): bool,
        Optional("extra_settings_list"): [str],
        Optional("http_port"): int,
        Optional("kernel_options"): dict,
        Optional("ldap_anonymous_bind"): bool,
        Optional("ldap_base_dn"): str,
        Optional("ldap_port"): int,
        Optional("ldap_search_bind_dn"): str,
        Optional("ldap_search_passwd"): str,
        Optional("ldap_search_prefix"): str,
        Optional("ldap_server"): str,
        Optional("ldap_tls"): bool,
        Optional("ldap_tls_cacertdir"): str,
        Optional("ldap_tls_cacertfile"): str,
        Optional("ldap_tls_certfile"): str,
        Optional("ldap_tls_keyfile"): str,
        Optional("ldap_tls_reqcert"): str,
        Optional("ldap_tls_cipher_suite"): str,
        Optional("bind_manage_ipmi"): bool,
        Optional("manage_dhcp_v4"): bool,
        Optional("manage_dhcp_v6"): bool,
        Optional("manage_dns"): bool,
        Optional("manage_forward_zones"): [str],
        Optional("manage_reverse_zones"): [str],
        Optional("manage_genders"): bool,
        Optional("manage_rsync"): bool,
        Optional("manage_tftpd"): bool,
        Optional("next_server_v4"): str,
        Optional("next_server_v6"): str,
        Optional("ndjbdns_data_file"): str,
        Optional("nsupdate_enabled"): bool,
        Optional("nsupdate_log"): str,
        Optional("nsupdate_tsig_algorithm"): str,
        Optional("nsupdate_tsig_key"): [str],
        Optional("power_management_default_type"): str,
        Optional("proxies"): [str],
        Optional("proxy_url_ext"): str,
        Optional("proxy_url_int"): str,
        Optional("puppet_auto_setup"): bool,
        Optional("puppet_parameterized_classes"): bool,
        Optional("puppet_server"): str,
        Optional("puppet_version"): int,
        Optional("puppetca_path"): str,
        Optional("pxe_just_once"): bool,
        Optional("nopxe_with_triggers"): bool,
        Optional("redhat_management_permissive"): bool,
        Optional("redhat_management_server"): str,
        Optional("redhat_management_key"): str,
        Optional("redhat_management_org"): str,
        Optional("redhat_management_user"): str,
        Optional("redhat_management_password"): str,
        Optional("uyuni_authentication_endpoint"): str,
        Optional("register_new_installs"): bool,
        Optional("remove_old_puppet_certs_automatically"): bool,
        Optional("replicate_repo_rsync_options"): str,
        Optional("replicate_rsync_options"): str,
        Optional("reposync_flags"): str,
        Optional("reposync_rsync_flags"): str,
        Optional("restart_dhcp"): bool,
        Optional("restart_dns"): bool,
        Optional("run_install_triggers"): bool,
        Optional("scm_track_enabled"): bool,
        Optional("scm_track_mode"): str,
        Optional("scm_track_author"): str,
        Optional("scm_push_script"): str,
        Optional("serializer_pretty_json"): bool,
        Optional("server"): str,
        Optional("sign_puppet_certs_automatically"): bool,
        Optional("signature_path"): str,
        Optional("signature_url"): str,
        Optional("tftpboot_location"): str,
        Optional("virt_auto_boot"): bool,
        Optional("webdir"): str,
        Optional("webdir_whitelist"): [str],
        Optional("xmlrpc_port"): int,
        Optional("yum_distro_priority"): int,
        Optional("yum_post_install_mirror"): bool,
        Optional("yumdownloader_flags"): str,
        Optional("windows_enabled"): bool,
        Optional("windows_wimupdate_location"): str,
        Optional("samba_distro_share"): str,
        Optional("modules"): {
            Optional("authentication"): {
                Optional("module"): str,
                Optional("hash_algorithm"): str,
            },
            Optional("authorization"): {Optional("module"): str},
            Optional("dns"): {Optional("module"): str},
            Optional("dhcp"): {Optional("module"): str},
            Optional("tftpd"): {Optional("module"): str},
            Optional("serializers"): {Optional("module"): str},
        },
        Optional("mongodb"): {
            Optional("host"): str,
            Optional("port"): int,
        },
        Optional("cache_enabled"): bool,
        Optional("autoinstall_scheme"): str,
        Optional("lazy_start"): bool,
        Optional("memory_indexes"): {
            Optional("distro"): {
                Optional("name"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("arch"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
            },
            Optional("image"): {
                Optional("name"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("arch"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("menu"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
            },
            Optional("menu"): {
                Optional("name"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("parent"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
            },
            Optional("network_interface"): {
                Optional("name"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("mac_address"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("ipv4.address"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("ipv6.address"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("dns.name"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
            },
            Optional("profile"): {
                Optional("name"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("parent"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("distro"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("arch"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("menu"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("repos"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
            },
            Optional("repo"): {
                Optional("name"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
            },
            Optional("system"): {
                Optional("name"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("image"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("profile"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
            },
            Optional("distro_group"): {
                Optional("name"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
            },
            Optional("profile_group"): {
                Optional("name"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
            },
            Optional("system_group"): {
                Optional("name"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
            },
        },
    },  # type: ignore
    ignore_extra_keys=False,
)


def validate(settings: Dict[str, Any]) -> bool:
    """
    Checks that a given settings dict is valid according to the reference V4.0.0 schema ``schema``.

    :param settings: The settings dict to validate.
    :return: True if valid settings dict otherwise False.
    """
    try:
        schema.validate(settings)  # type: ignore
    except SchemaError:
        return False
    return True


def normalize(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    If data in ``settings`` is valid the validated data is returned.

    :param settings: The settings dict to validate.
    :return: The validated dict.
    """

    # We are aware of our schema and thus can safely ignore this.
    return schema.validate(settings)  # type: ignore


def migrate(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migration of the settings ``settings`` to version V4.0.0 settings

    :param settings: The settings dict to migrate
    :return: The migrated dict
    """

    if not V3_3_7.validate(settings):
        raise SchemaError("V3.3.7: Schema error while validating")

    # rename keys and update their value if needed
    include = settings.pop("include")
    settings.pop("mgmt_classes")
    settings.pop("mgmt_parameters")
    settings.pop("manage_dhcp")
    jinja2_includedir = settings.pop("jinja2_includedir")
    iso_template_dir = settings.pop("iso_template_dir")
    boot_loader_conf_template_dir = settings.pop("boot_loader_conf_template_dir")
    autoinstall_snippets_dir = settings.pop("autoinstall_snippets_dir")
    settings.pop("windows_template_dir", None)

    # These two are not popped (they still exist in the V4.0.0 schema), but they may be
    # dropped later on by key_drop_if_default() if they equal their defaults - capture
    # them now for migrate_cobbler_autoinstall_templates() further down.
    autoinstall_templates_dir = settings.get(
        "autoinstall_templates_dir", "/var/lib/cobbler/templates"
    )
    default_template_type = settings.get("default_template_type", "cheetah")

    # Do mongodb.conf migration
    mongodb_config = "/etc/cobbler/mongodb.conf"
    modules_config_parser = ConfigParser()
    try:
        modules_config_parser.read(mongodb_config)
    except configparser.Error as cp_error:
        raise configparser.Error(
            "Could not read Cobbler MongoDB config file!"
        ) from cp_error
    settings["mongodb"] = {
        "host": modules_config_parser.get("connection", "host", fallback="localhost"),
        "port": modules_config_parser.getint("connection", "port", fallback=27017),
    }
    mongodb_config_path = pathlib.Path(mongodb_config)
    if mongodb_config_path.exists():
        mongodb_config_path.unlink()

    # Do modules.conf migration
    modules_config = "/etc/cobbler/modules.conf"
    modules_config_parser = ConfigParser()
    try:
        modules_config_parser.read(modules_config)
    except configparser.Error as cp_error:
        raise configparser.Error(
            "Could not read Cobbler modules.conf config file!"
        ) from cp_error
    settings["modules"] = {
        "authentication": {
            "module": modules_config_parser.get(
                "authentication", "module", fallback="authentication.configfile"
            ),
            "hash_algorithm": modules_config_parser.get(
                "authentication", "hash_algorithm", fallback="sha3_512"
            ),
        },
        "authorization": {
            "module": modules_config_parser.get(
                "authorization", "module", fallback="authorization.allowall"
            )
        },
        "dns": {
            "module": modules_config_parser.get(
                "dns", "module", fallback="managers.bind"
            )
        },
        "dhcp": {
            "module": modules_config_parser.get(
                "dhcp", "module", fallback="managers.isc"
            )
        },
        "tftpd": {
            "module": modules_config_parser.get(
                "tftpd", "module", fallback="managers.in_tftpd"
            )
        },
        "serializers": {
            "module": modules_config_parser.get(
                "serializers", "module", fallback="serializers.file"
            )
        },
    }
    modules_config_path = pathlib.Path(modules_config)
    if modules_config_path.exists():
        modules_config_path.unlink()

    # Migrate Jinja include directory to new location
    # TODO: Implement
    _ = jinja2_includedir

    # Migrate ISO template directory to new location
    # TODO: Implement
    _ = iso_template_dir

    # Migrate boot-loader conf template directory to new location
    # TODO: Implement
    _ = boot_loader_conf_template_dir

    # Migrate autoinstall snippets directory to new location
    # TODO: Implement
    _ = autoinstall_snippets_dir

    collection_folder = pathlib.Path("/var/lib/cobbler/collections/")
    # Back up the pristine collections tree once, before any of the following steps
    # mutate it.
    helper.backup_dir(str(collection_folder))
    # Rewrite cross-item references (distro/profile/image/menu/repos/parent) from
    # the old name-based values to the new uid-based ones.
    migrate_cobbler_uid_references(str(collection_folder))
    # Reshape flat legacy fields (power_*/virt_*/name_servers*/next_server_*/apt_*)
    # into their new nested Option sub-object shape, and drop per-item
    # mgmt_classes/mgmt_parameters (no longer supported at the item level).
    migrate_cobbler_item_options(str(collection_folder))
    # migrate stored cobbler collections
    migrate_cobbler_collections(str(collection_folder))
    # Create dedicated Template records for legacy autoinstall path references -
    # both per-item and the global settings default - and rewrite those
    # references to the new Template's uid. Must run before key_drop_if_default()/
    # update_settings_file() below, since it mutates settings["autoinstall"] in
    # place and that needs to reach the settings.yaml that gets written to disk.
    migrate_cobbler_autoinstall_templates(
        str(collection_folder),
        autoinstall_templates_dir,
        default_template_type,
        settings,
    )
    # Migrate JSON filenames
    migrate_cobbler_json_files(collection_folder)
    # Migrate SQLite DB
    # TODO
    # Migrate MongoDB
    # TODO
    # Migrate Network Interfaces to dedicated collection
    migrate_cobbler_network_interfaces(collection_folder)

    # Drop defaults
    # pylint: disable-next=import-outside-toplevel
    from cobbler.settings import Settings

    helper.key_drop_if_default(settings, Settings().to_dict())

    # Write settings to disk
    # pylint: disable-next=import-outside-toplevel
    from cobbler.settings import update_settings_file

    update_settings_file(settings)

    for include_path in include:
        # "include" entries are glob patterns (e.g. "/etc/cobbler/settings.d/*.settings"),
        # not literal directory paths, so the directory to clean up is the pattern's parent.
        include_directory = pathlib.Path(include_path).parent
        if include_directory.is_dir() and not any(include_directory.iterdir()):
            include_directory.rmdir()

    return normalize(settings)


def migrate_cobbler_collections(collections_dir: str) -> None:
    """
    Manipulate the main Cobbler stored collections and migrate deprecated settings
    to work with newer Cobbler versions.

    :param collections_dir: The directory of Cobbler where the collections files are.
    """
    # Migrate changed properties
    for collection_file in glob.glob(
        os.path.join(collections_dir, "**/*.json"), recursive=True
    ):
        data = None
        with open(collection_file, encoding="utf-8") as _f:
            data = json.loads(_f.read())

        # migrate interface.interface_type from empty string to "NA"
        if "interfaces" in data:
            for iface in data["interfaces"]:
                if data["interfaces"][iface]["interface_type"] == "":
                    data["interfaces"][iface]["interface_type"] = "NA"

        # Remove fetchable_files from the items
        if "fetchable_files" in data:
            data.pop("fetchable_files", None)

        # Migrate boot_files to template_files
        if "boot_files" in data and "template_files" in data:
            # Dicts can both be implicitly and explicitly inherited
            old_boot_files = data.pop("boot_files")
            if old_boot_files != "<<inherit>>":
                data["template_files"] = {**data["template_files"], **old_boot_files}

        with open(collection_file, "w", encoding="utf-8") as _f:
            _f.write(json.dumps(data))


def migrate_cobbler_json_files(collection_folder: pathlib.Path) -> None:
    """
    Rename all JSON files from name-based files to uid-based files.

    :param collection_folder: The directory of Cobbler where the collections files are.
    """
    for folder in pathlib.Path(collection_folder).iterdir():
        for file in folder.iterdir():
            if not file.name.endswith(".json"):
                continue
            uid = json.loads(file.read_text(encoding="UTF-8")).get("uid")
            file.rename(file.parent / f"{uid}.json")


def migrate_cobbler_network_interfaces(collection_folder: pathlib.Path) -> None:
    """
    Move all network interfaces from embedded system files to the dedicated collection.

    :param collection_folder: The directory of Cobbler where the collections files are.
    """
    for file in (collection_folder / "systems").iterdir():
        if not file.name.endswith(".json"):
            continue
        system_dict = json.loads(file.read_text(encoding="UTF-8"))
        interfaces = system_dict.pop("interfaces")
        for interface_name, interface_dict in interfaces.items():
            interface_uid = uuid.uuid4().hex
            interface_file = (
                collection_folder / "network_interfaces" / f"{interface_uid}.json"
            )
            # Set uid & name and system uid of the interface
            interface_dict["uid"] = interface_uid
            interface_dict["name"] = interface_name
            interface_dict["system_uid"] = system_dict["uid"]
            _reshape_interface_options(interface_dict)
            interface_file.write_text(json.dumps(interface_dict), encoding="UTF-8")
        file.write_text(json.dumps(system_dict), encoding="UTF-8")


def _reshape_interface_options(interface_dict: Dict[str, Any]) -> None:
    """
    Reshape a V3.3.7 network interface's flat IPv4/IPv6/DNS fields into the nested
    ipv4/ipv6/dns Option sub-object shape used by V4.0.0.

    The legacy schema only tracked a single ``mtu`` value per interface; it is
    assigned to ``ipv4.mtu`` since V3.3.x only supported one MTU setting per
    interface and IPv4 was always configured. ``ipv6.mtu`` is left unset.

    :param interface_dict: The interface dict to reshape, modified in place.
    """
    ipv4: Dict[str, Any] = {}
    for old_key, new_key in (
        ("ip_address", "address"),
        ("netmask", "netmask"),
        ("mtu", "mtu"),
        ("static_routes", "static_routes"),
    ):
        if old_key in interface_dict:
            ipv4[new_key] = interface_dict.pop(old_key)
    if ipv4:
        interface_dict["ipv4"] = ipv4

    ipv6: Dict[str, Any] = {}
    for old_key, new_key in (
        ("ipv6_address", "address"),
        ("ipv6_prefix", "prefix"),
        ("ipv6_secondaries", "secondaries"),
        ("ipv6_mtu", "mtu"),
    ):
        if old_key in interface_dict:
            ipv6[new_key] = interface_dict.pop(old_key)
    if ipv6:
        interface_dict["ipv6"] = ipv6

    dns: Dict[str, Any] = {}
    for old_key, new_key in (
        ("dns_name", "name"),
        ("cnames", "common_names"),
    ):
        if old_key in interface_dict:
            dns[new_key] = interface_dict.pop(old_key)
    if dns:
        interface_dict["dns"] = dns


def migrate_cobbler_uid_references(collections_dir: str) -> None:
    """
    Rewrite cross-item reference fields that stored the referenced item's name in
    V3.3.7 to use its uid instead, matching the V4.0.0 item model where items are
    looked up by uid rather than name.

    :param collections_dir: The directory of Cobbler where the collections files are.
    """
    # For each collection type, the fields it has that reference another item by
    # name, mapped to the collection type they reference.
    scalar_reference_fields = {
        "distros": {"parent": "distros"},
        "profiles": {"distro": "distros", "menu": "menus", "parent": "profiles"},
        "systems": {"profile": "profiles", "image": "images", "parent": "systems"},
        "images": {"menu": "menus", "parent": "images"},
        "menus": {"parent": "menus"},
        "repos": {"parent": "repos"},
    }
    list_reference_fields = {
        "profiles": {"repos": "repos"},
    }

    referenced_collections = {
        target
        for fields in scalar_reference_fields.values()
        for target in fields.values()
    } | {
        target
        for fields in list_reference_fields.values()
        for target in fields.values()
    }

    name_to_uid: Dict[str, Dict[str, str]] = {}
    for collection_type in referenced_collections:
        mapping: Dict[str, str] = {}
        for collection_file in glob.glob(
            os.path.join(collections_dir, collection_type, "*.json")
        ):
            with open(collection_file, encoding="UTF-8") as _f:
                data = json.loads(_f.read())
            if "name" in data and "uid" in data:
                mapping[data["name"]] = data["uid"]
        name_to_uid[collection_type] = mapping

    def resolve(value: str, target_collection: str) -> str:
        if value in ("", "<<inherit>>"):
            return value
        return name_to_uid.get(target_collection, {}).get(value, value)

    for collection_type, fields in scalar_reference_fields.items():
        for collection_file in glob.glob(
            os.path.join(collections_dir, collection_type, "*.json")
        ):
            with open(collection_file, encoding="UTF-8") as _f:
                data = json.loads(_f.read())
            changed = False
            for field, target_collection in fields.items():
                if field in data and isinstance(data[field], str):
                    new_value = resolve(data[field], target_collection)
                    if new_value != data[field]:
                        data[field] = new_value
                        changed = True
            for field, target_collection in list_reference_fields.get(
                collection_type, {}
            ).items():
                if field in data and isinstance(data[field], list):
                    new_values = [resolve(v, target_collection) for v in data[field]]
                    if new_values != data[field]:
                        data[field] = new_values
                        changed = True
            if changed:
                with open(collection_file, "w", encoding="UTF-8") as _f:
                    _f.write(json.dumps(data))


def migrate_cobbler_item_options(collections_dir: str) -> None:
    """
    Reshape flat legacy item fields that were moved into nested "Option"
    sub-objects in V4.0.0 (e.g. ``power_address`` -> ``power.address``), and drop
    the per-item ``mgmt_classes``/``mgmt_parameters`` fields, which no longer exist
    on any item class.

    :param collections_dir: The directory of Cobbler where the collections files are.
    """
    option_field_maps = {
        "power": {
            "power_address": "address",
            "power_id": "id",
            "power_pass": "password",
            "power_type": "type",
            "power_user": "user",
            "power_options": "options",
            "power_identity_file": "identity_file",
        },
        "virt": {
            "virt_auto_boot": "auto_boot",
            "virt_cpus": "cpus",
            "virt_disk_driver": "disk_driver",
            "virt_file_size": "file_size",
            "virt_path": "path",
            "virt_pxe_boot": "pxe_boot",
            "virt_ram": "ram",
            "virt_type": "type",
        },
        "dns": {
            "name_servers": "name_servers",
            "name_servers_search": "name_servers_search",
        },
        "tftp": {
            "next_server_v4": "next_server_v4",
            "next_server_v6": "next_server_v6",
        },
        "apt": {
            "apt_components": "components",
            "apt_dists": "dists",
        },
    }

    for collection_file in glob.glob(
        os.path.join(collections_dir, "**/*.json"), recursive=True
    ):
        with open(collection_file, encoding="UTF-8") as _f:
            data = json.loads(_f.read())

        data.pop("mgmt_classes", None)
        data.pop("mgmt_parameters", None)

        for option_name, field_map in option_field_maps.items():
            option_dict: Dict[str, Any] = {}
            for old_key, new_key in field_map.items():
                if old_key in data:
                    option_dict[new_key] = data.pop(old_key)
            if option_dict:
                data[option_name] = option_dict

        with open(collection_file, "w", encoding="UTF-8") as _f:
            _f.write(json.dumps(data))


def migrate_cobbler_autoinstall_templates(
    collections_dir: str,
    autoinstall_templates_dir: str,
    default_template_type: str,
    settings: Dict[str, Any],
) -> None:
    """
    Create dedicated Template collection records for legacy ``autoinstall`` path
    references - both per-item (profile/system/image) and the global
    ``settings["autoinstall"]`` default, which items with an inherited/unset
    autoinstall resolve to (V4.0.0 replaced the flat path string with a
    reference to a Template item in both places) - and rewrite each reference to
    the new Template's uid.

    A legacy reference to a file that no longer exists under
    ``autoinstall_templates_dir`` is dropped (with a warning) instead of causing
    the whole referencing item to fail to load later.

    :param collections_dir: The directory of Cobbler where the collections files are.
    :param autoinstall_templates_dir: The directory autoinstall template paths are relative to.
    :param default_template_type: The template engine to assign to synthesized Template records.
    :param settings: The settings dict, whose "autoinstall" default is migrated in place if present.
    """
    templates_dir = os.path.join(collections_dir, "templates")
    # Maps an old autoinstall path to the uid of the Template record created for it,
    # so multiple items referencing the same path share a single Template record.
    path_to_uid: Dict[str, str] = {}

    def resolve_autoinstall(autoinstall: str, referenced_by: str) -> str:
        if autoinstall in ("", "<<inherit>>"):
            return autoinstall
        if autoinstall not in path_to_uid:
            template_file_path = os.path.join(autoinstall_templates_dir, autoinstall)
            if not os.path.isfile(template_file_path):
                logger.warning(
                    'autoinstall template "%s" referenced by "%s" does not '
                    "exist under autoinstall_templates_dir - dropping the "
                    "reference instead of losing the whole item.",
                    autoinstall,
                    referenced_by,
                )
                path_to_uid[autoinstall] = ""
            else:
                template_uid = uuid.uuid4().hex
                # Item names may only contain [a-zA-Z0-9_-.:] - legacy autoinstall
                # paths can contain "/" for subdirectories, so replace it with the
                # same ":" separator Cobbler already uses elsewhere (e.g. profile
                # names like "x86_64:some-distro:install").
                template_record = {
                    "uid": template_uid,
                    "name": autoinstall.replace("/", ":"),
                    "template_type": default_template_type,
                    "uri": {"schema": "file", "path": autoinstall},
                }
                os.makedirs(templates_dir, exist_ok=True)
                with open(
                    os.path.join(templates_dir, f"{template_uid}.json"),
                    "w",
                    encoding="UTF-8",
                ) as _f:
                    _f.write(json.dumps(template_record))
                path_to_uid[autoinstall] = template_uid
        return path_to_uid[autoinstall]

    for collection_type in ("profiles", "systems", "images"):
        for collection_file in glob.glob(
            os.path.join(collections_dir, collection_type, "*.json")
        ):
            with open(collection_file, encoding="UTF-8") as _f:
                data = json.loads(_f.read())

            autoinstall = data.get("autoinstall", "")
            new_autoinstall = resolve_autoinstall(
                autoinstall, data.get("name", collection_file)
            )
            if new_autoinstall == autoinstall:
                continue

            data["autoinstall"] = new_autoinstall
            with open(collection_file, "w", encoding="UTF-8") as _f:
                _f.write(json.dumps(data))

    if "autoinstall" in settings:
        settings["autoinstall"] = resolve_autoinstall(
            settings["autoinstall"], "settings.yaml default"
        )
