"""
Migration from V3.2.1 to V3.3.0
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC


from schema import Optional, Schema, SchemaError

from cobbler.settings.migrations import helper

schema = Schema({
    "auto_migrate_settings": bool,
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
    "bind_zonefile_path": str,
    "bind_master": str,
    "boot_loader_conf_template_dir": str,
    Optional("bootloaders_dir", default="/var/lib/cobbler/loaders"): str,
    Optional("bootloaders_formats", default={
        'aarch64': {'binary_name': 'grubaa64.efi'},
        'arm': {'binary_name': 'bootarm.efi'},
        'arm64-efi': {'binary_name': 'grubaa64.efi', 'extra_modules': ['efinet']},
        'i386': {'binary_name': 'bootia32.efi'},
        'i386-pc-pxe': {'binary_name': 'grub.0', 'mod_dir': 'i386-pc',
                        'extra_modules': ['chain', 'pxe', 'biosdisk']},
        'i686': {'binary_name': 'bootia32.efi'},
        'IA64': {'binary_name': 'bootia64.efi'},
        'powerpc-ieee1275': {'binary_name': 'grub.ppc64le', 'extra_modules': ['net', 'ofnet']},
        'x86_64-efi': {'binary_name': 'grubx86.efi', 'extra_modules': ['chain', 'efinet']}}
             ): dict,
    Optional("bootloaders_modules", default=[
        'btrfs', 'ext2', 'xfs', 'jfs', 'reiserfs', 'all_video', 'boot',
        'cat', 'configfile', 'echo', 'fat', 'font', 'gfxmenu', 'gfxterm',
        'gzio', 'halt', 'iso9660', 'jpeg', 'linux', 'loadenv', 'minicmd',
        'normal', 'part_apple', 'part_gpt', 'part_msdos', 'password_pbkdf2',
        'png', 'reboot', 'search', 'search_fs_file', 'search_fs_uuid',
        'search_label', 'sleep', 'test', 'true', 'video', 'mdraid09',
        'mdraid1x', 'lvm', 'serial', 'regexp', 'tr', 'tftp', 'http', 'luks',
        'gcry_rijndael', 'gcry_sha1', 'gcry_sha256'
    ]): list,
    Optional("syslinux_dir", default="/usr/share/syslinux"): str,
    Optional("grub2_mod_dir", default="/usr/share/grub"): str,
    Optional("grubconfig_dir", default="/var/lib/cobbler/grub_config"): str,
    "build_reporting_enabled": bool,
    "build_reporting_email": [str],
    "build_reporting_ignorelist": [str],
    "build_reporting_sender": str,
    "build_reporting_smtp_server": str,
    "build_reporting_subject": str,
    Optional("buildisodir", default="/var/cache/cobbler/buildiso"): str,
    "cheetah_import_whitelist": [str],
    "client_use_https": bool,
    "client_use_localhost": bool,
    Optional("cobbler_master", default=""): str,
    Optional("convert_server_to_ip", default=False): bool,
    "createrepo_flags": str,
    "autoinstall": str,
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
    "enable_ipxe": bool,
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
    # TODO: Remove following line
    "manage_dhcp": bool,
    "manage_dhcp_v4": bool,
    "manage_dhcp_v6": bool,
    "manage_dns": bool,
    "manage_forward_zones": [str],
    "manage_reverse_zones": [str],
    Optional("manage_genders", False): bool,
    "manage_rsync": bool,
    "manage_tftpd": bool,
    "mgmt_classes": [str],
    # TODO: Validate Subdict
    "mgmt_parameters": dict,
    "next_server_v4": str,
    "next_server_v6": str,
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
    Optional("windows_enabled", default=False): bool,
    Optional("windows_template_dir", default="/etc/cobbler/windows"): str,
    Optional("samba_distro_share", default="DISTRO"): str,
}, ignore_extra_keys=False)


def validate(settings: dict) -> bool:
    """
    Checks that a given settings dict is valid according to the reference V3.3.0 schema ``schema``.

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
    Migration of the settings ``settings`` to version V3.3.0 settings

    :param settings: The settings dict to migrate
    :return: The migrated dict
    """

    # migrate gpxe -> ipxe
    if "enable_gpxe" in settings:
        gpxe = helper.key_get("enable_gpxe", settings)
        helper.key_rename(gpxe, "enable_ipxe", settings)

    # rename keys and update their value
    old_setting = helper.Setting("default_autoinstall", "/var/lib/cobbler/autoinstall_templates/default.ks")
    new_setting = helper.Setting("autoinstall", "default.ks")
    helper.key_rename(old_setting, "autoinstall", settings)
    helper.key_set_value(new_setting, settings)

    old_setting = helper.Setting("next_server", "127.0.0.1")
    new_setting = helper.Setting("next_server_v4", "127.0.0.1")
    helper.key_rename(old_setting, "next_server_v4", settings)
    helper.key_set_value(new_setting, settings)

    # add missing keys
    # name - value pairs
    missing_keys = {'auto_migrate_settings': True,
                    'bind_zonefile_path': "@@bind_zonefiles@@",
                    'bootloaders_formats': {
                        "aarch64": {"binary_name": "grubaa64.efi"},
                        "arm": {"binary_name": "bootarm.efi"},
                        "arm64-efi": {"binary_name": "grubaa64.efi", "extra_modules": ["efinet"]},
                        "i386": {"binary_name": "bootia32.efi"},
                        "i386-pc-pxe": {
                            "binary_name": "grub.0",
                            "mod_dir": "i386-pc",
                            "extra_modules": ["chain", "pxe", "biosdisk"]},
                        "i686": {"binary_name": "bootia32.efi"},
                        "IA64": {"binary_name": "bootia64.efi"},
                        "powerpc-ieee1275": {"binary_name": "grub.ppc64le", "extra_modules": ["net", "ofnet"], },
                        "x86_64-efi": {"binary_name": "grubx86.efi", "extra_modules": ["chain", "efinet"]}
                    },
                    'bootloaders_modules': ["btrfs", "ext2", "xfs", "jfs", "reiserfs",
                                            "all_video", "boot", "cat", "configfile", "echo", "fat", "font", "gfxmenu",
                                            "gfxterm", "gzio", "halt", "iso9660", "jpeg", "linux", "loadenv", "minicmd",
                                            "normal", "part_apple", "part_gpt", "part_msdos", "password_pbkdf2", "png",
                                            "reboot", "search", "search_fs_file", "search_fs_uuid", "search_label",
                                            "sleep", "test", "true", "video", "mdraid09", "mdraid1x", "lvm", "serial",
                                            "regexp", "tr", "tftp", "http", "luks", "gcry_rijndael", "gcry_sha1",
                                            "gcry_sha256"],
                    'grub2_mod_dir': "/usr/share/grub2",
                    'manage_dhcp_v4': False,
                    'manage_dhcp_v6': False,
                    'next_server_v6': "::1",
                    'syslinux_dir': "/usr/share/syslinux"}
    for (key, value) in missing_keys.items():
        new_setting = helper.Setting(key, value)
        helper.key_add(new_setting, settings)

    # delete removed keys
    helper.key_delete("cache_enabled", settings)

    if not validate(settings):
        raise SchemaError("V3.3.0: Schema error while validating")
    return normalize(settings)
