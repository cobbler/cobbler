"""
Migration from V3.2.0 to V3.2.1
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC

import os

from schema import Optional, Schema, SchemaError

from cobbler import utils

schema = Schema({
    Optional("auto_migrate_settings", default=True): bool,
    "allow_duplicate_hostnames": bool,
    "allow_duplicate_ips": bool,
    "allow_duplicate_macs": bool,
    "allow_dynamic_settings": bool,
    "always_write_dhcp_entries": bool,
    "anamon_enabled": bool,
    "auth_token_expiration": int,
    "authn_pam_service": str,
    "autoinstall_snippets_dir": str,
    "autoinstall_templates_dir": str,
    "bind_chroot_path": str,
    "bind_master": str,
    "boot_loader_conf_template_dir": str,
    Optional("bootloaders_dir", default="/var/lib/cobbler/loaders"): str,
    Optional("grubconfig_dir", default="/var/lib/cobbler/grub_config"): str,
    "build_reporting_enabled": bool,
    "build_reporting_email": [str],
    "build_reporting_ignorelist": [str],
    "build_reporting_sender": str,
    "build_reporting_smtp_server": str,
    "build_reporting_subject": str,
    Optional("buildisodir", default="/var/cache/cobbler/buildiso"): str,
    "cache_enabled": bool,
    "cheetah_import_whitelist": [str],
    "client_use_https": bool,
    "client_use_localhost": bool,
    Optional("cobbler_master", default=""): str,
    Optional("convert_server_to_ip", default=False): bool,
    "createrepo_flags": str,
    "default_autoinstall": str,
    "default_name_servers": [str],
    "default_name_servers_search": [str],
    "default_ownership": [str],
    "default_password_crypted": str,
    "default_template_type": str,
    "default_virt_bridge": str,
    Optional("default_virt_disk_driver", default="raw"): str,
    "default_virt_file_size": int,
    "default_virt_ram": int,
    "default_virt_type": str,
    "enable_gpxe": bool,
    "enable_menu": bool,
    "http_port": int,
    "include": [str],
    Optional("iso_template_dir", default="/etc/cobbler/iso"): str,
    Optional("jinja2_includedir", default="/var/lib/cobbler/jinja2"): str,
    "kernel_options": dict,
    "ldap_anonymous_bind": bool,
    "ldap_base_dn": str,
    "ldap_port": int,
    "ldap_search_bind_dn": str,
    "ldap_search_passwd": str,
    "ldap_search_prefix": str,
    "ldap_server": str,
    "ldap_tls": bool,
    "ldap_tls_cacertfile": str,
    "ldap_tls_certfile": str,
    "ldap_tls_keyfile": str,
    Optional("bind_manage_ipmi", default=False): bool,
    "manage_dhcp": bool,
    "manage_dns": bool,
    "manage_forward_zones": [str],
    "manage_reverse_zones": [str],
    Optional("manage_genders", False): bool,
    "manage_rsync": bool,
    "manage_tftpd": bool,
    "mgmt_classes": [str],
    # TODO: Validate Subdict
    "mgmt_parameters": dict,
    "next_server": str,
    Optional("nsupdate_enabled", False): bool,
    Optional("nsupdate_log", default="/var/log/cobbler/nsupdate.log"): str,
    Optional("nsupdate_tsig_algorithm", default="hmac-sha512"): str,
    Optional("nsupdate_tsig_key", default=[]): [str],
    "power_management_default_type": str,
    "proxy_url_ext": str,
    "proxy_url_int": str,
    "puppet_auto_setup": bool,
    Optional("puppet_parameterized_classes", default=True): bool,
    Optional("puppet_server", default="puppet"): str,
    Optional("puppet_version", default=2): int,
    "puppetca_path": str,
    "pxe_just_once": bool,
    "nopxe_with_triggers": bool,
    "redhat_management_permissive": bool,
    "redhat_management_server": str,
    "redhat_management_key": str,
    "register_new_installs": bool,
    "remove_old_puppet_certs_automatically": bool,
    "replicate_repo_rsync_options": str,
    "replicate_rsync_options": str,
    "reposync_flags": str,
    "reposync_rsync_flags": str,
    "restart_dhcp": bool,
    "restart_dns": bool,
    "run_install_triggers": bool,
    "scm_track_enabled": bool,
    "scm_track_mode": str,
    "scm_track_author": str,
    "scm_push_script": str,
    "serializer_pretty_json": bool,
    "server": str,
    "sign_puppet_certs_automatically": bool,
    Optional("signature_path", default="/var/lib/cobbler/distro_signatures.json"): str,
    Optional("signature_url", default="https://cobbler.github.io/signatures/3.0.x/latest.json"): str,
    "tftpboot_location": str,
    "virt_auto_boot": bool,
    "webdir": str,
    "webdir_whitelist": [str],
    "xmlrpc_port": int,
    "yum_distro_priority": int,
    "yum_post_install_mirror": bool,
    "yumdownloader_flags": str,
}, ignore_extra_keys=False)


def validate(settings: dict) -> bool:
    """
    Checks that a given settings dict is valid according to the reference schema ``schema``.

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
    Migration of the settings ``settings`` to the V3.2.1 settings

    :param settings: The settings dict to migrate
    :return: The migrated dict
    """
    # int bool to real bool conversion
    bool_values = ["allow_duplicate_hostnames", "allow_duplicate_ips", "allow_duplicate_macs",
                   "allow_duplicate_macs", "allow_dynamic_settings", "always_write_dhcp_entries",
                   "anamon_enabled", "bind_manage_ipmi", "build_reporting_enabled", "cache_enabled","client_use_https",
                   "client_use_localhost", "convert_server_to_ip", "enable_gpxe", "enable_menu",
                   "ldap_anonymous_bind", "ldap_tls", "manage_dhcp", "manage_dns", "manage_genders",
                   "manage_rsync", "manage_tftp", "manage_tftpd", "nopxe_with_triggers",
                   "nsupdate_enabled", "puppet_auto_setup", "puppet_parameterized_classes",
                   "pxe_just_once", "redhat_management_permissive", "register_new_installs",
                   "remove_old_puppet_certs_automatically", "restart_dhcp", "restart_dns",
                   "run_install_triggers", "scm_track_enabled", "serializer_pretty_json",
                   "sign_puppet_certs_automatically", "virt_auto_boot", "yum_post_install_mirror"]
    for key in bool_values:
        if key in settings:
            settings[key] = utils.input_boolean(settings[key])
    mgmt_parameters = "mgmt_parameters"
    if mgmt_parameters in settings and "from_cobbler" in settings[mgmt_parameters]:
        settings[mgmt_parameters]["from_cobbler"] = utils.input_boolean(
            settings[mgmt_parameters]["from_cobbler"]
        )

    # rename old settings filename
    filename = "/etc/cobbler/settings"
    if os.path.exists(filename):
        os.rename(filename, filename + ".yaml")
        filename += ".yaml"

    if not validate(settings):
        raise SchemaError("V3.2.1: Schema error while validating")
    return normalize(settings)
