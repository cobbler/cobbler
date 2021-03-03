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
import os.path
import re
import traceback
from typing import Union, Dict, Hashable, Any

import yaml

from cobbler import utils
from cobbler.cexceptions import CX


# defaults is to be used if the config file doesn't contain the value we need
DEFAULTS = {
    "allow_duplicate_hostnames": [0, "bool"],
    "allow_duplicate_ips": [0, "bool"],
    "allow_duplicate_macs": [0, "bool"],
    "allow_dynamic_settings": [0, "bool"],
    "always_write_dhcp_entries": [0, "bool"],
    "anamon_enabled": [0, "bool"],
    "auth_token_expiration": [3600, "int"],
    "authn_pam_service": ["login", "str"],
    "autoinstall_snippets_dir": ["/var/lib/cobbler/snippets", "str"],
    "autoinstall_templates_dir": ["/var/lib/cobbler/templates", "str"],
    "bind_chroot_path": ["", "str"],
    "bind_master": ["127.0.0.1", "str"],
    "boot_loader_conf_template_dir": ["/etc/cobbler/boot_loader_conf", "str"],
    "bootloaders_dir": ["/var/lib/cobbler/loaders", "str"],
    "grubconfig_dir": ["/var/lib/cobbler/grub_config", "str"],
    "build_reporting_enabled": [0, "bool"],
    "build_reporting_ignorelist": ["", "str"],
    "build_reporting_sender": ["", "str"],
    "build_reporting_smtp_server": ["localhost", "str"],
    "build_reporting_subject": ["", "str"],
    "buildisodir": ["/var/cache/cobbler/buildiso", "str"],
    "cache_enabled": [1, "bool"],
    "cheetah_import_whitelist": [["re", "random", "time"], "list"],
    "client_use_https": [0, "bool"],
    "client_use_localhost": [0, "bool"],
    "cobbler_master": ["", "str"],
    "convert_server_to_ip": [0, "bool"],
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
    "enable_ipxe": [False, "bool"],
    "enable_menu": [True, "bool"],
    "http_port": [80, "int"],
    "include": [["/etc/cobbler/settings.d/*.settings"], "list"],
    "iso_template_dir": ["/etc/cobbler/iso", "str"],
    "kernel_options": [{}, "dict"],
    "ldap_anonymous_bind": [1, "bool"],
    "ldap_base_dn": ["DC=devel,DC=redhat,DC=com", "str"],
    "ldap_port": [389, "int"],
    "ldap_search_bind_dn": ["", "str"],
    "ldap_search_passwd": ["", "str"],
    "ldap_search_prefix": ['uid=', "str"],
    "ldap_server": ["grimlock.devel.redhat.com", "str"],
    "ldap_tls": ["on", "str"],
    "ldap_tls_cacertfile": ["", "str"],
    "ldap_tls_certfile": ["", "str"],
    "ldap_tls_keyfile": ["", "str"],
    "bind_manage_ipmi": [0, "bool"],
    "manage_dhcp": [0, "bool"],
    "manage_dns": [0, "bool"],
    "manage_forward_zones": [[], "list"],
    "manage_reverse_zones": [[], "list"],
    "manage_genders": [0, "bool"],
    "manage_rsync": [0, "bool"],
    "manage_tftp": [1, "bool"],
    "manage_tftpd": [1, "bool"],
    "mgmt_classes": [[], "list"],
    "mgmt_parameters": [{}, "dict"],
    "next_server": ["127.0.0.1", "str"],
    "nsupdate_enabled": [0, "bool"],
    "power_management_default_type": ["ipmitool", "str"],
    "proxy_url_ext": ["", "str"],
    "proxy_url_int": ["", "str"],
    "puppet_auto_setup": [0, "bool"],
    "puppet_parameterized_classes": [1, "bool"],
    "puppet_server": ["puppet", "str"],
    "puppet_version": [2, "int"],
    "puppetca_path": ["/usr/bin/puppet", "str"],
    "pxe_just_once": [1, "bool"],
    "nopxe_with_triggers": [1, "bool"],
    "redhat_management_permissive": [0, "bool"],
    "redhat_management_server": ["xmlrpc.rhn.redhat.com", "str"],
    "redhat_management_key": ["", "str"],
    "register_new_installs": [0, "bool"],
    "remove_old_puppet_certs_automatically": [0, "bool"],
    "replicate_repo_rsync_options": ["-avzH", "str"],
    "replicate_rsync_options": ["-avzH", "str"],
    "reposync_flags": ["-l -m -d", "str"],
    "restart_dhcp": [1, "bool"],
    "restart_dns": [1, "bool"],
    "run_install_triggers": [1, "bool"],
    "scm_track_enabled": [0, "bool"],
    "scm_track_mode": ["git", "str"],
    "scm_track_author": ["cobbler <cobbler@localhost>", "str"],
    "scm_push_script": ["/bin/true", "str"],
    "serializer_pretty_json": [0, "bool"],
    "server": ["127.0.0.1", "str"],
    "sign_puppet_certs_automatically": [0, "bool"],
    "signature_path": ["/var/lib/cobbler/distro_signatures.json", "str"],
    "signature_url": ["https://cobbler.github.io/signatures/3.0.x/latest.json", "str"],
    "tftpboot_location": ["/var/lib/tftpboot", "str"],
    "virt_auto_boot": [0, "bool"],
    "webdir": ["/var/www/cobbler", "str"],
    "webdir_whitelist": [".link_cache", "misc", "distro_mirror", "images", "links", "localmirror", "pub", "rendered",
                         "repo_mirror", "repo_profile", "repo_system", "svc", "web", "webui"],
    "xmlrpc_port": [25151, "int"],
    "yum_distro_priority": [1, "int"],
    "yum_post_install_mirror": [1, "bool"],
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
        self._clear()

    def _clear(self):
        """
        This resets all settings to the defaults which are built into Cobbler.
        """
        self.__dict__ = {}
        for key in list(DEFAULTS.keys()):
            self.__dict__[key] = DEFAULTS[key][0]

    def set(self, name, value):
        """
        Alias for setting an option "name" to the new value "value". (See __settattr__)

        :param name: The name of the setting to set.
        :param value: The value of the setting to set.
        :return: 0 if the action was completed successfully. No return if there is an error.
        """
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

        :return: The dict with all user settings combined with settings which are left to the default.
        """
        return self.__dict__

    def from_dict(self, _dict):
        """
        Modify this object to load values in dictionary.

        WARNING: If the dict from the args has not all settings included Cobbler may behave unexpectedly.

        :param _dict: The dictionary with settings to replace.
        :return: Returns the settings instance this method was called from.
        """
        if _dict is None:
            print("warning: not loading empty structure for %s" % self.filename())
            return

        self._clear()
        self.__dict__.update(_dict)

        return self

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
                    if utils.input_boolean(value):
                        value = 1
                    else:
                        value = 0
                elif DEFAULTS[name][1] == "float":
                    value = float(value)
                elif DEFAULTS[name][1] == "list":
                    value = utils.input_string_or_list(value)
                elif DEFAULTS[name][1] == "dict":
                    value = utils.input_string_or_dict(value)[1]
            except:
                raise AttributeError

            self.__dict__[name] = value
            update_settings_file(self.to_dict())

            return 0
        else:
            # FIXME. Not sure why __dict__ is part of name workaround applied, ignore exception
            # raise AttributeError
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
        except:
            if name in DEFAULTS:
                lookup = DEFAULTS[name][0]
                self.__dict__[name] = lookup
                return lookup
            else:
                raise AttributeError(f"no settings attribute named '{name}' found")


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


def autodect_bind_chroot():
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


def __migrate_settingsfile_name():
    if os.path.exists("/etc/cobbler/settings"):
        os.rename("/etc/cobbler/settings", "/etc/cobbler/settings.yaml")


def read_settings_file(filepath="/etc/cobbler/settings.yaml") -> Union[Dict[Hashable, Any], list, None]:
    """
    Reads the settings file from the default location or the given one. This method then also recursively includes all
    files in the ``include`` directory. Any key may be overwritten in a later loaded settings file. The last loaded file
    wins.

    :param filepath: The path to the settings file.
    :return: A dictionary with the settings. As a word of caution: This may not represent a correct settings object, it
             will only contain a correct YAML representation.
    :raises CX: If the YAML file is not syntactically valid or could not be read.
    :raises FileNotFoundError: If the file handed to the function does not exist.
    """
    __migrate_settingsfile_name()
    if not os.path.exists(filepath):
        raise FileNotFoundError("Given path \"%s\" does not exist." % filepath)
    try:
        with open(filepath) as main_settingsfile:
            filecontent = yaml.safe_load(main_settingsfile.read())

            for ival in filecontent.get("include", []):
                for ifile in glob.glob(ival):
                    with open(ifile, 'r') as extra_settingsfile:
                        filecontent.update(yaml.safe_load(extra_settingsfile.read()))
    except yaml.YAMLError as e:
        traceback.print_exc()
        raise CX("\"%s\" is not a valid YAML file" % filepath) from e
    return filecontent


def update_settings_file(data, filepath="/etc/cobbler/settings.yaml"):
    """
    Write data handed to this function into the settings file of Cobbler. This function overwrites the existing content.

    :param data: The data to put into the settings file.
    :param filepath: This sets the path of the settingsfile to write.
    :return: True if the action succeeded. Otherwise return nothing.
    """
    __migrate_settingsfile_name()
    with open(filepath, "w") as settings_file:
        yaml.safe_dump(data, settings_file)


# Initialize Settings module for manipulating the global DEFAULTS variable
autodect_bind_chroot()
