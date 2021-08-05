"""
Cobbler app-wide settings

Copyright 2006-2008, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""
import glob
import logging
import os.path
import re
import traceback
from typing import Union, Dict, Hashable, Any

import yaml
from schema import Schema, Optional, SchemaError, SchemaMissingKeyError, SchemaWrongKeyError

from cobbler import utils

# TODO: Only log settings dict on error and not always!

BIND_CHROOT_PATH = ""


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
        self.bind_chroot_path = BIND_CHROOT_PATH
        self.bind_zonefile_path = "/var/lib/named"
        self.bind_master = "127.0.0.1"
        self.boot_loader_conf_template_dir = "/etc/cobbler/boot_loader_conf"
        self.bootloaders_dir = "/var/lib/cobbler/loaders"
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
        self.default_virt_file_size = 5
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
        self.ldap_tls_cacertfile = ""
        self.ldap_tls_certfile = ""
        self.ldap_tls_keyfile = ""
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

    def to_dict(self) -> dict:
        """
        Return an easily serializable representation of the config.

        .. deprecated:: 3.2.1
           Use ``obj.__dict__`` directly please. Will be removed with 3.3.0

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
                (success, result) = utils.input_string_or_dict(self.__dict__[name], allow_multiples=False)
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

    def save(self):
        """
        Saves the settings to the disk.
        """
        update_settings_file(self.to_dict())


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
    schema = Schema({
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
    return schema.validate(settings_content)


def parse_bind_config(configpath: str):
    """
    Parse the Bind9 configuration file and adjust the Cobbler default settings according to the readings.

    :param configpath: The path in the filesystem where the file can be read.
    """
    global BIND_CHROOT_PATH
    bind_config = {}
    # When running as a webapp we can't access this, but don't need it
    try:
        bind_config_file = open(configpath, "r")
    except (IOError, OSError):
        pass
    else:
        for line in bind_config_file:
            if re.match(r"[a-zA-Z]+=", line):
                (name, value) = line.rstrip().split("=")
                bind_config[name] = value.strip('"')
        # RHEL, SysV Fedora
        if "ROOTDIR" in bind_config:
            BIND_CHROOT_PATH = bind_config["ROOTDIR"]
        # Debian, Systemd Fedora
        if "OPTIONS" in bind_config:
            rootdirmatch = re.search(r"-t ([/\w]+)", bind_config["OPTIONS"])
            if rootdirmatch is not None:
                BIND_CHROOT_PATH = rootdirmatch.group(1)


def autodetect_bind_chroot():
    """
    Autodetect bind chroot configuration
    """
    bind_config_filename = None
    if os.path.exists("/etc/sysconfig/named"):
        # RHEL/Fedora
        bind_config_filename = "/etc/sysconfig/named"
    else:
        # Debian
        bind_config_files = glob.glob("/etc/default/bind*")
        for filename in bind_config_files:
            if os.path.exists(filename):
                bind_config_filename = filename
    # Parse the config file if available
    if bind_config_filename:
        parse_bind_config(bind_config_filename)


def __migrate_settingsfile_name(filename="/etc/cobbler/settings") -> str:
    if filename[-8:] == "settings" and os.path.exists(filename):
        os.rename(filename, filename + ".yaml")
        filename += ".yaml"
    return filename


def __migrate_settingsfile_gpxe_ipxe(settings_dict: dict) -> dict:
    """
    Replaces the old ``enable_gpxe`` key nmae with the new ``enable_ipxe`` one.

    :param settings_dict: A dictionary with the settings.
    :return A dictionary with the changed settings.
    """
    if "enable_gpxe" in settings_dict:
        settings_dict["enable_ipxe"] = settings_dict.pop("enable_gpxe")
    return settings_dict


def __migrate_settingsfile_int_bools(settings_dict: dict) -> dict:
    for key in settings_dict:
        if isinstance(getattr(Settings(), key), bool):
            settings_dict[key] = utils.input_boolean(settings_dict[key])
    mgmt_parameters = "mgmt_parameters"
    if mgmt_parameters in settings_dict and "from_cobbler" in settings_dict[mgmt_parameters]:
        settings_dict[mgmt_parameters]["from_cobbler"] = utils.input_boolean(
            settings_dict[mgmt_parameters]["from_cobbler"]
        )
    return settings_dict


def read_settings_file(filepath="/etc/cobbler/settings.yaml") -> Union[Dict[Hashable, Any], list, None]:
    """
    Reads the settings file from the default location or the given one. This method then also recursively includes all
    files in the ``include`` directory. Any key may be overwritten in a later loaded settings file. The last loaded file
    wins. If the read settings file is invalid in the context of Cobbler we will return an empty Dictionary.

    :param filepath: The path to the settings file.
    :return: A dictionary with the settings. As a word of caution: This may not represent a correct settings object, it
             will only contain a correct YAML representation.
    :raises yaml.YAMLError: If the YAML file is not syntactically valid or could not be read.
    :raises FileNotFoundError: If the file handed to the function does not exist.
    """
    filepath = __migrate_settingsfile_name(filepath)
    if not os.path.exists(filepath):
        raise FileNotFoundError("Given path \"%s\" does not exist." % filepath)
    try:
        with open(filepath) as main_settingsfile:
            filecontent = yaml.safe_load(main_settingsfile.read())

            for ival in filecontent.get("include", []):
                for ifile in glob.glob(ival):
                    with open(ifile, 'r') as extra_settingsfile:
                        filecontent.update(yaml.safe_load(extra_settingsfile.read()))
    except yaml.YAMLError as error:
        traceback.print_exc()
        raise yaml.YAMLError("\"%s\" is not a valid YAML file" % filepath) from error
    filecontent = __migrate_settingsfile_gpxe_ipxe(filecontent)
    filecontent = __migrate_settingsfile_int_bools(filecontent)
    try:
        validate_settings(filecontent)
    except SchemaMissingKeyError:
        logging.exception("Settings file was not returned due to missing keys.")
        logging.debug("The settings to read were: \"%s\"", filecontent)
        return {}
    except SchemaWrongKeyError:
        logging.exception("Settings file was returned due to an error in the schema.")
        logging.debug("The settings to read were: \"%s\"", filecontent)
        return {}
    except SchemaError:
        logging.exception("Settings file was returned due to an error in the schema.")
        logging.debug("The settings to read were: \"%s\"", filecontent)
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
    try:
        validated_data = validate_settings(data)
        filepath = __migrate_settingsfile_name(filepath)
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
        logging.debug("The settings to write were: \"%s\"", data)
        return False
    except SchemaError:
        logging.exception("Settings file was not written to the disc due to an error in the schema.")
        logging.debug("The settings to write were: \"%s\"", data)
        return False


# Initialize Settings module for manipulating the global DEFAULTS variable
autodetect_bind_chroot()
