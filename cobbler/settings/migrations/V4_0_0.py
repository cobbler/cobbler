"""
Migration from V3.3.3 to V4.0.0
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2022 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC

import configparser
import datetime
import glob
import json
import logging
import os
import pathlib
import shutil
import sqlite3
import tempfile
import uuid
from configparser import ConfigParser
from typing import TYPE_CHECKING, Any, Callable, Dict, List
from typing import Optional as TOptional
from typing import Tuple

from schema import Optional, Schema, SchemaError  # type: ignore

from cobbler.settings.migrations import V3_3_7, helper

if TYPE_CHECKING:
    from pymongo.database import Database
    from pymongo.mongo_client import MongoClient

logger = logging.getLogger()

# Filenames from the legacy "iso_template_dir" (/etc/cobbler/iso) that are known to
# correspond to a specific, well-known Template tag. Any other file present in that
# directory is migrated as a plain, untagged Template record.
ISO_TEMPLATE_TAGS = {
    "buildiso.template": "iso_buildiso",
    "grub_menuentry.template": "iso_grub_menuentry",
    "bootinfo.template": "iso_bootinfo",
    "isolinux_menuentry.template": "iso_isolinux_menuentry",
}

# Filenames from the legacy "boot_loader_conf_template_dir"
# (/etc/cobbler/boot_loader_conf) that are known to correspond to a specific,
# well-known Template tag. Any other file present in that directory is migrated as a
# plain, untagged Template record.
BOOT_LOADER_CONF_TEMPLATE_TAGS = {
    "bootcfg.template": "bootcfg",
    "grub.template": "grub",
    "grub_menu.template": "grub_menu",
    "grub_submenu.template": "grub_submenu",
    "ipxe.template": "ipxe",
    "ipxe_menu.template": "ipxe_menu",
    "ipxe_submenu.template": "ipxe_submenu",
    "pxe.template": "pxe",
    "pxe_menu.template": "pxe_menu",
    "pxe_submenu.template": "pxe_submenu",
}

# All collection types that can exist in a V3.3.7 install (i.e. before
# network_interfaces/templates/*_groups were introduced in V4.0.0).
LEGACY_COLLECTION_TYPES = ("distros", "profiles", "systems", "repos", "images", "menus")

# Collection types the migration pipeline may create records in, in addition to the
# legacy ones above.
NEW_COLLECTION_TYPES = ("network_interfaces", "templates")

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
        Optional("autoinstall_templates_allow_new_files"): bool,
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
        Optional("nsupdate_mgm_txt"): bool,
        Optional("nsupdate_tsig"): dict,
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
        Optional("xmlrpc_bind_address"): str,
        Optional("xmlrpc_host"): str,
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
            Optional("httpd"): {Optional("module"): str},
            # Valid values for "module": "process_management.service", "process_management.docker", or "auto"
            # (auto-detects Docker vs. systemd/supervisord based on whether cobblerd is running in a container).
            Optional("process_management"): {
                Optional("module"): str,
                Optional("docker_socket_path"): str,
                Optional("docker_service_labels"): dict,
            },
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
                Optional("system_uid"): {
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
                Optional("parent"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("members"): {
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
                Optional("parent"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("members"): {
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
                Optional("parent"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("members"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
            },
            Optional("template"): {
                Optional("name"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("tags"): {
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
        "httpd": {
            "module": modules_config_parser.get(
                "httpd", "module", fallback="managers.in_httpd"
            )
        },
        "process_management": {
            "module": "auto",
            "docker_socket_path": "/var/run/docker.sock",
            "docker_service_labels": {
                "dhcpd": "dhcp",
                "dhcpd4": "dhcp",
                "dhcpd6": "dhcp",
                "named": "dns",
                "dnsmasq": "dnsmasq",
            },
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

    # Migrate collection item data (distros/profiles/systems/etc.), plus the legacy
    # iso_template_dir/boot_loader_conf_template_dir/jinja2_includedir/
    # autoinstall_snippets_dir directories (all folded into the Template collection
    # in V4.0.0). Determines which single backend (file/sqlite/mongodb) actually
    # holds the data and migrates it - refuses to run if more than one appears
    # populated. Must run before key_drop_if_default()/update_settings_file() below,
    # since it mutates settings["autoinstall"] in place and that needs to reach the
    # settings.yaml that gets written to disk.
    determine_and_migrate_collections_data(
        settings,
        iso_template_dir,
        boot_loader_conf_template_dir,
        jinja2_includedir,
        autoinstall_snippets_dir,
        autoinstall_templates_dir,
        default_template_type,
    )

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
        interfaces = system_dict.pop("interfaces", {})
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


def _create_template_record(
    templates_dir: str,
    name: str,
    template_type: str,
    relative_path: str,
    tags: TOptional[List[str]] = None,
) -> None:
    """
    Write a new Template collection record to disk.

    :param templates_dir: The "templates" collection directory to write into.
    :param name: The name for the new Template record (must not contain "/").
    :param template_type: The template engine ("cheetah"/"jinja") for the new record.
    :param relative_path: The path of the template file, relative to autoinstall_templates_dir.
    :param tags: The tags to assign to the new record, if any.
    """
    template_uid = uuid.uuid4().hex
    template_record: Dict[str, Any] = {
        "uid": template_uid,
        "name": name,
        "template_type": template_type,
        "uri": {"schema": "file", "path": relative_path},
    }
    if tags:
        template_record["tags"] = tags
    os.makedirs(templates_dir, exist_ok=True)
    with open(
        os.path.join(templates_dir, f"{template_uid}.json"), "w", encoding="UTF-8"
    ) as _f:
        _f.write(json.dumps(template_record))


def migrate_cobbler_iso_and_bootloader_templates(
    collections_dir: str,
    iso_template_dir: str,
    boot_loader_conf_template_dir: str,
    autoinstall_templates_dir: str,
    default_template_type: str,
) -> None:
    """
    Create dedicated Template collection records for the legacy
    ``iso_template_dir``/``boot_loader_conf_template_dir`` directories, which V4.0.0
    replaced with Template records looked up by tag (e.g. ``iso_buildiso``,
    ``grub_menu``). Known legacy filenames are tagged with their well-known tag plus
    "active" (so they take effect over the shipped built-in default - a template with
    only the kind-tag and neither "active" nor "default" is never selected by any of
    the lookups in cobbler/actions/buildiso/__init__.py or cobbler/tftpgen.py).
    Unrecognized files are still migrated (content preserved) but left untagged.

    Files are physically copied into a subdirectory of ``autoinstall_templates_dir``,
    since that is the only directory Template's FILE-schema content resolves against.

    :param collections_dir: The directory of Cobbler where the collections files are.
    :param iso_template_dir: The legacy directory containing ISO build templates.
    :param boot_loader_conf_template_dir: The legacy directory containing boot-loader
                                           config generation templates.
    :param autoinstall_templates_dir: The directory Template file paths are relative to.
    :param default_template_type: The template engine for unrecognized/custom files.
    """
    templates_dir = os.path.join(collections_dir, "templates")
    for source_dir, subdir, known_tags in (
        (iso_template_dir, "iso", ISO_TEMPLATE_TAGS),
        (
            boot_loader_conf_template_dir,
            "boot_loader_conf",
            BOOT_LOADER_CONF_TEMPLATE_TAGS,
        ),
    ):
        if not os.path.isdir(source_dir):
            continue
        target_dir = os.path.join(autoinstall_templates_dir, subdir)
        os.makedirs(target_dir, exist_ok=True)
        for filename in sorted(os.listdir(source_dir)):
            source_file = os.path.join(source_dir, filename)
            if not os.path.isfile(source_file):
                continue
            shutil.copy2(source_file, os.path.join(target_dir, filename))
            relative_path = f"{subdir}/{filename}"
            tag = known_tags.get(filename)
            _create_template_record(
                templates_dir,
                name=relative_path.replace("/", ":"),
                # Legacy files are always Cheetah, regardless of what template
                # engine the current built-in default for the same tag uses.
                template_type="cheetah" if tag else default_template_type,
                relative_path=relative_path,
                tags=[tag, "active"] if tag else None,
            )


def migrate_cobbler_snippets_and_jinja_includes(
    collections_dir: str,
    jinja2_includedir: str,
    autoinstall_snippets_dir: str,
    autoinstall_templates_dir: str,
    default_template_type: str,
) -> None:
    """
    Create dedicated, name-addressable Template collection records for every file
    under the legacy ``jinja2_includedir``/``autoinstall_snippets_dir`` directories.
    V4.0.0 resolves both Jinja2 ``{% include "x" %}`` and Cheetah ``SNIPPET::x``
    directives via ``find_template(name="x")`` rather than a filesystem search path.

    Files are physically copied into a subdirectory of ``autoinstall_templates_dir``.
    Any ``SNIPPET::<old-path>``/``{% include "<old-path>" %}`` reference embedded in
    other already-migrated template content is intentionally NOT rewritten (that
    would mean parsing/rewriting arbitrary template syntax across two different
    template languages, too risky for this migration to attempt automatically) - a
    warning is logged listing every renamed path so an admin can update references
    manually.

    :param collections_dir: The directory of Cobbler where the collections files are.
    :param jinja2_includedir: The legacy directory Jinja2 templates could include from.
    :param autoinstall_snippets_dir: The legacy directory holding reusable autoinstall snippets.
    :param autoinstall_templates_dir: The directory Template file paths are relative to.
    :param default_template_type: The template engine to assign to the migrated records.
    """
    templates_dir = os.path.join(collections_dir, "templates")
    renamed: List[Tuple[str, str]] = []
    for source_dir, subdir in (
        (jinja2_includedir, "jinja2"),
        (autoinstall_snippets_dir, "snippets"),
    ):
        if not os.path.isdir(source_dir):
            continue
        target_dir = os.path.join(autoinstall_templates_dir, subdir)
        for root, _dirs, files in os.walk(source_dir):
            for filename in sorted(files):
                source_file = os.path.join(root, filename)
                relative_to_source = os.path.relpath(source_file, source_dir)
                relative_path = f"{subdir}/{relative_to_source}"
                target_file = os.path.join(target_dir, relative_to_source)
                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                shutil.copy2(source_file, target_file)
                new_name = relative_path.replace("/", ":").replace("\\", ":")
                _create_template_record(
                    templates_dir,
                    name=new_name,
                    template_type=default_template_type,
                    relative_path=relative_path.replace("\\", "/"),
                )
                renamed.append((relative_to_source, new_name))

    if renamed:
        logger.warning(
            "%d snippet/jinja2-include file(s) were migrated to named Template "
            'records. Any SNIPPET::<old-path> or {%% include "<old-path>" %%} '
            "reference to them inside OTHER templates must be updated manually to "
            "use the new name (old path -> new name): %s",
            len(renamed),
            ", ".join(f"{old} -> {new}" for old, new in renamed),
        )


def _count_file_collection_items(collections_dir: str) -> int:
    """
    Count how many item JSON files exist across all legacy (V3.3.7-era) collection
    types under ``collections_dir``.

    :param collections_dir: The directory of Cobbler where the collections files are.
    :return: The total number of item files found.
    """
    total = 0
    for collection_type in LEGACY_COLLECTION_TYPES:
        total += len(
            glob.glob(os.path.join(collections_dir, collection_type, "*.json"))
        )
    return total


def _count_sqlite_collection_items(db_path: str) -> int:
    """
    Count how many item rows exist across all legacy collection tables in a Cobbler
    SQLite database.

    :param db_path: The path to the "collections.db" SQLite database file.
    :return: The total number of item rows found, or 0 if the database doesn't exist.
    """
    if not os.path.isfile(db_path):
        return 0
    connection = sqlite3.connect(db_path)
    try:
        total = 0
        for collection_type in LEGACY_COLLECTION_TYPES:
            try:
                cursor = connection.execute(f"SELECT COUNT(*) FROM {collection_type}")
                total += cursor.fetchone()[0]
            except sqlite3.OperationalError:
                # Table doesn't exist yet - no items of this type were ever stored.
                continue
        return total
    finally:
        connection.close()


def _count_mongo_collection_items(host: str, port: int) -> Tuple[bool, int]:
    """
    Attempt to connect to a MongoDB server and count how many documents exist across
    all legacy collections in the "cobbler" database.

    :param host: The MongoDB host to connect to.
    :param port: The MongoDB port to connect to.
    :return: A tuple of (whether the server was reachable, the total document count).
    """
    try:
        # pylint: disable-next=import-outside-toplevel
        import pymongo
    except ImportError:
        return False, 0

    try:
        client: "MongoClient[Dict[str, Any]]" = pymongo.MongoClient(  # type: ignore
            host, port, serverSelectionTimeoutMS=2000
        )
        client.admin.command("ping")
    except Exception:  # pylint: disable=broad-except
        return False, 0

    database = client["cobbler"]
    total = sum(
        database[collection_type].count_documents({})
        for collection_type in LEGACY_COLLECTION_TYPES
    )
    return True, total


class AmbiguousDataSourceError(RuntimeError):
    """
    Raised when more than one of the file/sqlite/mongodb data sources appears to
    hold real Cobbler collection data at once, making it unsafe to guess which one
    is authoritative.
    """


def _run_collection_pipeline(
    work_dir: str,
    iso_template_dir: str,
    boot_loader_conf_template_dir: str,
    jinja2_includedir: str,
    autoinstall_snippets_dir: str,
    autoinstall_templates_dir: str,
    default_template_type: str,
    settings: Dict[str, Any],
) -> None:
    """
    Run the full item-content migration pipeline against ``work_dir``, which must
    already contain the legacy (V3.3.7-shaped) collection JSON files. Shared by the
    file/sqlite/mongodb backends so the same, already-verified transform logic is
    reused unchanged regardless of which storage backend the data came from.

    :param work_dir: A directory shaped like a Cobbler "collections" directory.
    """
    for extra_dir in NEW_COLLECTION_TYPES:
        os.makedirs(os.path.join(work_dir, extra_dir), exist_ok=True)

    migrate_cobbler_uid_references(work_dir)
    migrate_cobbler_item_options(work_dir)
    migrate_cobbler_collections(work_dir)
    migrate_cobbler_autoinstall_templates(
        work_dir, autoinstall_templates_dir, default_template_type, settings
    )
    migrate_cobbler_iso_and_bootloader_templates(
        work_dir,
        iso_template_dir,
        boot_loader_conf_template_dir,
        autoinstall_templates_dir,
        default_template_type,
    )
    migrate_cobbler_snippets_and_jinja_includes(
        work_dir,
        jinja2_includedir,
        autoinstall_snippets_dir,
        autoinstall_templates_dir,
        default_template_type,
    )
    migrate_cobbler_json_files(pathlib.Path(work_dir))
    migrate_cobbler_network_interfaces(pathlib.Path(work_dir))


def _dump_dir_from_reader(
    work_dir: str,
    collection_types: Tuple[str, ...],
    read_items: Callable[[str], List[Dict[str, Any]]],
) -> None:
    """
    Populate ``work_dir`` with one ``<uid>.json`` file per item, for each collection
    type, using ``read_items(collection_type)`` as the source.
    """
    for collection_type in collection_types:
        collection_path = os.path.join(work_dir, collection_type)
        os.makedirs(collection_path, exist_ok=True)
        for item in read_items(collection_type):
            with open(
                os.path.join(collection_path, f"{item['uid']}.json"),
                "w",
                encoding="UTF-8",
            ) as _f:
                _f.write(json.dumps(item))


def _load_dir_into_writer(
    work_dir: str,
    collection_types: Tuple[str, ...],
    write_items: Callable[[str, List[Dict[str, Any]]], None],
) -> None:
    """
    Read every ``*.json`` file for each collection type out of ``work_dir`` (after
    the pipeline has transformed them) and hand them to ``write_items(collection_type,
    items)`` to persist back into the real backend.
    """
    for collection_type in collection_types:
        collection_path = os.path.join(work_dir, collection_type)
        items: List[Dict[str, Any]] = []
        for item_file in sorted(glob.glob(os.path.join(collection_path, "*.json"))):
            with open(item_file, encoding="UTF-8") as _f:
                items.append(json.loads(_f.read()))
        write_items(collection_type, items)


def _migrate_file_backend(
    collections_dir: str,
    iso_template_dir: str,
    boot_loader_conf_template_dir: str,
    jinja2_includedir: str,
    autoinstall_snippets_dir: str,
    autoinstall_templates_dir: str,
    default_template_type: str,
    settings: Dict[str, Any],
) -> None:
    """
    Migrate a file-serializer-backed install: run the pipeline directly, in place,
    against the real collections directory (after backing it up).
    """
    helper.backup_dir(collections_dir)
    _run_collection_pipeline(
        collections_dir,
        iso_template_dir,
        boot_loader_conf_template_dir,
        jinja2_includedir,
        autoinstall_snippets_dir,
        autoinstall_templates_dir,
        default_template_type,
        settings,
    )


def _migrate_sqlite_backend(
    db_path: str,
    iso_template_dir: str,
    boot_loader_conf_template_dir: str,
    jinja2_includedir: str,
    autoinstall_snippets_dir: str,
    autoinstall_templates_dir: str,
    default_template_type: str,
    settings: Dict[str, Any],
) -> None:
    """
    Migrate a SQLite-serializer-backed install: back up the database file, dump every
    table's items into a throwaway directory, run the same pipeline used for the file
    backend against it, then load the transformed items back into the database.
    """
    # The backup must NOT be placed inside the collections directory itself - that
    # directory is also scanned by the file-backend migration functions (e.g.
    # migrate_cobbler_json_files() iterates every entry expecting it to be a
    # collection-type subdirectory), so a stray backup file left alongside it would
    # break them.
    timestamp = datetime.datetime.now().isoformat()
    collections_dir = os.path.dirname(db_path)
    backup_path = os.path.join(
        os.path.dirname(collections_dir), f"collections.db.backup.{timestamp}"
    )
    shutil.copy2(db_path, backup_path)

    connection = sqlite3.connect(db_path)
    try:

        def read_items(collection_type: str) -> List[Dict[str, Any]]:
            try:
                cursor = connection.execute(f"SELECT item FROM {collection_type}")
            except sqlite3.OperationalError:
                return []
            return [json.loads(row[0]) for row in cursor.fetchall()]

        def write_items(collection_type: str, items: List[Dict[str, Any]]) -> None:
            connection.execute(
                f"CREATE TABLE IF NOT EXISTS {collection_type}"
                "(uid text primary key, item text)"
            )
            connection.execute(f"DELETE FROM {collection_type}")
            for item in items:
                connection.execute(
                    f"INSERT INTO {collection_type}(uid, item) VALUES (?, ?)",
                    (item["uid"], json.dumps(item)),
                )
            connection.commit()

        with tempfile.TemporaryDirectory() as work_dir:
            _dump_dir_from_reader(work_dir, LEGACY_COLLECTION_TYPES, read_items)
            _run_collection_pipeline(
                work_dir,
                iso_template_dir,
                boot_loader_conf_template_dir,
                jinja2_includedir,
                autoinstall_snippets_dir,
                autoinstall_templates_dir,
                default_template_type,
                settings,
            )
            _load_dir_into_writer(
                work_dir,
                LEGACY_COLLECTION_TYPES + NEW_COLLECTION_TYPES,
                write_items,
            )
    finally:
        connection.close()


def _migrate_mongodb_backend(
    host: str,
    port: int,
    iso_template_dir: str,
    boot_loader_conf_template_dir: str,
    jinja2_includedir: str,
    autoinstall_snippets_dir: str,
    autoinstall_templates_dir: str,
    default_template_type: str,
    settings: Dict[str, Any],
) -> None:
    """
    Migrate a MongoDB-serializer-backed install: connect directly via pymongo (not
    through MongoDBSerializer, to keep this migration's own error handling), back up
    every collection to a local JSON dump, dump every collection's items into a
    throwaway directory, run the same pipeline used for the file backend against it,
    then load the transformed items back into MongoDB.

    :raises RuntimeError: If pymongo isn't available or the server can't be reached.
    """
    try:
        # pylint: disable-next=import-outside-toplevel
        import pymongo
    except ImportError as import_error:
        raise RuntimeError(
            "Configured serializer is serializers.mongodb, but the pymongo package "
            "is not installed - cannot migrate MongoDB-backed collections."
        ) from import_error

    try:
        client: "MongoClient[Dict[str, Any]]" = pymongo.MongoClient(  # type: ignore
            host, port, serverSelectionTimeoutMS=5000
        )
        client.admin.command("ping")
    except Exception as connection_error:  # pylint: disable=broad-except
        raise RuntimeError(
            f"Configured serializer is serializers.mongodb, but no MongoDB server "
            f"could be reached at {host}:{port} - cannot migrate MongoDB-backed "
            "collections."
        ) from connection_error

    database: "Database[Dict[str, Any]]" = client["cobbler"]

    def read_items(collection_type: str) -> List[Dict[str, Any]]:
        return list(database[collection_type].find({}, {"_id": 0}))

    def write_items(collection_type: str, items: List[Dict[str, Any]]) -> None:
        database[collection_type].delete_many({})
        if items:
            database[collection_type].insert_many(items)

    with tempfile.TemporaryDirectory() as work_dir:
        _dump_dir_from_reader(work_dir, LEGACY_COLLECTION_TYPES, read_items)

        timestamp = datetime.datetime.now().isoformat()
        backup_dir = os.path.join(
            tempfile.gettempdir(), f"mongodb-collections.backup.{timestamp}"
        )
        shutil.copytree(work_dir, backup_dir)
        logger.info("Backed up MongoDB collections to %s before migrating.", backup_dir)

        _run_collection_pipeline(
            work_dir,
            iso_template_dir,
            boot_loader_conf_template_dir,
            jinja2_includedir,
            autoinstall_snippets_dir,
            autoinstall_templates_dir,
            default_template_type,
            settings,
        )
        _load_dir_into_writer(
            work_dir, LEGACY_COLLECTION_TYPES + NEW_COLLECTION_TYPES, write_items
        )


def determine_and_migrate_collections_data(
    settings: Dict[str, Any],
    iso_template_dir: str,
    boot_loader_conf_template_dir: str,
    jinja2_includedir: str,
    autoinstall_snippets_dir: str,
    autoinstall_templates_dir: str,
    default_template_type: str,
) -> None:
    """
    Determine which single backend (file/sqlite/mongodb) actually holds the install's
    collection data, and migrate it. Refuses to run if more than one backend shows
    real data present, since it would be unsafe to guess which one is authoritative.
    If the declared serializer is serializers.mongodb, a working connection is
    required - this is a hard requirement, not a best-effort skip.

    :param settings: The settings dict being migrated (already contains "modules").
    :raises RuntimeError: If multiple data sources are present, or if the declared
                           MongoDB serializer can't actually be reached.
    """
    collections_dir = "/var/lib/cobbler/collections/"
    db_path = os.path.join(collections_dir, "collections.db")
    declared_serializer = (
        settings.get("modules", {}).get("serializers", {}).get("module", "")
    )
    mongodb_settings = settings.get("mongodb", {})
    mongo_host = mongodb_settings.get("host", "localhost")
    mongo_port = mongodb_settings.get("port", 27017)

    file_count = _count_file_collection_items(collections_dir)
    sqlite_count = _count_sqlite_collection_items(db_path)
    mongo_reachable, mongo_count = _count_mongo_collection_items(mongo_host, mongo_port)

    if declared_serializer == "serializers.mongodb" and not mongo_reachable:
        raise RuntimeError(
            "Configured serializer is serializers.mongodb, but no MongoDB server "
            f"could be reached at {mongo_host}:{mongo_port} - refusing to migrate."
        )

    present = [
        name
        for name, count in (
            ("file", file_count),
            ("sqlite", sqlite_count),
            ("mongodb", mongo_count if mongo_reachable else 0),
        )
        if count > 0
    ]

    if len(present) > 1:
        raise AmbiguousDataSourceError(
            f"Multiple data sources detected ({', '.join(present)}) - refusing to "
            "migrate. Exactly one of file/sqlite/mongodb collection storage may be "
            "present; remove stale leftover data from unused backends first."
        )

    common_args = (
        iso_template_dir,
        boot_loader_conf_template_dir,
        jinja2_includedir,
        autoinstall_snippets_dir,
        autoinstall_templates_dir,
        default_template_type,
        settings,
    )

    if not present:
        return
    if present[0] == "file":
        _migrate_file_backend(collections_dir, *common_args)
    elif present[0] == "sqlite":
        _migrate_sqlite_backend(db_path, *common_args)
    else:
        _migrate_mongodb_backend(mongo_host, mongo_port, *common_args)
