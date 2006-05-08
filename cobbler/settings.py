"""
Cobbler app-wide settings

Michael DeHaan <mdehaan@redhat.com>
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

