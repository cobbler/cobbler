"""
Cobbler app-wide settings

Michael DeHaan <mdehaan@redhat.com>
"""

import serializable
import utils

class Settings(serializable.Serializable):

   def filename(self):
       return "/var/lib/cobbler/settings"

   def __init__(self):
       self.clear()

   def clear(self):
       self._attributes = {
          "httpd_bin"      : "/usr/sbin/httpd",
          "pxelinux"       : "/usr/lib/syslinux/pxelinux.0",
          "dhcpd_conf"     : "/etc/dhcpd.conf",
          "tftpd_bin"      : "/usr/sbin/in.tftpd",
          "server"         : "localhost",
          "dhcpd_bin"      : "/usr/sbin/dhcpd",
          "kernel_options" : "append devfs=nomount ramdisk_size=16438 lang= vga=788 ksdevice=eth0",
          "tftpd_conf"     : "/etc/xinetd.d/tftp",
          "tftpboot"       : "/tftpboot",
       }


   def to_datastruct(self):
       return self._attributes

   def from_datastruct(self,datastruct):
       if datastruct is None:
          print "DEBUG: not loading empty structure"
          return
       self._attributes = datastruct
       return self

   # could use getatr, but I'd rather not.
   def __getattr__(self,name):
       if utils.app_debug:
           print "Settings::__getattr__(self,%s)" % name       
       if self._attributes.has_key(name):
           return self._attributes[name]
       else:
           raise AttributeError, name

