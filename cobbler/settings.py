"""
Cobbler app-wide settings

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import serializable
import utils
from utils import _

TESTMODE = False

# defaults is to be used if the config file doesn't contain the value
# we need.

DEFAULTS = {
    "allow_duplicate_macs"        : 0,
    "allow_duplicate_ips"         : 0,
    "bind_bin"                    : "/usr/sbin/named",
    "bootloaders"                 : {
        "standard"                : "/usr/lib/syslinux/pxelinux.0",
        "ia64"                    : "/var/lib/cobbler/elilo-3.6-ia64.efi"
    },
    "cobbler_master"              : '',
    "default_kickstart"           : "/etc/cobbler/default.ks",
    "default_virt_bridge"         : "xenbr0",
    "default_virt_type"           : "auto",
    "default_virt_file_size"      : "5",
    "default_virt_ram"            : "512",
    "default_ownership"           : "admin",
    "dhcpd_conf"                  : "/etc/dhcpd.conf",
    "dhcpd_bin"                   : "/usr/sbin/dhcpd",
    "dnsmasq_bin"                 : "/usr/sbin/dnsmasq",
    "dnsmasq_conf"                : "/etc/dnsmasq.conf",
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
    "manage_dhcp"                 : 0,
    "manage_dhcp_mode"            : "isc",
    "manage_dns"                  : 0,
    "manage_forward_zones"        : [],
    "manage_reverse_zones"        : [],
    "named_conf"                  : "/etc/named.conf",
    "next_server"                 : "127.0.0.1",
    "omapi_enabled"		  : 0,
    "omapi_port"		  : 647,
    "omshell_bin"                 : "/usr/bin/omshell",
    "pxe_just_once"               : 0,
    "register_new_installs"       : 0,
    "run_install_triggers"        : 1,
    "server"                      : "127.0.0.1",
    "snippetsdir"                 : "/var/lib/cobbler/snippets",
    "syslog_port"                 : 25150,
    "tftpd_bin"                   : "/usr/sbin/in.tftpd",
    "tftpd_conf"                  : "/etc/xinetd.d/tftp",
    "webdir"                      : "/var/www/cobbler",
    "xmlrpc_port"                 : 25151,
    "xmlrpc_rw_enabled"           : 1,
    "xmlrpc_rw_port"              : 25152,
    "yum_post_install_mirror"     : 1,
    "yumdownloader_flags"         : "--resolve"
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

       self._attributes = datastruct

       return self

   def __getattr__(self,name):
       if self._attributes.has_key(name):
           if name == "kernel_options":
               # backwards compatibility -- convert possible string value to hash
               (success, result) = utils.input_string_or_hash(self._attributes[name], " ")
               self._attributes[name] = result
               return result
           return self._attributes[name]
       elif DEFAULTS.has_key(name):
           lookup = DEFAULTS[name]
           self._attributes[name] = lookup
           return lookup
       else:
           raise AttributeError, name

if __name__ == "__main__":
    # used to save a settings file to /var/lib/cobbler/settings, for purposes of
    # including a new updated settings file in the RPM without remembering how
    # to format lots of YAML.
    import yaml
    print yaml.dump(DEFAULTS)

 
