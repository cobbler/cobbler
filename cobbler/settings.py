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

import utils
from utils import _

TESTMODE = False

# defaults is to be used if the config file doesn't contain the value
# we need.

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
    "build_reporting_enabled": [0, "bool"],
    "build_reporting_ignorelist": ["", "str"],
    "build_reporting_sender": ["", "str"],
    "build_reporting_sender": ["", "str"],
    "build_reporting_smtp_server": ["localhost", "str"],
    "build_reporting_subject": ["", "str"],
    "buildisodir": ["/var/cache/cobbler/buildiso", "str"],
    "cheetah_import_whitelist": [["re", "random", "time"], "list"],
    "client_use_https": [0, "bool"],
    "client_use_localhost": [0, "bool"],
    "cobbler_master": ["", "str"],
    "createrepo_flags": ["-c cache -s sha", "str"],
    "default_autoinstall": ["/var/lib/cobbler/templates/default.ks", "str"],
    "default_name_servers": [[], "list"],
    "default_name_servers_search": [[], "list"],
    "default_ownership": [["admin"], "list"],
    "default_password_crypted": ["\$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.", "str"],
    "default_template_type": ["cheetah", "str"],
    "default_virt_bridge": ["xenbr0", "str"],
    "default_virt_disk_driver": ["raw", "str"],
    "default_virt_file_size": [5, "int"],
    "default_virt_ram": [512, "int"],
    "default_virt_type": ["auto", "str"],
    "enable_gpxe": [0, "bool"],
    "enable_menu": [1, "bool"],
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
    "manage_dhcp": [0, "bool"],
    "manage_dns": [0, "bool"],
    "manage_forward_zones": [[], "list"],
    "manage_reverse_zones": [[], "list"],
    "manage_rsync": [0, "bool"],
    "manage_tftp": [1, "bool"],
    "manage_tftpd": [1, "bool"],
    "mgmt_classes": [[], "list"],
    "mgmt_parameters": [{}, "dict"],
    "next_server": ["127.0.0.1", "str"],
    "power_management_default_type": ["ipmitool", "str"],
    "power_template_dir": ["/etc/cobbler/power", "str"],
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
    "register_new_installs": [0, "bool"],
    "remove_old_puppet_certs_automatically": [0, "bool"],
    "replicate_repo_rsync_options": ["-avzH", "str"],
    "replicate_rsync_options": ["-avzH", "str"],
    "reposync_flags": ["-l -m -d", "str"],
    "restart_dhcp": [1, "bool"],
    "restart_dns": [1, "bool"],
    "restart_xinetd": [1, "bool"],
    "run_install_triggers": [1, "bool"],
    "scm_track_enabled": [0, "bool"],
    "scm_track_mode": ["git", "str"],
    "scm_track_author": ["cobbler <cobbler@localhost>", "str"],
    "scm_push_scripts": ["/bin/true", "str"],
    "serializer_pretty_json": [0, "bool"],
    "server": ["127.0.0.1", "str"],
    "sign_puppet_certs_automatically": [0, "bool"],
    "signature_path": ["/var/lib/cobbler/distro_signatures.json", "str"],
    "signature_url": ["http://cobbler.github.io/signatures/3.0.x/latest.json", "str"],
    "virt_auto_boot": [0, "bool"],
    "webdir": ["/var/www/cobbler", "str"],
    "webdir_whitelist": [".link_cache", "aux", "distro_mirror", "images", "links", "localmirror", "pub", "rendered", "repo_mirror", "repo_profile", "repo_system", "svc", "web", "webui"],
    "xmlrpc_port": [25151, "int"],
    "yum_distro_priority": [1, "int"],
    "yum_post_install_mirror": [1, "bool"],
    "yumdownloader_flags": ["--resolve", "str"],
}

FIELDS = [
    ["name", "", "", "Name", True, "Ex: server", 0, "str"],
    ["value", "", "", "Value", True, "Ex: 127.0.0.1", 0, "str"],
]

if os.path.exists("/srv/www/"):
    DEFAULTS["webdir"] = "/srv/www/cobbler"

# Autodetect bind chroot configuration
# RHEL/Fedora
if os.path.exists("/etc/sysconfig/named"):
    bind_config_filename = "/etc/sysconfig/named"
# Debian
else:
    bind_config_filename = None
    bind_config_files = glob.glob("/etc/default/bind*")
    for filename in bind_config_files:
        if os.path.exists(filename):
            bind_config_filename = filename
# Parse the config file
if bind_config_filename:
    bind_config = {}
    # When running as a webapp we can't access this, but don't need it
    try:
        bind_config_file = open(bind_config_filename, "r")
    except (IOError, OSError):
        pass
    else:
        for line in bind_config_file:
            if re.match("[a-zA-Z]+=", line):
                (name, value) = line.rstrip().split("=")
                bind_config[name] = value.strip('"')
        # RHEL, SysV Fedora
        if "ROOTDIR" in bind_config:
            DEFAULTS["bind_chroot_path"] = bind_config["ROOTDIR"]
        # Debian, Systemd Fedora
        if "OPTIONS" in bind_config:
            rootdirmatch = re.search("-t ([/\w]+)", bind_config["OPTIONS"])
            if rootdirmatch is not None:
                DEFAULTS["bind_chroot_path"] = rootdirmatch.group(1)


class Settings:

    def collection_type(self):
        return "settings"

    def __init__(self):
        """
        Constructor.
        """
        self._clear()

    def _clear(self):
        self.__dict__ = {}
        for key in DEFAULTS.keys():
            self.__dict__[key] = DEFAULTS[key][0]

    def set(self, name, value):
        return self.__setattr__(name, value)

    def to_string(self):
        buf = ""
        buf += _("defaults\n")
        buf += _("kernel options  : %s\n") % self.__dict__['kernel_options']
        return buf

    def to_dict(self):
        """
        Return an easily serializable representation of the config.
        """
        return self.__dict__

    def from_dict(self, _dict):
        """
        Modify this object to load values in dictionary.
        """
        if _dict is None:
            print _("warning: not loading empty structure for %s") % self.filename()
            return

        self._clear()
        self.__dict__.update(_dict)

        return self

    def __setattr__(self, name, value):
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
            if not utils.update_settings_file(self.to_dict()):
                raise AttributeError

            return 0
        else:
            raise AttributeError

    def __getattr__(self, name):
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
                raise AttributeError
