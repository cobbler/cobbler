"""
Migration from V3.3.3 to V3.4.0
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2022 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC

import configparser
import glob
import json
import os
import pathlib
from configparser import ConfigParser
from typing import Any, Dict

from schema import Optional, Schema, SchemaError  # type: ignore

from cobbler.settings.migrations import V3_3_5, helper

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
        Optional("autoinstall_snippets_dir"): str,
        Optional("autoinstall_templates_dir"): str,
        Optional("bind_chroot_path"): str,
        Optional("bind_zonefile_path"): str,
        Optional("bind_master"): str,
        Optional("boot_loader_conf_template_dir"): str,
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
        Optional("enable_ipxe"): bool,
        Optional("enable_menu"): bool,
        Optional("extra_settings_list"): [str],
        Optional("http_port"): int,
        Optional("iso_template_dir"): str,
        Optional("jinja2_includedir"): str,
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
        # TODO: Remove following line
        Optional("manage_dhcp"): bool,
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
        Optional("windows_template_dir"): str,
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
                Optional("uid"): {
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
                Optional("uid"): {
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
                Optional("uid"): {
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
            Optional("profile"): {
                Optional("uid"): {
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
                Optional("uid"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
            },
            Optional("system"): {
                Optional("uid"): {
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
                Optional("mac_address"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("ip_address"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("ipv6_address"): {
                    Optional("property"): str,
                    Optional("nonunique"): bool,
                    Optional("disabled"): bool,
                },
                Optional("dns_name"): {
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
    Checks that a given settings dict is valid according to the reference V3.4.0 schema ``schema``.

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
    Migration of the settings ``settings`` to version V3.4.0 settings

    :param settings: The settings dict to migrate
    :return: The migrated dict
    """

    if not V3_3_5.validate(settings):
        raise SchemaError("V3.3.5: Schema error while validating")

    # rename keys and update their value if needed
    include = settings.pop("include")
    include = settings.pop("mgmt_classes")
    include = settings.pop("mgmt_parameters")

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

    # Do mongodb.conf migration
    modules_config = "/etc/cobbler/modules.conf"
    modules_config_parser = ConfigParser()
    try:
        modules_config_parser.read(mongodb_config)
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

    # Drop defaults
    from cobbler.settings import Settings

    helper.key_drop_if_default(settings, Settings().to_dict())

    # Write settings to disk
    from cobbler.settings import update_settings_file

    update_settings_file(settings)

    for include_path in include:
        include_directory = pathlib.Path(include_path)
        if include_directory.is_dir() and include_directory.exists():
            include_directory.rmdir()

    # migrate stored cobbler collections
    migrate_cobbler_collections("/var/lib/cobbler/collections/")

    return normalize(settings)


def migrate_cobbler_collections(collections_dir: str) -> None:
    """
    Manipulate the main Cobbler stored collections and migrate deprecated settings
    to work with newer Cobbler versions.

    :param collections_dir: The directory of Cobbler where the collections files are.
    """
    helper.backup_dir(collections_dir)
    for collection_file in glob.glob(
        os.path.join(collections_dir, "**/*.json"), recursive=True
    ):
        data = None
        with open(collection_file, encoding="utf-8") as _f:
            data = json.loads(_f.read())

        # migrate interface.interface_type from emptry string to "NA"
        if "interfaces" in data:
            for iface in data["interfaces"]:
                if data["interfaces"][iface]["interface_type"] == "":
                    data["interfaces"][iface]["interface_type"] = "NA"

        # Remove fetchable_files from the items
        if "fetchable_files" in data:
            data.pop("fetchable_files", None)

        # Migrate boot_files to template_files
        if "boot_files" in data and "template_files" in data:
            data["template_files"] = {**data["template_files"], **data["boot_files"]}

        with open(collection_file, "w", encoding="utf-8") as _f:
            _f.write(json.dumps(data))
