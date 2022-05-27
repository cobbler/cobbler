"""
Cobbler app-wide settings
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2008, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC

import datetime
import glob
import logging
import os.path
import pathlib
import shutil
import traceback
from pathlib import Path
from typing import Any, Dict, Hashable
import yaml
from schema import SchemaError, SchemaMissingKeyError, SchemaWrongKeyError

from cobbler import utils
from cobbler.settings import migrations


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

    def __init__(self):
        """
        Constructor.
        """
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
        self.bootloaders_ipxe_folder = "/usr/share/ipxe/"
        self.grubconfig_dir = "/var/lib/cobbler/grub_config"
        self.build_reporting_enabled = False
        self.build_reporting_email = []
        self.build_reporting_ignorelist = []
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
        self.default_name_servers = []
        self.default_name_servers_search = []
        self.default_ownership = ["admin"]
        self.default_password_crypted = r"\$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac."
        self.default_template_type = "cheetah"
        self.default_virt_bridge = "xenbr0"
        self.default_virt_disk_driver = "raw"
        self.default_virt_file_size = 5.0
        self.default_virt_ram = 512
        self.default_virt_type = "auto"
        self.enable_ipxe = False
        self.enable_menu = True
        self.http_port = 80
        self.include = ["/etc/cobbler/settings.d/*.settings"]
        self.iso_template_dir = "/etc/cobbler/iso"
        self.jinja2_includedir = "/var/lib/cobbler/jinja2"
        self.kernel_options = {}
        self.ldap_anonymous_bind = True
        self.ldap_base_dn = "DC=devel,DC=redhat,DC=com"
        self.ldap_port = 389
        self.ldap_search_bind_dn = ""
        self.ldap_search_passwd = ""
        self.ldap_search_prefix = 'uid='
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
        self.manage_forward_zones = []
        self.manage_reverse_zones = []
        self.manage_genders = False
        self.manage_rsync = False
        self.manage_tftpd = True
        self.mgmt_classes = []
        self.mgmt_parameters = {}
        self.next_server_v4 = "127.0.0.1"
        self.next_server_v6 = "::1"
        self.nsupdate_enabled = False
        self.nsupdate_log = "/var/log/cobbler/nsupdate.log"
        self.nsupdate_tsig_algorithm = "hmac-sha512"
        self.nsupdate_tsig_key = []
        self.power_management_default_type = "ipmilanplus"
        self.proxies = []
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
        self.virt_auto_boot = False
        self.webdir = "/var/www/cobbler"
        self.webdir_whitelist = [".link_cache", "misc", "distro_mirror", "images", "links", "localmirror", "pub",
                                 "rendered", "repo_mirror", "repo_profile", "repo_system", "svc", "web", "webui"]
        self.xmlrpc_port = 25151
        self.yum_distro_priority = 1
        self.yum_post_install_mirror = True
        self.yumdownloader_flags = "--resolve"
        self.windows_enabled = False
        self.windows_template_dir = "/etc/cobbler/windows"
        self.samba_distro_share = "DISTRO"

    def to_string(self) -> str:
        """
        Returns the kernel options as a string.

        :return: The multiline string with the kernel options.
        """
        buf = "defaults\n"
        buf += "kernel options  : %s\n" % self.__dict__['kernel_options']
        return buf

    def to_dict(self, resolved: bool = False) -> dict:
        """
        Return an easily serializable representation of the config.

        .. deprecated:: 3.2.1
           Use ``obj.__dict__`` directly please. Will be removed with 3.3.0

        :param resolved: Present for the compatibility with the Cobbler collections.
        :return: The dict with all user settings combined with settings which are left to the default.
        """
        # TODO: Deprecate and remove. Tailcall is not needed.
        return self.__dict__

    def from_dict(self, new_values):
        """
        Modify this object to load values in dictionary. If the handed dict would lead to an invalid object it is
        silently discarded.

        .. warning:: If the dict from the args has not all settings included Cobbler may behave unexpectedly.

        :param new_values: The dictionary with settings to replace.
        :return: Returns the settings instance this method was called from.
        """
        if new_values is None:
            logging.warning("Not loading empty settings dictionary!")
            return

        old_settings = self.__dict__

        self.__dict__.update(new_values)

        if not self.is_valid():
            self.__dict__ = old_settings

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

    def __getattr__(self, name):
        """
        This returns the current value of the setting named in the args.

        :param name: The setting to return the value of.
        :return: The value of the setting "name".
        """
        try:
            if name == "kernel_options":
                # backwards compatibility -- convert possible string value to dict
                result = utils.input_string_or_dict(
                    self.__dict__[name], allow_multiples=False
                )
                self.__dict__[name] = result
                return result
            # TODO: This needs to be explicitly tested
            elif name == "manage_dhcp":
                return self.manage_dhcp_v4
            return self.__dict__[name]
        except Exception as error:
            if name in self.__dict__:
                return self.__dict__[name]
            else:
                raise AttributeError(f"no settings attribute named '{name}' found") from error

    def save(self, filepath="/etc/cobbler/settings.yaml"):
        """
        Saves the settings to the disk.
        """
        update_settings_file(self.to_dict(), filepath)


def validate_settings(settings_content: dict) -> dict:
    """
    This function performs logical validation of our loaded YAML files.
    This function will:
    - Perform type validation on all values of all keys.
    - Provide defaults for optional settings.
    :param settings_content: The dictionary content from the YAML file.
    :raises SchemaError: In case the data given is invalid.
    :return: The Settings of Cobbler which can be safely used inside this instance.
    """
    return migrations.normalize(settings_content)


def read_yaml_file(filepath="/ect/cobbler/settings.yaml") -> Dict[Hashable, Any]:
    """
    Reads settings files from ``filepath`` and all paths in `include` (which is read from the settings file) and saves
    the content in a dictionary.
    Any key may be overwritten in a later loaded settings file. The last loaded file wins.

    :param filepath: Settings file path, defaults to "/ect/cobbler/settings.yaml"
    :raises FileNotFoundError: In case file does not exist or is a directory.
    :raises yaml.YAMLError: In case the file is not a valid YAML file.
    :return: The aggregated dict of all settings.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError('Given path "%s" does not exist or is a directory.' % filepath)
    try:
        with open(filepath) as main_settingsfile:
            filecontent = yaml.safe_load(main_settingsfile.read())

            for ival in filecontent.get("include", []):
                for ifile in glob.glob(ival):
                    with open(ifile, 'r') as extra_settingsfile:
                        filecontent.update(yaml.safe_load(extra_settingsfile.read()))
    except yaml.YAMLError as error:
        traceback.print_exc()
        raise yaml.YAMLError('"%s" is not a valid YAML file' % filepath) from error
    return filecontent


