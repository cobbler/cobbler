"""
Migration from V2.x.x to V2.8.5
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC


from schema import Optional, Schema, SchemaError

schema = Schema({
    Optional("auto_migrate_settings", default=True): int,
    "allow_duplicate_hostnames": int,
    "allow_duplicate_ips": int,
    "allow_duplicate_macs": int,
    "allow_dynamic_settings": int,
    "always_write_dhcp_entries": int,
    "anamon_enabled": int,
    "authn_pam_service": str,
    "auth_token_expiration": int,
    "bind_chroot_path": str,
    "bind_manage_ipmi": int,
    "bind_master": str,
    Optional("buildisodir", default="/var/cache/cobbler/buildiso"): str,
    "build_reporting_enabled": int,
    "build_reporting_email": list,
    "build_reporting_ignorelist": list,
    "build_reporting_sender": str,
    "build_reporting_smtp_server": str,
    "build_reporting_subject": str,
    Optional("build_reporting_to_address", default=""): str,
    "cheetah_import_whitelist": list,
    "client_use_https": int,
    "client_use_localhost": int,
    Optional("cobbler_master", default=""): str,
    "consoles": str,
    "createrepo_flags": str,
    Optional("default_deployment_method", default=""): str,
    "default_kickstart": str,
    "default_name_servers": list,
    Optional("default_name_servers_search", default=[]): list,
    "default_ownership": list,
    "default_password_crypted": str,
    "default_template_type": str,
    "default_virt_bridge": str,
    Optional("default_virt_disk_driver", default="raw"): str,
    "default_virt_file_size": int,
    "default_virt_ram": int,
    "default_virt_type": str,
    "enable_gpxe": int,
    "enable_menu": int,
    "func_auto_setup": int,
    "func_master": str,
    "http_port": int,
    Optional("isc_set_host_name", default=0): int,
    Optional("iso_template_dir", default="/etc/cobbler/iso"): str,
    Optional("kerberos_realm", default="EXAMPLE.COM"): str,
    "kernel_options": dict,
    "kernel_options_s390x": dict,
    "ldap_anonymous_bind": int,
    "ldap_base_dn": str,
    Optional("ldap_management_default_type", default="authconfig"): str,
    "ldap_port": int,
    "ldap_search_bind_dn": str,
    "ldap_search_passwd": str,
    "ldap_search_prefix": str,
    "ldap_server": str,
    "ldap_tls": int,
    "ldap_tls_cacertfile": str,
    "ldap_tls_certfile": str,
    "ldap_tls_keyfile": str,
    "manage_dhcp": int,
    "manage_dns": int,
    "manage_forward_zones": list,
    "manage_reverse_zones": list,
    "manage_genders": int,
    "manage_rsync": int,
    Optional("manage_tftp", default=1): int,
    "manage_tftpd": int,
    "mgmt_classes": list,
    "mgmt_parameters": dict,
    "next_server": str,
    "power_management_default_type": str,
    "power_template_dir": str,
    "proxy_url_ext": str,
    "proxy_url_int": str,
    "puppet_auto_setup": int,
    "puppetca_path": str,
    Optional("puppet_parameterized_classes", default=1): int,
    Optional("puppet_server", default="puppet"): str,
    Optional("puppet_version", default=2): int,
    "pxe_just_once": int,
    "pxe_template_dir": str,
    "redhat_management_permissive": int,
    "redhat_management_server": str,
    "redhat_management_key": str,
    "redhat_management_type": str,
    "register_new_installs": int,
    "remove_old_puppet_certs_automatically": int,
    "replicate_repo_rsync_options": str,
    "replicate_rsync_options": str,
    "reposync_flags": str,
    "restart_dhcp": int,
    "restart_dns": int,
    "run_install_triggers": int,
    "scm_track_enabled": int,
    "scm_track_mode": str,
    "serializer_pretty_json": int,
    "server": str,
    Optional("signature_path", default="/var/lib/cobbler/distro_signatures.json"): str,
    Optional("signature_url", default="https://cobbler.github.io/signatures/2.8.x/latest.json"): str,
    "sign_puppet_certs_automatically": int,
    "snippetsdir": str,
    "template_remote_kickstarts": int,
    "virt_auto_boot": int,
    "webdir": str,
    "xmlrpc_port": int,
    "yum_distro_priority": int,
    "yum_post_install_mirror": int,
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
    Migration of the settings ``settings`` to the V2.8.5 settings

    :param settings: The settings dict to migrate
    :return: The migrated dict
    """
    if not validate(settings):
        raise SchemaError("V2.8.5: Schema error while validating")
    return normalize(settings)
