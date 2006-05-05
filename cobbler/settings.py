import serializable

"""
Cobbler app-wide settings
"""

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
   

   def to_datastruct():
       return self._attributes()

   def from_datastruct(datastruct):
       self._attributes = datastruct   

   def __getattr__(self,name):
       if name in self._attributes:
           return self._attributes[name]
       else:
           raise AttributeError, name

