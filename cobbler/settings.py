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

class Settings(serializable.Serializable):

   def filename(self):
       """
       The filename where settings are serialized.
       """
       return "/var/lib/cobbler/settings"

   def __init__(self):
       """
       Constructor.
       """
       self.clear()

   def clear(self):
       """
       Reset this object to reasonable default values.
       """
       self._attributes = {
          "httpd_bin"      : "/usr/sbin/httpd",
          "dhcpd_conf"     : "/etc/dhcpd.conf",
          "tftpd_bin"      : "/usr/sbin/in.tftpd",
          "server"         : "localhost",
          "dhcpd_bin"      : "/usr/sbin/dhcpd",
          "kernel_options" : "append devfs=nomount ramdisk_size=16438 lang= vga=788 ksdevice=eth0",
          "tftpd_conf"     : "/etc/xinetd.d/tftp",
          "tftpboot"       : "/tftpboot",
          "webdir"         : "/var/www/cobbler",
          "manage_dhcp"    : 0,
          "pxelinuxes"     : {
              "i386"   : "/usr/lib/syslinux/pxelinux.0"
              "ia64"   : "/no/path/to/this/file/pxelinux.0"
          }
       }

   def printable(self):
       buf = ""
       buf = buf + "defaults\n"
       buf = buf + "kernel options  : %s\n" % self._attributes['kernel_options']
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
          print "warning: not loading empty structure for %s" % self.filename()
          return
       self._attributes = datastruct
       return self

   def __getattr__(self,name):
       if self._attributes.has_key(name):
           return self._attributes[name]
       else:
           raise AttributeError, name