def read_settings_file(filepath="/etc/cobbler/settings.yaml") -> Dict[Hashable, Any]:
    """
    Utilizes ``read_yaml_file()``. If the read settings file is invalid in the context of Cobbler we will return an
    empty dictionary.

    :param filepath: The path to the settings file.
    :raises SchemaMissingKeyError: In case keys are minssing.
    :raises SchemaWrongKeyError: In case keys are not listed in the schema.
    :raises SchemaError: In case the schema is wrong.
    :return: A dictionary with the settings. As a word of caution: This may not represent a correct settings object, it
             will only contain a correct YAML representation.
    """
    filecontent = read_yaml_file(filepath)

    # FIXME: Do not call validate_settings() because of chicken - egg problem
    try:
        validate_settings(filecontent)
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


def update_settings_file(data: dict, filepath="/etc/cobbler/settings.yaml") -> bool:
    """
    Write data handed to this function into the settings file of Cobbler. This function overwrites the existing content.
    It will only write valid settings. If you are trying to save invalid data this will raise a SchemaException
    described in :py:meth:`cobbler.settings.validate`.

    :param data: The data to put into the settings file.
    :param filepath: This sets the path of the settingsfile to write.
    :return: True if the action succeeded. Otherwise return False.
    """
    # Backup old settings file
    path = pathlib.Path(filepath)
    if path.exists():
        timestamp = str(datetime.datetime.now().strftime("%Y%m%d_%H-%M-%S"))
        shutil.copy(path, path.parent.joinpath(f"{path.stem}_{timestamp}{path.suffix}"))

    try:
        validated_data = validate_settings(data)
        with open(filepath, "w") as settings_file:
            yaml_dump = yaml.safe_dump(validated_data)
            header = "# Cobbler settings file\n"
            header += "# Docs for this file can be found at: https://cobbler.readthedocs.io/en/latest/cobbler-conf.html"
            header += "\n\n"
            yaml_dump = header + yaml_dump
            settings_file.write(yaml_dump)
        return True
    except SchemaMissingKeyError:
        logging.exception("Settings file was not written to the disc due to missing keys.")
        logging.debug('The settings to write were: "%s"', data)
        return False
    except SchemaError:
        logging.exception("Settings file was not written to the disc due to an error in the schema.")
        logging.debug('The settings to write were: "%s"', data)
        return False


def migrate(yaml_dict: dict, settings_path: Path) -> dict:
    """
    Migrates the current settings

    :param yaml_dict: The settings dict
    :param settings_path: The settings path
    :return: The migrated settings
    """
    return migrations.migrate(yaml_dict, settings_path)
