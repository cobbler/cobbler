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
from schema import Schema, Optional, SchemaError, SchemaMissingKeyError

from cobbler import utils

# TODO: Convert this into properties for 3.3.0
# defaults is to be used if the config file doesn't contain the value we need
DEFAULTS = {
    "allow_duplicate_hostnames": [False, "bool"],
    "allow_duplicate_ips": [False, "bool"],
    "allow_duplicate_macs": [False, "bool"],
    "allow_dynamic_settings": [False, "bool"],
    "always_write_dhcp_entries": [False, "bool"],
    "anamon_enabled": [False, "bool"],
    "auth_token_expiration": [3600, "int"],
    "authn_pam_service": ["login", "str"],
    "autoinstall_snippets_dir": ["/var/lib/cobbler/snippets", "str"],
    "autoinstall_templates_dir": ["/var/lib/cobbler/templates", "str"],
    "bind_chroot_path": ["", "str"],
    "bind_master": ["127.0.0.1", "str"],
    "boot_loader_conf_template_dir": ["/etc/cobbler/boot_loader_conf", "str"],
    "bootloaders_dir": ["/var/lib/cobbler/loaders", "str"],
    "grubconfig_dir": ["/var/lib/cobbler/grub_config", "str"],
    "build_reporting_enabled": [False, "bool"],
    "build_reporting_email": [[], "list"],
    "build_reporting_ignorelist": [[], "list"],
    "build_reporting_sender": ["", "str"],
    "build_reporting_smtp_server": ["localhost", "str"],
    "build_reporting_subject": ["", "str"],
    "buildisodir": ["/var/cache/cobbler/buildiso", "str"],
    "cache_enabled": [True, "bool"],
    "cheetah_import_whitelist": [["re", "random", "time"], "list"],
    "client_use_https": [False, "bool"],
    "client_use_localhost": [False, "bool"],
    "cobbler_master": ["", "str"],
    "convert_server_to_ip": [False, "bool"],
    "createrepo_flags": ["-c cache -s sha", "str"],
    "default_autoinstall": ["/var/lib/cobbler/templates/default.ks", "str"],
    "default_name_servers": [[], "list"],
    "default_name_servers_search": [[], "list"],
    "default_ownership": [["admin"], "list"],
    "default_password_crypted": [r"\$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.", "str"],
    "default_template_type": ["cheetah", "str"],
    "default_virt_bridge": ["xenbr0", "str"],
    "default_virt_disk_driver": ["raw", "str"],
    "default_virt_file_size": [5, "int"],
    "default_virt_ram": [512, "int"],
    "default_virt_type": ["auto", "str"],
    "enable_gpxe": [False, "bool"],
    "enable_menu": [True, "bool"],
    "http_port": [80, "int"],
    "include": [["/etc/cobbler/settings.d/*.settings"], "list"],
    "iso_template_dir": ["/etc/cobbler/iso", "str"],
    "jinja2_includedir": ["/var/lib/cobbler/jinja2", "str"],
    "kernel_options": [{}, "dict"],
    "ldap_anonymous_bind": [True, "bool"],
    "ldap_base_dn": ["DC=devel,DC=redhat,DC=com", "str"],
    "ldap_port": [389, "int"],
    "ldap_search_bind_dn": ["", "str"],
    "ldap_search_passwd": ["", "str"],
    "ldap_search_prefix": ['uid=', "str"],
    "ldap_server": ["grimlock.devel.redhat.com", "str"],
    "ldap_tls": [True, "bool"],
    "ldap_tls_cacertfile": ["", "str"],
    "ldap_tls_certfile": ["", "str"],
    "ldap_tls_keyfile": ["", "str"],
    "bind_manage_ipmi": [False, "bool"],
    "manage_dhcp": [False, "bool"],
    "manage_dns": [False, "bool"],
    "manage_forward_zones": [[], "list"],
    "manage_reverse_zones": [[], "list"],
    "manage_genders": [False, "bool"],
    "manage_rsync": [False, "bool"],
    "manage_tftpd": [True, "bool"],
    "mgmt_classes": [[], "list"],
    "mgmt_parameters": [{}, "dict"],
    "next_server": ["127.0.0.1", "str"],
    "nsupdate_enabled": [False, "bool"],
    "nsupdate_log": ["/var/log/cobbler/nsupdate.log", "str"],
    "nsupdate_tsig_algorithm": ["hmac-sha512", "str"],
    "nsupdate_tsig_key": [[], "list"],
    "power_management_default_type": ["ipmilan", "str"],
    "proxy_url_ext": ["", "str"],
    "proxy_url_int": ["", "str"],
    "puppet_auto_setup": [False, "bool"],
    "puppet_parameterized_classes": [True, "bool"],
    "puppet_server": ["puppet", "str"],
    "puppet_version": [2, "int"],
    "puppetca_path": ["/usr/bin/puppet", "str"],
    "pxe_just_once": [True, "bool"],
    "nopxe_with_triggers": [True, "bool"],
    "redhat_management_permissive": [False, "bool"],
    "redhat_management_server": ["xmlrpc.rhn.redhat.com", "str"],
    "redhat_management_key": ["", "str"],
    "register_new_installs": [False, "bool"],
    "remove_old_puppet_certs_automatically": [False, "bool"],
    "replicate_repo_rsync_options": ["-avzH", "str"],
    "replicate_rsync_options": ["-avzH", "str"],
    "reposync_flags": ["-l -m -d", "str"],
    "reposync_rsync_flags": ["", "str"],
    "restart_dhcp": [True, "bool"],
    "restart_dns": [True, "bool"],
    "run_install_triggers": [True, "bool"],
    "scm_track_enabled": [False, "bool"],
    "scm_track_mode": ["git", "str"],
    "scm_track_author": ["cobbler <cobbler@localhost>", "str"],
    "scm_push_script": ["/bin/true", "str"],
    "serializer_pretty_json": [False, "bool"],
    "server": ["127.0.0.1", "str"],
    "sign_puppet_certs_automatically": [False, "bool"],
    "signature_path": ["/var/lib/cobbler/distro_signatures.json", "str"],
    "signature_url": ["https://cobbler.github.io/signatures/3.0.x/latest.json", "str"],
    "tftpboot_location": ["/var/lib/tftpboot", "str"],
    "virt_auto_boot": [False, "bool"],
    "webdir": ["/var/www/cobbler", "str"],
    "webdir_whitelist": [".link_cache", "misc", "distro_mirror", "images", "links", "localmirror", "pub", "rendered",
                         "repo_mirror", "repo_profile", "repo_system", "svc", "web", "webui"],
    "xmlrpc_port": [25151, "int"],
    "yum_distro_priority": [1, "int"],
    "yum_post_install_mirror": [True, "bool"],
    "yumdownloader_flags": ["--resolve", "str"],
}

