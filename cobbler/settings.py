"""
Cobbler app-wide settings

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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

import serializable
import utils
from utils import _

TESTMODE = False

# defaults is to be used if the config file doesn't contain the value
# we need.

DEFAULTS = {
    "anamon_enabled"              : 0,
    "allow_duplicate_hostnames"   : 0,
    "allow_duplicate_macs"        : 0,
    "allow_duplicate_ips"         : 0,
    "bind_bin"                    : "/usr/sbin/named",
    "build_reporting_enabled"     : 0,
    "build_reporting_to_address"  : "",
    "build_reporting_sender"      : "",
    "build_reporting_subject"     : "",
    "build_reporting_smtp_server" : "localhost",
    "cheetah_import_whitelist"    : [ "re", "random", "time" ],
    "cobbler_master"              : '',
    "default_kickstart"           : "/var/lib/cobbler/kickstarts/default.ks",
    "default_name_servers"        : '',
    "default_name_servers_search" : '',
    "default_password_crypted"    : "\$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.",
    "default_virt_bridge"         : "xenbr0",
    "default_virt_type"           : "auto",
    "default_virt_file_size"      : "5",
    "default_virt_ram"            : "512",
    "default_ownership"           : [ "admin" ],
    "dhcpd_conf"                  : "/etc/dhcpd.conf",
    "dhcpd_bin"                   : "/usr/sbin/dhcpd",
    "dnsmasq_bin"                 : "/usr/sbin/dnsmasq",
    "dnsmasq_conf"                : "/etc/dnsmasq.conf",
    "enable_menu"                 : 1,
    "func_master"                 : "overlord.example.org",
    "func_auto_setup"             : 0,
    "httpd_bin"                   : "/usr/sbin/httpd",
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
    "manage_ris_linuxd"           : 0,
    "manage_xinetd"               : 0,
    "manage_forward_zones"        : [],
    "manage_reverse_zones"        : [],
    "mgmt_classes"                : [],
    "mgmt_parameters"             : {},
    "named_conf"                  : "/etc/named.conf",
    "next_server"                 : "127.0.0.1",
    "omapi_enabled"		  : 0,
    "omapi_port"		  : 647,
    "omshell_bin"                 : "/usr/bin/omshell",
    "power_management_default_type" : "ipmitool",
    "power_template_dir"          : "/etc/cobbler/power",
    "pxe_just_once"               : 0,
    "pxe_template_dir"            : "/etc/cobbler/pxe",
    "redhat_management_permissive" : 0,
    "redhat_management_type"      : "off",
    "redhat_management_key"       : "",
    "redhat_management_server"    : "xmlrpc.rhn.redhat.com",
    "register_new_installs"       : 0,
    "restart_dns"                 : 1,
    "restart_dhcp"                : 1,
    "restart_ris_linuxd"          : 1,
    "restart_xinetd"              : 1,
    "ris_linuxd_dir"              : "/tftpboot/drivers",
    "ris_linuxd_flags"            : "",
    "run_install_triggers"        : 1,
    "scm_track_enabled"           : 0,
    "scm_track_mode"              : "git",
    "server"                      : "127.0.0.1",
    "snippetsdir"                 : "/var/lib/cobbler/snippets",
    "tftpd_bin"                   : "/usr/sbin/in.tftpd",
    "tftpd_conf"                  : "/etc/xinetd.d/tftp",
    "tftpd_rules"                 : "/var/lib/cobbler/cobbler-tftpd.rules",
    "vsftpd_bin"                  : "/usr/sbin/vsftpd",
    "webdir"                      : "/var/www/cobbler",
    "xmlrpc_port"                 : 25151,
    "yum_post_install_mirror"     : 1,
    "yumdownloader_flags"         : "--resolve",
    "yumreposync_flags"           : "-l"
}


class Settings(serializable.Serializable):

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

