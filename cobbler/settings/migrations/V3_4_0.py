"""
Migration from V3.3.1 to V3.3.2
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2022 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC
import configparser
import pathlib
from configparser import ConfigParser

from schema import Optional, Schema, SchemaError

from cobbler.settings.migrations import helper
from cobbler.settings.migrations import V3_3_3

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
        Optional("enable_ipxe"): bool,
        Optional("enable_menu"): bool,
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
        Optional("mgmt_classes"): [str],
        Optional("mgmt_parameters"): dict,
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
    },
    ignore_extra_keys=False,
)


def validate(settings: dict) -> bool:
    """
    Checks that a given settings dict is valid according to the reference V3.4.0 schema ``schema``.

    :param settings: The settings dict to validate.
    :return: True if valid settings dict otherwise False.
    """
    try:
        schema.validate(settings)
    except SchemaError:
        return False
    return True


def normalize(settings: dict) -> dict:
    """
    If data in ``settings`` is valid the validated data is returned.

    :param settings: The settings dict to validate.
    :return: The validated dict.
    """

    return schema.validate(settings)


def migrate(settings: dict) -> dict:
    """
    Migration of the settings ``settings`` to version V3.4.0 settings

    :param settings: The settings dict to migrate
    :return: The migrated dict
    """

    if not V3_3_3.validate(settings):
        raise SchemaError("V3.3.3: Schema error while validating")

    # rename keys and update their value if needed
    include = settings.pop("include")

    # Do mongodb.conf migration
    mongodb_config = "/etc/cobbler/mongodb.conf"
    cp = ConfigParser()
    try:
        cp.read(mongodb_config)
    except configparser.Error as cp_error:
        raise configparser.Error(
            "Could not read Cobbler MongoDB config file!"
        ) from cp_error
    settings["mongodb"] = {
        "host": cp.get("connection", "host", fallback="localhost"),
        "port": cp.getint("connection", "port", fallback=27017),
    }
    pathlib.Path(mongodb_config).unlink(missing_ok=True)

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

    return normalize(settings)
