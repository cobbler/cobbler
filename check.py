# Validates a system is configured for network booting
# 
# Michael DeHaan <mdehaan@redhat.com>

# FUTURE: Apache checking
# FUTURE: Check to see what's running

import os
import sys
import re

from msg import *

class BootCheck:

   def __init__(self, api):
       self.api = api
       self.config = self.api.config
   
   """
   Returns None if there are no errors, otherwise returns a list 
   of things to correct prior to running bootconf 'for real'.
   FIXME: this needs to be more tolerant of non-default paths
   """
   def run(self):
       status = []
       self.check_dhcpd_bin(status)
       self.check_pxelinux_bin(status)
       self.check_tftpd_bin(status)
       self.check_tftpd_dir(status)
       self.check_tftpd_conf(status)
       self.check_dhcpd_conf(status)
       return status

   """
   Check if dhcpd is installed
   """
   def check_dhcpd_bin(self,status):
       if not os.path.exists(self.config.dhcpd_bin):
          status.append(m("no_dhcpd"))

   """
   Check if pxelinux (part of syslinux) is installed
   """
   def check_pxelinux_bin(self,status):
       if not os.path.exists(self.config.pxelinux):
          status.append(m("no_pxelinux"))

   """
   Check if tftpd is installed
   """
   def check_tftpd_bin(self,status):
       if not os.path.exists(self.config.tftpd_bin):
          status.append(m("no_tftpd")) 

   """
   Check if bootconf.conf's tftpboot directory exists
   """
   def check_tftpd_dir(self,status):
       if not os.path.exists(self.config.tftpboot):
          status.append(m("no_dir") % self.config.tftpboot)
   
   """
   Check that bootconf tftpd boot directory matches with tftpd directory
   Check that tftpd is enabled to autostart
   """
   def check_tftpd_conf(self,status):
       if os.path.exists(self.config.tftpd_conf):
          f = open(self.config.tftpd_conf)
          re_1 = re.compile(r'default:.*off')
          re_2 = re.compile(r'disable.*=.*yes')
          found_bootdir = False
          for line in f.readlines():
             if re_1.search(line):
                 status.append(m("chg_attrib") % ('default','on',self.config.tftpd_conf))
             if re_2.search(line):
                 status.append(m("chg_attrib") % ('disable','no',self.config.tftpd_conf))
             if line.find("-s %s" % self.config.tftpboot) != -1:
                 found_bootdir = True
          if not found_bootdir:
              status.append(m("chg_attrib") % ('server_args',"-s %s" % self.config.tftpboot, self.config.tftpd_conf))   
       else:
          status.append(m("no_exist") % self.tftpd_conf)
   
   """
   Check that dhcpd *appears* to be configured for pxe booting.
   We can't assure file correctness
   """
   def check_dhcpd_conf(self,status):
       if os.path.exists(self.config.dhcpd_conf):
           match_next = False
           match_file = False
           f = open(self.config.dhcpd_conf)
           for line in f.readlines():
               if line.find("next-server") != -1: 
                   match_next = True
               if line.find("filename") != -1:
                   match_file = True     
           if not match_next:
              status.append(m("no_line") % (self.config.dhcpd_conf, 'next-server ip-address'))
           if not match_file:
              status.append(m("no_line") % (self.config.dhcpd_conf, 'filename "%s/pxelinux.0";' % self.config.tftpboot))
       else:
           status.append(m("no_exist") % self.config.dhcpd_conf)
       if not os.path.exists(self.config.kernel_root):
          status.append(m("no_dir2") % (self.config.kernel_root, 'kernel_root'))
       if not os.path.exists(self.config.kickstart_root):
          status.append(m("no_dir2") % (self.config.kickstart_root, 'kickstart_root'))