FIELDS = [
    ["name", "", "", "Name", True, "Ex: server", 0, "str"],
    ["value", "", "", "Value", True, "Ex: 127.0.0.1", 0, "str"],
]


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
        for key in list(DEFAULTS.keys()):
            self.__dict__[key] = DEFAULTS[key][0]

    def set(self, name, value):
        """
        Alias for setting an option "name" to the new value "value". (See __settattr__)

        .. deprecated:: 3.2.1
           Use ``obj.__settattr__`` directly please. Will be removed with 3.3.0

        :param name: The name of the setting to set.
        :param value: The value of the setting to set.
        :return: 0 if the action was completed successfully. No return if there is an error.
        """
        # TODO: Deprecate and remove. Tailcall is not needed.
        return self.__setattr__(name, value)

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

    def __setattr__(self, name, value):
        """
        This sets the value of the settings named in the args.

        :param name: The setting to set its value.
        :param value: The value of the setting "name". Must be the correct the type.
        :return: 0 if the action was completed successfully. No return if there is an error.
        :raises AttributeError: Raised if the setting with "name" has the wrong type.
        """
        if name in DEFAULTS:
            try:
                if DEFAULTS[name][1] == "str":
                    value = str(value)
                elif DEFAULTS[name][1] == "int":
                    value = int(value)
                elif DEFAULTS[name][1] == "bool":
                    value = utils.input_boolean(value)
                elif DEFAULTS[name][1] == "float":
                    value = float(value)
                elif DEFAULTS[name][1] == "list":
                    value = utils.input_string_or_list(value)
                elif DEFAULTS[name][1] == "dict":
                    value = utils.input_string_or_dict(value)[1]
            except Exception as error:
                raise AttributeError from error

            self.__dict__[name] = value
            update_settings_file(self.to_dict())

            return 0
        else:
            pass

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
            return self.__dict__[name]
        except Exception as error:
            if name in DEFAULTS:
                lookup = DEFAULTS[name][0]
                self.__dict__[name] = lookup
                return lookup
            else:
                raise AttributeError(f"no settings attribute named '{name}' found") from error


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
    return schema.validate(settings_content)


def parse_bind_config(configpath: str):
    """
    Parse the Bind9 configuration file and adjust the Cobbler default settings according to the readings.

    :param configpath: The path in the filesystem where the file can be read.
    """
    # pylint: disable=global-statement
    global DEFAULTS
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
            DEFAULTS["bind_chroot_path"] = bind_config["ROOTDIR"]
        # Debian, Systemd Fedora
        if "OPTIONS" in bind_config:
            rootdirmatch = re.search(r"-t ([/\w]+)", bind_config["OPTIONS"])
            if rootdirmatch is not None:
                DEFAULTS["bind_chroot_path"] = rootdirmatch.group(1)


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


def __migrate_settingsfile_int_bools(settings_dict: dict) -> dict:
    for key in settings_dict:
        if DEFAULTS[key][1] == "bool":
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
    filecontent = __migrate_settingsfile_int_bools(filecontent)
    try:
        validate_settings(filecontent)
    except SchemaMissingKeyError:
        logging.exception("Settings file was not returned due to missing keys.")
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
