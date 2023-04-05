"""
Migration from V2.8.5 to V3.0.0
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC
import glob
import json
import os
import shutil
from typing import Any, Dict, List

from schema import Optional, Or, Schema, SchemaError  # type: ignore

from cobbler.settings.migrations import V2_8_5, helper

schema = Schema(
    {
        Optional("auto_migrate_settings", default=True): bool,
        "allow_duplicate_hostnames": int,
        "allow_duplicate_ips": int,
        "allow_duplicate_macs": int,
        "allow_dynamic_settings": int,
        "always_write_dhcp_entries": int,
        "anamon_enabled": int,
        "authn_pam_service": str,
        "auth_token_expiration": int,
        "autoinstall_snippets_dir": str,
        "autoinstall_templates_dir": str,
        "bind_chroot_path": str,
        Optional("bind_manage_ipmi", default=0): int,
        "bind_master": str,
        "boot_loader_conf_template_dir": str,
        Optional("bootloaders_dir", default="/var/lib/cobbler/loaders"): str,
        Optional("buildisodir", default="/var/cache/cobbler/buildiso"): str,
        "build_reporting_enabled": int,
        "build_reporting_email": list,
        # in yaml this is a list but should be a str
        "build_reporting_ignorelist": list,
        "build_reporting_sender": str,
        "build_reporting_smtp_server": str,
        "build_reporting_subject": str,
        "cheetah_import_whitelist": list,
        "client_use_https": int,
        "client_use_localhost": int,
        Optional("cobbler_master", default=""): str,
        "createrepo_flags": str,
        "default_autoinstall": str,
        "default_name_servers": list,
        "default_name_servers_search": list,
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
        Optional("grubconfig_dir", default="/var/lib/cobbler/grub_config"): str,
        "http_port": int,
        "include": list,
        Optional("iso_template_dir", default="/etc/cobbler/iso"): str,
        "kernel_options": dict,
        "ldap_anonymous_bind": int,
        "ldap_base_dn": str,
        "ldap_port": int,
        "ldap_search_bind_dn": str,
        "ldap_search_passwd": str,
        "ldap_search_prefix": str,
        "ldap_server": str,
        "ldap_tls_cacertfile": str,
        "ldap_tls_certfile": str,
        "ldap_tls_keyfile": str,
        # in yaml this is an int but should be a str
        "ldap_tls": int,
        "manage_dhcp": int,
        "manage_dns": int,
        "manage_forward_zones": list,
        Optional("manage_genders", default=0): int,
        "manage_reverse_zones": list,
        "manage_rsync": int,
        Optional("manage_tftp", default=1): int,
        "manage_tftpd": int,
        "mgmt_classes": list,
        "mgmt_parameters": dict,
        "next_server": str,
        "nopxe_with_triggers": int,
        Optional("nsupdate_enabled", default=0): int,
        Optional("nsupdate_log", default="/var/log/cobbler/nsupdate.log"): str,
        Optional("nsupdate_tsig_algorithm", default="hmac-sha512"): str,
        Optional(
            "nsupdate_tsig_key",
            default=[
                "cobbler_update_key.",
                "hvnK54HFJXFasHjzjEn09ASIkCOGYSnofRq4ejsiBHz3udVyGiuebFGAswSjKUxNuhmllPrkI0HRSSmM2qvZug==",
            ],
        ): list,
        "power_management_default_type": str,
        "power_template_dir": str,
        Optional("proxy_url_ext", default=""): Or(None, str),
        "proxy_url_int": str,
        "puppet_auto_setup": int,
        "puppetca_path": str,
        Optional("puppet_parameterized_classes", default=1): int,
        Optional("puppet_server", default="puppet"): str,
        Optional("puppet_version", default=2): int,
        "pxe_just_once": int,
        "redhat_management_key": str,
        "redhat_management_permissive": int,
        "redhat_management_server": str,
        "register_new_installs": int,
        "remove_old_puppet_certs_automatically": int,
        "replicate_repo_rsync_options": str,
        "replicate_rsync_options": str,
        "reposync_flags": str,
        "restart_dhcp": int,
        "restart_dns": int,
        "run_install_triggers": int,
        "scm_push_script": str,
        "scm_track_author": str,
        "scm_track_enabled": int,
        "scm_track_mode": str,
        "serializer_pretty_json": int,
        "server": str,
        Optional(
            "signature_path", default="/var/lib/cobbler/distro_signatures.json"
        ): str,
        Optional(
            "signature_url",
            default="https://cobbler.github.io/signatures/3.0.x/latest.json",
        ): str,
        "sign_puppet_certs_automatically": int,
        "tftpboot_location": str,
        "virt_auto_boot": int,
        "webdir": str,
        "webdir_whitelist": list,
        "xmlrpc_port": int,
        "yum_distro_priority": int,
        "yum_post_install_mirror": int,
        "yumdownloader_flags": str,
    },  # type: ignore
    ignore_extra_keys=False,
)


def validate(settings: Dict[str, Any]) -> bool:
    """
    Checks that a given settings dict is valid according to the reference schema ``schema``.

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
    Migration of the settings ``settings`` to the V3.0.0 settings

    :param settings: The settings dict to migrate
    :return: The migrated dict
    """

    if not V2_8_5.validate(settings):
        raise SchemaError("V2.8.5: Schema error while validating")

    # rename keys and update their value
    old_setting = helper.Setting(
        "default_kickstart", "/var/lib/cobbler/kickstarts/default.ks"
    )
    new_setting = helper.Setting(
        "default_autoinstall", "/var/lib/cobbler/autoinstall_templates/default.ks"
    )
    helper.key_rename(old_setting, "default_autoinstall", settings)
    helper.key_set_value(new_setting, settings)

    old_setting = helper.Setting("snippetsdir", "/var/lib/cobbler/snippets")
    new_setting = helper.Setting(
        "autoinstall_snippets_dir", "/var/lib/cobbler/snippets"
    )
    helper.key_rename(old_setting, "autoinstall_snippets_dir", settings)
    helper.key_set_value(new_setting, settings)

    # add missing keys
    # name - value pairs
    missing_keys = {
        "autoinstall_templates_dir": "/var/lib/cobbler/templates",
        "boot_loader_conf_template_dir": "/etc/cobbler/boot_loader_conf",
        "default_name_servers_search": [],
        "include": ["/etc/cobbler/settings.d/*.settings"],
        "nopxe_with_triggers": 1,
        "scm_push_script": "/bin/true",
        "scm_track_author": "cobbler <cobbler@localhost>",
        "tftpboot_location": "/srv/tftpboot",
        "webdir_whitelist": [],
    }
    for (key, value) in missing_keys.items():
        new_setting = helper.Setting(key, value)
        helper.key_add(new_setting, settings)

    # delete removed keys
    deleted_keys = [
        "consoles",
        "func_auto_setup",
        "func_master",
        "kernel_options_s390x",
        "pxe_template_dir",
        "redhat_management_type",
        "template_remote_kickstarts",
    ]
    for key in deleted_keys:
        helper.key_delete(key, settings)

    # START: migrate-data-v2-to-v3
    def serialize_item(collection: str, item: Dict[str, Any]) -> None:
        """
        Save a collection item to file system

        :param collection: name
        :param item: dictionary
        """
        filename = f"/var/lib/cobbler/collections/{collection}/{item['name']}"

        if settings.get("serializer_pretty_json", False):
            sort_keys = True
            indent = 4
        else:
            sort_keys = False
            indent = None

        filename += ".json"
        with open(filename, "w", encoding="UTF-8") as item_fd:
            data = json.dumps(item, sort_keys=sort_keys, indent=indent)
            item_fd.write(data)

    def deserialize_raw_old(collection_types: str) -> List[Dict[str, Any]]:
        results = []
        all_files = glob.glob(f"/var/lib/cobbler/config/{collection_types}/*")

        for file in all_files:
            with open(file, encoding="UTF-8") as item_fd:
                json_data = item_fd.read()
                _dict = json.loads(json_data)
                results.append(_dict)  # type: ignore
        return results  # type: ignore

    def substitute_paths(value: Any) -> Any:
        if isinstance(value, list):
            value = [substitute_paths(x) for x in value]  # type: ignore
        elif isinstance(value, str):
            value = value.replace("/ks_mirror/", "/distro_mirror/")
        return value

    def transform_key(key: str, value: Any) -> Any:
        if key in transform:
            ret_value = transform[key](value)
        else:
            ret_value = value

        return substitute_paths(ret_value)

    # Keys to add to various collections
    add = {
        "distros": {
            "boot_loader": "grub",
        },
        "profiles": {
            "next_server": "<<inherit>>",
        },
        "systems": {
            "boot_loader": "<<inherit>>",
            "next_server": "<<inherit>>",
            "power_identity_file": "",
            "power_options": "",
            "serial_baud_rate": "",
            "serial_device": "",
        },
    }

    # Keys to remove
    remove = [
        "ldap_enabled",
        "ldap_type",
        "monit_enabled",
        "redhat_management_server",
        "template_remote_kickstarts",
    ]

    # Keys to rename
    rename = {
        "kickstart": "autoinstall",
        "ks_meta": "autoinstall_meta",
    }

    # Keys to transform - use new key name if renamed
    transform = {
        "autoinstall": os.path.basename,
    }

    # Convert the old collections to new collections
    for old_type in [
        "distros.d",
        "files.d",
        "images.d",
        "mgmtclasses.d",
        "packages.d",
        "profiles.d",
        "repos.d",
        "systems.d",
    ]:
        new_type = old_type[:-2]
        # Load old files
        old_collection = deserialize_raw_old(old_type)
        print(f"Processing {old_type}:")

        for old_item in old_collection:
            print(f"    Processing {old_item['name']}")
            new_item = {}
            for key in old_item:
                if key in remove:
                    continue
                if key in rename:
                    new_item[rename[key]] = transform_key(rename[key], old_item[key])
                    continue
                new_item[key] = transform_key(key, old_item[key])

            if new_type in add:
                # We only add items if they don't exist
                for item in add[new_type]:
                    if item not in new_item:
                        new_item[item] = add[new_type][item]

            serialize_item(new_type, new_item)

    path_rename = [
        ("/var/lib/cobbler/kickstarts", "/var/lib/cobbler/templates"),
        ("/var/www/cobbler/ks_mirror", "/var/www/cobbler/distro_mirror"),
    ]

    # Copy paths
    for old_path, new_path in path_rename:
        if os.path.isdir(old_path):
            shutil.copytree(old_path, new_path)
            os.rename(old_path, new_path)

    # END: migrate-data-v2-to-v3
    if not validate(settings):
        raise SchemaError("V3.0.0: Schema error while validating")
    return normalize(settings)
