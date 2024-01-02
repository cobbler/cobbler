"""
Cobbler app-wide settings
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2008, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: 2022 Pablo Suárez Hernández <psuarezhernandez@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC

import datetime
import logging
import os.path
import pathlib
import shutil
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from schema import (  # type: ignore
    SchemaError,
    SchemaMissingKeyError,
    SchemaWrongKeyError,
)

from cobbler.settings import migrations
from cobbler.utils import input_converters


class Settings:
    """
    This class contains all app-wide settings of Cobbler. It should only exist once in a Cobbler instance.
    """

    @staticmethod
    def collection_type() -> str:
        """
        This is a hardcoded string which represents the collection type.

        :return: "setting"
        """
        return "setting"

    @staticmethod
    def collection_types() -> str:
        """
        return the collection plural name
        """
        return "settings"

    def __init__(self) -> None:
        """
        Constructor.
        """
        self.auto_migrate_settings = False
        self.autoinstall_scheme = "http"
        self.allow_duplicate_hostnames = False
        self.allow_duplicate_ips = False
        self.allow_duplicate_macs = False
        self.allow_dynamic_settings = False
        self.always_write_dhcp_entries = False
        self.anamon_enabled = False
        self.auth_token_expiration = 3600
        self.authn_pam_service = "login"
        self.autoinstall_snippets_dir = "/var/lib/cobbler/snippets"
        self.autoinstall_templates_dir = "/var/lib/cobbler/templates"
        self.bind_chroot_path = ""
        self.bind_zonefile_path = "/var/lib/named"
        self.bind_master = "127.0.0.1"
        self.boot_loader_conf_template_dir = "/etc/cobbler/boot_loader_conf"
        self.bootloaders_dir = "/var/lib/cobbler/loaders"
        self.bootloaders_shim_folder = "/usr/share/efi/*/"
        self.bootloaders_shim_file = r"shim\.efi$"
        self.secure_boot_grub_folder = "/usr/share/efi/*/"
        self.secure_boot_grub_file = r"grub\.efi$"
        self.bootloaders_ipxe_folder = "/usr/share/ipxe/"
        self.bootloaders_formats = {
            "aarch64": {"binary_name": "grubaa64.efi"},
            "arm": {"binary_name": "bootarm.efi"},
            "arm64-efi": {
                "binary_name": "grubaa64.efi",
                "extra_modules": ["efinet"],
            },
            "i386-efi": {"binary_name": "bootia32.efi"},
            "i386-pc-pxe": {
                "binary_name": "grub.0",
                "mod_dir": "i386-pc",
                "extra_modules": ["chain", "pxe", "biosdisk"],
            },
            "i686": {"binary_name": "bootia32.efi"},
            "IA64": {"binary_name": "bootia64.efi"},
            "powerpc-ieee1275": {
                "binary_name": "grub.ppc64le",
                "extra_modules": ["net", "ofnet"],
            },
            "x86_64-efi": {
                "binary_name": "grubx64.efi",
                "extra_modules": ["chain", "efinet"],
            },
        }
        self.bootloaders_modules = [
            "btrfs",
            "ext2",
            "xfs",
            "jfs",
            "reiserfs",
            "all_video",
            "boot",
            "cat",
            "configfile",
            "echo",
            "fat",
            "font",
            "gfxmenu",
            "gfxterm",
            "gzio",
            "halt",
            "iso9660",
            "jpeg",
            "linux",
            "loadenv",
            "minicmd",
            "normal",
            "part_apple",
            "part_gpt",
            "part_msdos",
            "password_pbkdf2",
            "png",
            "reboot",
            "search",
            "search_fs_file",
            "search_fs_uuid",
            "search_label",
            "sleep",
            "test",
            "true",
            "video",
            "mdraid09",
            "mdraid1x",
            "lvm",
            "serial",
            "regexp",
            "tr",
            "tftp",
            "http",
            "luks",
            "gcry_rijndael",
            "gcry_sha1",
            "gcry_sha256",
        ]
        self.grubconfig_dir = "/var/lib/cobbler/grub_config"
        self.build_reporting_enabled = False
        self.build_reporting_email: List[str] = []
        self.build_reporting_ignorelist: List[str] = []
        self.build_reporting_sender = ""
        self.build_reporting_smtp_server = "localhost"
        self.build_reporting_subject = ""
        self.buildisodir = "/var/cache/cobbler/buildiso"
        self.cheetah_import_whitelist = ["re", "random", "time"]
        self.client_use_https = False
        self.client_use_localhost = False
        self.cobbler_master = ""
        self.convert_server_to_ip = False
        self.createrepo_flags = "-c cache -s sha"
        self.autoinstall = "default.ks"
        self.default_name_servers: List[str] = []
        self.default_name_servers_search: List[str] = []
        self.default_ownership = ["admin"]
        self.default_password_crypted = r"\$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac."
        self.default_template_type = "cheetah"
        self.default_virt_bridge = "virbr0"
        self.default_virt_disk_driver = "raw"
        self.default_virt_file_size = 5.0
        self.default_virt_ram = 512
        self.default_virt_type = "kvm"
        self.dnsmasq_ethers_file = "/etc/ethers"
        self.dnsmasq_hosts_file = "/var/lib/cobbler/cobbler_hosts"
        self.enable_ipxe = False
        self.enable_menu = True
        self.extra_settings_list: List[str] = []
        self.grub2_mod_dir = "/usr/share/grub2/"
        self.http_port = 80
        self.iso_template_dir = "/etc/cobbler/iso"
        self.jinja2_includedir = "/var/lib/cobbler/jinja2"
        self.kernel_options: Dict[str, Any] = {}
        self.ldap_anonymous_bind = True
        self.ldap_base_dn = "DC=devel,DC=redhat,DC=com"
        self.ldap_port = 389
        self.ldap_search_bind_dn = ""
        self.ldap_search_passwd = ""
        self.ldap_search_prefix = "uid="
        self.ldap_server = "grimlock.devel.redhat.com"
        self.ldap_tls = True
        self.ldap_tls_cacertdir = ""
        self.ldap_tls_cacertfile = ""
        self.ldap_tls_certfile = ""
        self.ldap_tls_keyfile = ""
        self.ldap_tls_reqcert = "hard"
        self.ldap_tls_cipher_suite = ""
        self.bind_manage_ipmi = False
        # TODO: Remove following line
        self.manage_dhcp = False
        self.manage_dhcp_v6 = False
        self.manage_dhcp_v4 = False
        self.manage_dns = False
        self.manage_forward_zones: List[str] = []
        self.manage_reverse_zones: List[str] = []
        self.manage_genders = False
        self.manage_rsync = False
        self.manage_tftpd = True
        self.modules = {
            "authentication": {
                "module": "authentication.configfile",
                "hash_algorithm": "sha3_512",
            },
            "authorization": {"module": "authorization.allowall"},
            "dns": {"module": "managers.bind"},
            "dhcp": {"module": "managers.isc"},
            "tftpd": {"module": "managers.in_tftpd"},
            "serializers": {"module": "serializers.file"},
        }
        self.mongodb = {"host": "localhost", "port": 27017}
        self.next_server_v4 = "127.0.0.1"
        self.next_server_v6 = "::1"
        self.nsupdate_enabled = False
        self.nsupdate_log = "/var/log/cobbler/nsupdate.log"
        self.nsupdate_tsig_algorithm = "hmac-sha512"
        self.nsupdate_tsig_key: List[str] = []
        self.power_management_default_type = "ipmilanplus"
        self.proxies: List[str] = []
        self.proxy_url_ext = ""
        self.proxy_url_int = ""
        self.puppet_auto_setup = False
        self.puppet_parameterized_classes = True
        self.puppet_server = "puppet"
        self.puppet_version = 2
        self.puppetca_path = "/usr/bin/puppet"
        self.pxe_just_once = True
        self.nopxe_with_triggers = True
        self.redhat_management_permissive = False
        self.redhat_management_server = "xmlrpc.rhn.redhat.com"
        self.redhat_management_key = ""
        self.redhat_management_org = ""
        self.redhat_management_user = ""
        self.redhat_management_password = ""
        self.uyuni_authentication_endpoint = ""
        self.register_new_installs = False
        self.remove_old_puppet_certs_automatically = False
        self.replicate_repo_rsync_options = "-avzH"
        self.replicate_rsync_options = "-avzH"
        self.reposync_flags = "-l -m -d"
        self.reposync_rsync_flags = ""
        self.restart_dhcp = True
        self.restart_dns = True
        self.run_install_triggers = True
        self.scm_track_enabled = False
        self.scm_track_mode = "git"
        self.scm_track_author = "cobbler <cobbler@localhost>"
        self.scm_push_script = "/bin/true"
        self.serializer_pretty_json = False
        self.server = "127.0.0.1"
        self.sign_puppet_certs_automatically = False
        self.signature_path = "/var/lib/cobbler/distro_signatures.json"
        self.signature_url = "https://cobbler.github.io/signatures/3.0.x/latest.json"
        self.syslinux_dir = "/usr/share/syslinux"
        self.syslinux_memdisk_folder = "/usr/share/syslinux"
        self.syslinux_pxelinux_folder = "/usr/share/syslinux"
        self.tftpboot_location = "/var/lib/tftpboot"
        self.virt_auto_boot = True
        self.webdir = "/var/www/cobbler"
        self.webdir_whitelist = [
            ".link_cache",
            "misc",
            "distro_mirror",
            "images",
            "links",
            "localmirror",
            "pub",
            "rendered",
            "repo_mirror",
            "repo_profile",
            "repo_system",
            "svc",
            "web",
            "webui",
        ]
        self.xmlrpc_port = 25151
        self.yum_distro_priority = 1
        self.yum_post_install_mirror = True
        self.yumdownloader_flags = "--resolve"
        self.windows_enabled = False
        self.windows_template_dir = "/etc/cobbler/windows"
        self.samba_distro_share = "DISTRO"
        self.cache_enabled = False
        self.lazy_start = False
        self.memory_indexes = {
            "distro": {
                "uid": {"nonunique": False, "disabled": False},
                "arch": {"nonunique": True, "disabled": False},
            },
            "image": {
                "uid": {"nonunique": False, "disabled": False},
                "arch": {"nonunique": True, "disabled": False},
                "menu": {"nonunique": True, "disabled": False},
            },
            "menu": {
                "uid": {"nonunique": False, "disabled": False},
                "parent": {
                    "nonunique": True,
                    "disabled": False,
                },
            },
            "profile": {
                "uid": {"nonunique": False, "disabled": False},
                "parent": {
                    "nonunique": True,
                    "disabled": False,
                },
                "distro": {"nonunique": True, "disabled": False},
                "arch": {"nonunique": True, "disabled": False},
                "menu": {"nonunique": True, "disabled": False},
                "repos": {"nonunique": True, "disabled": False},
            },
            "repo": {
                "uid": {"nonunique": False, "disabled": False},
            },
            "system": {
                "uid": {"nonunique": False, "disabled": False},
                "image": {"nonunique": True, "disabled": False},
                "profile": {"nonunique": True, "disabled": False},
                "mac_address": {
                    "property": "get_mac_addresses",
                    "nonunique": self.allow_duplicate_macs,
                    "disabled": self.allow_duplicate_macs,
                },
                "ip_address": {
                    "property": "get_ipv4_addresses",
                    "nonunique": self.allow_duplicate_ips,
                    "disabled": self.allow_duplicate_ips,
                },
                "ipv6_address": {
                    "property": "get_ipv6_addresses",
                    "nonunique": self.allow_duplicate_ips,
                    "disabled": self.allow_duplicate_ips,
                },
                "dns_name": {
                    "property": "get_dns_names",
                    "nonunique": self.allow_duplicate_hostnames,
                    "disabled": self.allow_duplicate_hostnames,
                },
            },
        }

    def to_dict(self, resolved: bool = False) -> Dict[str, Any]:
        """
        Return an easily serializable representation of the config.

        .. deprecated:: 3.2.1
           Use ``obj.__dict__`` directly please. Will be removed with 3.3.0

        :param resolved: Present for the compatibility with the Cobbler collections.
        :return: The dict with all user settings combined with settings which are left to the default.
        """
        # TODO: Deprecate and remove. Tailcall is not needed.
        return self.__dict__

    def from_dict(self, new_values: Dict[str, Any]) -> Optional["Settings"]:
        """
        Modify this object to load values in dictionary. If the handed dict would lead to an invalid object it is
        silently discarded.

        .. warning:: If the dict from the args has not all settings included Cobbler may behave unexpectedly.

        :param new_values: The dictionary with settings to replace.
        :return: Returns the settings instance this method was called from.
        """
        if new_values is None:  # type: ignore[reportUnnecessaryComparison]
            logging.warning("Not loading empty settings dictionary!")
            return None

        old_settings = self.__dict__  # pylint: disable=access-member-before-definition
        self.__dict__.update(  # pylint: disable=access-member-before-definition
            new_values
        )

        if not self.is_valid():
            self.__dict__ = old_settings
            raise ValueError(
                "New settings would not be valid. Please fix the dict you pass."
            )

        return self

    def is_valid(self) -> bool:
        """
        Silently drops all errors and returns ``True`` when everything is valid.

        :return: If this settings object is valid this returns true. Otherwise false.
        """
        try:
            validate_settings(self.__dict__)
        except SchemaError:
            return False
        return True

    def __getattr__(self, name: str) -> Any:
        """
        This returns the current value of the setting named in the args.

        :param name: The setting to return the value of.
        :return: The value of the setting "name".
        """
        try:
            if name == "kernel_options":
                # backwards compatibility -- convert possible string value to dict
                result = input_converters.input_string_or_dict(
                    self.__dict__[name], allow_multiples=False
                )
                self.__dict__[name] = result
                return result
            # TODO: This needs to be explicitly tested
            if name == "manage_dhcp":
                return self.manage_dhcp_v4
            return self.__dict__[name]
        except Exception as error:
            if name in self.__dict__:
                return self.__dict__[name]

            raise AttributeError(
                f"no settings attribute named '{name}' found"
            ) from error

    def save(
        self,
        filepath: str = "/etc/cobbler/settings.yaml",
        ignore_keys: Optional[List[str]] = None,
    ) -> None:
        """
        Saves the settings to the disk.
        :param filepath: This sets the path of the settingsfile to write.
        :param ignore_keys: The list of ignore keys to exclude from migration.
        """
        if not ignore_keys:
            ignore_keys = []
        update_settings_file(self.to_dict(), filepath, ignore_keys)


def validate_settings(
    settings_content: Dict[str, Any], ignore_keys: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    This function performs logical validation of our loaded YAML files.
    This function will:
    - Perform type validation on all values of all keys.
    - Provide defaults for optional settings.
    :param settings_content: The dictionary content from the YAML file.
    :param ignore_keys: The list of ignore keys to exclude from validation.
    :raises SchemaError: In case the data given is invalid.
    :return: The Settings of Cobbler which can be safely used inside this instance.
    """
    if not ignore_keys:
        ignore_keys = []

    # Extra settings and ignored keys are excluded from validation
    data, data_to_exclude_from_validation = migrations.filter_settings_to_validate(
        settings_content, ignore_keys
    )

    result = migrations.normalize(data)
    result.update(data_to_exclude_from_validation)
    return result


