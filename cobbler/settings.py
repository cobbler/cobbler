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
    "anamon_enabled"              : [0,"bool"],
    "allow_duplicate_hostnames"   : [0,"bool"],
    "allow_duplicate_macs"        : [0,"bool"],
    "allow_duplicate_ips"         : [0,"bool"],
    "bind_chroot_path"            : ["","str"],
    "bind_master"                 : ["127.0.0.1","str"],
    "build_reporting_enabled"     : [0,"bool"],
    "build_reporting_to_address"  : ["","str"],
    "build_reporting_sender"      : ["","str"],
    "build_reporting_subject"     : ["","str"],
    "build_reporting_smtp_server" : ["localhost","str"],
    "cheetah_import_whitelist"    : [["re", "random", "time"],"list"],
    "cobbler_master"              : ["","str"],
    "default_deployment_method"   : ["ssh","str"],
    "default_kickstart"           : ["/var/lib/cobbler/kickstarts/default.ks","str"],
    "default_name_servers"        : [[],"list"],
    "default_name_servers_search" : [[],"list"],
    "default_password_crypted"    : ["\$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.","str"],
    "default_template_type"       : ["cheetah","str"],
    "default_virt_bridge"         : ["xenbr0","str"],
    "default_virt_type"           : ["auto","str"],
    "default_virt_file_size"      : [5,"int"],
    "default_virt_disk_driver"    : ["raw","str"],
    "default_virt_ram"            : [512,"int"],
    "default_ownership"           : [["admin"],"list"],
    "enable_gpxe"                 : [0,"bool"],
    "enable_menu"                 : [1,"bool"],
    "func_master"                 : ["overlord.example.org","str"],
    "func_auto_setup"             : [0,"bool"],
    "http_port"                   : [80,"int"],
    "isc_set_host_name"           : [0,"bool"],
    "ldap_server"                 : ["grimlock.devel.redhat.com","str"],
    "ldap_base_dn"                : ["DC=devel,DC=redhat,DC=com","str"],
    "ldap_port"                   : [389,"int"],
    "ldap_tls"                    : ["on","str"],
    "ldap_anonymous_bind"         : [1,"bool"],
    "ldap_search_bind_dn"         : ["","str"],
    "ldap_search_passwd"          : ["","str"],
    "ldap_search_prefix"          : ['uid=',"str"],
    "kerberos_realm"              : ["EXAMPLE.COM","str"],
    "kernel_options"              : [{"lang":" ", "text":None, "ksdevice":"eth0"},"dict"],
    "kernel_options_s390x"        : [{},"dict"],
    "manage_dhcp"                 : [0,"bool"],
    "manage_dns"                  : [0,"bool"],
    "manage_tftp"                 : [1,"bool"],
    "manage_tftpd"                : [1,"bool"],
    "manage_rsync"                : [0,"bool"],
    "manage_forward_zones"        : [[],"list"],
    "manage_reverse_zones"        : [[],"list"],
    "mgmt_classes"                : [[],"list"],
    "mgmt_parameters"             : [{},"dict"],
    "next_server"                 : ["127.0.0.1","str"],
    "power_management_default_type" : ["ipmitool","str"],
    "power_template_dir"          : ["/etc/cobbler/power","str"],
    "puppet_auto_setup"           : [0,"bool"],
    "sign_puppet_certs_automatically": [0,"bool"],
    "pxe_just_once"               : [0,"bool"],
    "iso_template_dir"            : ["/etc/cobbler/iso","str"],
    "pxe_template_dir"            : ["/etc/cobbler/pxe","str"],
    "redhat_management_permissive" : [0,"bool"],
    "redhat_management_type"      : ["off","str"],
    "redhat_management_key"       : ["","str"],
    "redhat_management_server"    : ["xmlrpc.rhn.redhat.com","str"],
    "register_new_installs"       : [0,"bool"],
    "restart_dns"                 : [1,"bool"],
    "restart_dhcp"                : [1,"bool"],
    "restart_xinetd"              : [1,"bool"],
    "run_install_triggers"        : [1,"bool"],
    "scm_track_enabled"           : [0,"bool"],
    "scm_track_mode"              : ["git","str"],
    "server"                      : ["127.0.0.1","str"],
    "client_use_localhost"        : ["","str"],
    "snippetsdir"                 : ["/var/lib/cobbler/snippets","str"],
    "template_remote_kickstarts"  : [0,"bool"],
    "virt_auto_boot"              : [0,"bool"],
    "webdir"                      : ["/var/www/cobbler","str"],
    "buildisodir"                 : ["/var/cache/cobbler/buildiso","str"],
    "xmlrpc_port"                 : [25151,"int"],
    "yum_post_install_mirror"     : [1,"bool"],
    "createrepo_flags"            : ["-c cache -s sha","str"],
    "yum_distro_priority"         : [1,"int"],
    "yumdownloader_flags"         : ["--resolve","str"],
    "reposync_flags"              : ["-l -m -d","str"],
    "ldap_management_default_type": ["authconfig","str"],
    "consoles"                    : ["/var/consoles","str"],
}

FIELDS = [
   ["name","","","Name",True,"Ex: server",0,"str"],
   ["value","","","Value",True,"Ex: 127.0.0.1",0,"str"],
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
       self.__dict__ = {}
       for key in DEFAULTS.keys():
           self.__dict__[key] = DEFAULTS[key][0]

   def set(self,name,value):
       return self.__setattr__(name,value)

   def printable(self):
       buf = ""
       buf = buf + _("defaults\n")
       buf = buf + _("kernel options  : %s\n") % self.__dict__['kernel_options']
       return buf

   def to_datastruct(self):
       """
       Return an easily serializable representation of the config.
       """
       return self.__dict__

   def from_datastruct(self,datastruct):
       """
       Modify this object to load values in datastruct.
       """
       if datastruct is None:
          print _("warning: not loading empty structure for %s") % self.filename()
          return
  
       self.clear()
       self.__dict__.update(datastruct)

       return self

   def __setattr__(self,name,value):
       if DEFAULTS.has_key(name):
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
                   value = utils.input_string_or_hash(value)[1]
           except:
               raise AttributeError, "failed to set %s to %s" % (name,str(value))
           
           self.__dict__[name] = value
           utils.update_settings_file(name,value)
           return 0
       else:
           raise AttributeError, name

   def __getattr__(self,name):
       try:
           if name == "kernel_options":
               # backwards compatibility -- convert possible string value to hash
               (success, result) = utils.input_string_or_hash(self.__dict__[name], " ",allow_multiples=False)
               self.__dict__[name] = result
               return result
           return self.__dict__[name]
       except:
           if DEFAULTS.has_key(name):
               lookup = DEFAULTS[name][0]
               self.__dict__[name] = lookup
               return lookup
           else:
               raise AttributeError, name
