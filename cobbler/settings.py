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

import utils
from utils import _

import os.path
import glob
import re
import sys

TESTMODE = False

# defaults is to be used if the config file doesn't contain the value
# we need.

DEFAULTS = {
    "anamon_enabled"              : 0,
    "allow_duplicate_hostnames"   : 0,
    "allow_duplicate_macs"        : 0,
    "allow_duplicate_ips"         : 0,
    "bind_chroot_path"            : "", 
    "bind_master"                 : "127.0.0.1",
    "build_reporting_enabled"     : 0,
    "build_reporting_to_address"  : "",
    "build_reporting_sender"      : "",
    "build_reporting_subject"     : "",
    "build_reporting_smtp_server" : "localhost",
    "cheetah_import_whitelist"    : [ "re", "random", "time" ],
    "cobbler_master"              : '',
    "default_deployment_method"   : "ssh",
    "default_kickstart"           : "/var/lib/cobbler/kickstarts/default.ks",
    "default_name_servers"        : [],
    "default_name_servers_search" : [],
    "default_password_crypted"    : "\$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.",
    "default_template_type"       : "cheetah",
    "default_virt_bridge"         : "xenbr0",
    "default_virt_type"           : "auto",
    "default_virt_file_size"      : "5",
    "default_virt_disk_driver"    : "raw",
    "default_virt_ram"            : "512",
    "default_ownership"           : [ "admin" ],
    "enable_gpxe"                 : 0,
    "enable_menu"                 : 1,
    "func_master"                 : "overlord.example.org",
    "func_auto_setup"             : 0,
    "http_port"                   : "80",
    "isc_set_host_name"           : 0,
    "ldap_server"                 : "grimlock.devel.redhat.com",
    "ldap_base_dn"                : "DC=devel,DC=redhat,DC=com",
    "ldap_port"                   : 389,
    "ldap_tls"                    : "on",
    "ldap_anonymous_bind"         : 1,
    "ldap_search_bind_dn"         : '',
    "ldap_search_passwd"          : '',
    "ldap_search_prefix"          : 'uid=',
    "kerberos_realm"              : "EXAMPLE.COM",
    "kernel_options"              : {
        "lang"                    : " ",
        "text"                    : None,
        "ksdevice"                : "eth0"
    },
    "kernel_options_s390x"        : {},
    "manage_dhcp"                 : 0,
    "manage_dns"                  : 0,
    "manage_tftp"                 : 1,
    "manage_tftpd"                : 1,
    "manage_rsync"                : 0,
    "manage_forward_zones"        : [],
    "manage_reverse_zones"        : [],
    "mgmt_classes"                : [],
    "mgmt_parameters"             : {},
    "next_server"                 : "127.0.0.1",
    "power_management_default_type" : "ipmitool",
    "power_template_dir"          : "/etc/cobbler/power",
    "puppet_auto_setup"           : 0,
    "sign_puppet_certs_automatically": 0,
    "pxe_just_once"               : 0,
    "iso_template_dir"            : "/etc/cobbler/iso",
    "pxe_template_dir"            : "/etc/cobbler/pxe",
    "redhat_management_permissive" : 0,
    "redhat_management_type"      : "off",
    "redhat_management_key"       : "",
    "redhat_management_server"    : "xmlrpc.rhn.redhat.com",
    "register_new_installs"       : 0,
    "restart_dns"                 : 1,
    "restart_dhcp"                : 1,
    "restart_xinetd"              : 1,
    "run_install_triggers"        : 1,
    "scm_track_enabled"           : 0,
    "scm_track_mode"              : "git",
    "server"                      : "127.0.0.1",
    "client_use_localhost"        : "",
    "snippetsdir"                 : "/var/lib/cobbler/snippets",
    "template_remote_kickstarts"  : 0,
    "virt_auto_boot"              : 0,
    "webdir"                      : "/var/www/cobbler",
    "buildisodir"                 : "/var/cache/cobbler/buildiso",
    "xmlrpc_port"                 : 25151,
    "yum_post_install_mirror"     : 1,
    "createrepo_flags"            : "-c cache -s sha",
    "yum_distro_priority"         : 1,
    "yumdownloader_flags"         : "--resolve",
    "reposync_flags"              : "-l -m -d",
    "ldap_management_default_type": "authconfig",
    "consoles"                     : "/var/consoles"
}

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
        bind_config_file = open(bind_config_filename,"r")
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
       self.clear()

   def clear(self):
       """
       Reset this object to reasonable default values.
       """
       self._attributes = DEFAULTS

   def printable(self):
       buf = ""
       buf = buf + _("defaults\n")
       buf = buf + _("kernel options  : %s\n") % self._attributes['kernel_options']
       return buf

   def to_datastruct(self):
       """
       Return an easily serializable representation of the config.
       """
       return self._attributes

   def from_datastruct(self,datastruct):
       """
       Modify this object to load values in datastruct.
       """
       if datastruct is None:
          print _("warning: not loading empty structure for %s") % self.filename()
          return
  
       self._attributes = DEFAULTS
       self._attributes.update(datastruct)

       return self

   def __getattr__(self,name):
       if self._attributes.has_key(name):
           if name == "kernel_options":
               # backwards compatibility -- convert possible string value to hash
               (success, result) = utils.input_string_or_hash(self._attributes[name], " ",allow_multiples=False)
               self._attributes[name] = result
               return result
           return self._attributes[name]
       elif DEFAULTS.has_key(name):
           lookup = DEFAULTS[name]
           self._attributes[name] = lookup
           return lookup
       else:
           raise AttributeError, name