def read_yaml_file(filepath: str = "/etc/cobbler/settings.yaml") -> Dict[str, Any]:
    """
    Reads settings files from ``filepath`` and saves the content in a dictionary.

    :param filepath: Settings file path, defaults to "/ect/cobbler/settings.yaml"
    :raises FileNotFoundError: In case file does not exist or is a directory.
    :raises yaml.YAMLError: In case the file is not a valid YAML file.
    :return: The aggregated dict of all settings.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(
            f'Given path "{filepath}" does not exist or is a directory.'
        )
    try:
        with open(filepath, encoding="UTF-8") as main_settingsfile:
            filecontent: Dict[str, Any] = yaml.safe_load(main_settingsfile.read())
    except yaml.YAMLError as error:
        traceback.print_exc()
        raise yaml.YAMLError(f'"{filepath}" is not a valid YAML file') from error
    return filecontent


def read_settings_file(
    filepath: str = "/etc/cobbler/settings.yaml",
    ignore_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Utilizes ``read_yaml_file()``. If the read settings file is invalid in the context of Cobbler we will return an
    empty dictionary.

    :param filepath: The path to the settings file.
    :param ignore_keys: The list of ignore keys to exclude from validation.
    :raises SchemaMissingKeyError: In case keys are minssing.
    :raises SchemaWrongKeyError: In case keys are not listed in the schema.
    :raises SchemaError: In case the schema is wrong.
    :return: A dictionary with the settings. As a word of caution: This may not represent a correct settings object, it
             will only contain a correct YAML representation.
    """
    if not ignore_keys:
        ignore_keys = []

    filecontent = read_yaml_file(filepath)

    # FIXME: Do not call validate_settings() because of chicken - egg problem
    try:
        validate_settings(filecontent, ignore_keys)
    except SchemaMissingKeyError:
        logging.exception("Settings file was not returned due to missing keys.")
        logging.debug('The settings to read were: "%s"', filecontent)
        return {}
    except SchemaWrongKeyError:
        logging.exception("Settings file was returned due to an error in the schema.")
        logging.debug('The settings to read were: "%s"', filecontent)
        return {}
    except SchemaError:
        logging.exception("Settings file was returned due to an error in the schema.")
        logging.debug('The settings to read were: "%s"', filecontent)
        return {}
    return filecontent


