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
from rhpl.translate import _, N_, textdomain, utf8

TESTMODE = False

DEFAULTS = {
    "bootloaders"                 : {
        "standard"                : "/usr/lib/syslinux/pxelinux.0",
        "ia64"                    : "/var/lib/cobbler/elilo-3.6-ia64.efi"
    },
    "default_kickstart"           : "/etc/cobbler/default.ks",
    "default_virt_type"           : "auto",
    "dhcpd_conf"                  : "/etc/dhcpd.conf",
    "dhcpd_bin"                   : "/usr/sbin/dhcpd",
    "dnsmasq_bin"                 : "/usr/sbin/dnsmasq",
    "dnsmasq_conf"                : "/etc/dnsmasq.conf",
    "httpd_bin"                   : "/usr/sbin/httpd",
    "kernel_options"              : {
        "lang"                    : " ",
        "text"                    : None,
        "ksdevice"                : "eth0",
    },
    "manage_dhcp"                 : 0,
    "manage_dhcp_mode"            : "isc",
    "next_server"                 : "127.0.0.1",
    "pxe_just_once"               : 0,
    "server"                      : "127.0.0.1",
    "snippetsdir"                 : "/var/lib/cobbler/snippets",
    "syslog_port"                 : 25150,
    "tftpboot"                    : "/tftpboot",
    "tftpd_bin"                   : "/usr/sbin/in.tftpd",
    "tftpd_conf"                  : "/etc/xinetd.d/tftp",
    "webdir"                      : "/var/www/cobbler",
    "xmlrpc_port"                 : 25151,
    "xmlrpc_rw_enabled"           : 0,
    "xmlrpc_rw_port"              : 25152,
    "yum_core_mirror_from_server" : 0
}


class Settings(serializable.Serializable):

   def filename(self):
       """
       The filename where settings are serialized.
       """
       if TESTMODE:
           return "/var/lib/cobbler/test/settings"
       else:
           return "/var/lib/cobbler/settings"

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