def update_settings_file(
    data: Dict[str, Any],
    filepath: str = "/etc/cobbler/settings.yaml",
    ignore_keys: Optional[List[str]] = None,
) -> bool:
    """
    Write data handed to this function into the settings file of Cobbler. This function overwrites the existing content.
    It will only write valid settings. If you are trying to save invalid data this will raise a SchemaException
    described in :py:meth:`cobbler.settings.validate`.

    :param data: The data to put into the settings file.
    :param filepath: This sets the path of the settingsfile to write.
    :param ignore_keys: The list of ignore keys to exclude from validation.
    :return: True if the action succeeded. Otherwise return False.
    """
    if not ignore_keys:
        ignore_keys = []

    # Backup old settings file
    path = pathlib.Path(filepath)
    if path.exists():
        timestamp = str(datetime.datetime.now().strftime("%Y%m%d_%H-%M-%S"))
        shutil.copy(path, path.parent.joinpath(f"{path.stem}_{timestamp}{path.suffix}"))

    try:
        validated_data = validate_settings(data, ignore_keys)
        version = migrations.get_installed_version()

        # If "ignore_keys" was set during migration, we persist these keys as "extra_settings_list"
        # in the final settings, so the migrated settings are able to validate later
        if ignore_keys or "extra_settings_list" in validated_data:
            if "extra_settings_list" in validated_data:
                validated_data["extra_settings_list"].extend(ignore_keys)
                # Remove items from "extra_settings_list" in case it is now a valid settings
                current_schema = list(
                    map(
                        lambda x: getattr(x, "_schema", x),
                        migrations.VERSION_LIST[version].schema._schema.keys(),
                    )
                )
                validated_data["extra_settings_list"] = [
                    x
                    for x in validated_data["extra_settings_list"]
                    if x not in current_schema
                ]
            else:
                validated_data["extra_settings_list"] = ignore_keys
            validated_data["extra_settings_list"] = list(
                set(validated_data["extra_settings_list"])
            )

        with open(filepath, "w", encoding="UTF-8") as settings_file:
            yaml_dump = yaml.safe_dump(validated_data)
            header = "# Cobbler settings file\n"
            header += "# Docs for this file can be found at: https://cobbler.readthedocs.io/en/latest/cobbler-conf.html"
            header += "\n\n"
            yaml_dump = header + yaml_dump
            settings_file.write(yaml_dump)
        return True
    except SchemaMissingKeyError:
        logging.exception(
            "Settings file was not written to the disc due to missing keys."
        )
        logging.debug('The settings to write were: "%s"', data)
        return False
    except SchemaError:
        logging.exception(
            "Settings file was not written to the disc due to an error in the schema."
        )
        logging.debug('The settings to write were: "%s"', data)
        return False


def migrate(
    yaml_dict: Dict[str, Any],
    settings_path: Path,
    ignore_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Migrates the current settings

    :param yaml_dict: The settings dict
    :param settings_path: The settings path
    :param ignore_keys: The list of ignore keys to exclude from migration.
    :return: The migrated settings
    """
    if not ignore_keys:
        ignore_keys = []

    # Extra settings and ignored keys are excluded from validation
    data, data_to_exclude_from_validation = migrations.filter_settings_to_validate(
        yaml_dict, ignore_keys
    )

    result = migrations.migrate(data, settings_path)
    result.update(data_to_exclude_from_validation)
    return result
