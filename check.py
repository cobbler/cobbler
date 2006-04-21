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
   

   def run(self):
       """
       Returns None if there are no errors, otherwise returns a list 
       of things to correct prior to running $0 'for real'.
       """
       status = []
       self.check_dhcpd_bin(status)
       self.check_pxelinux_bin(status)
       self.check_tftpd_bin(status)
       self.check_tftpd_dir(status)
       self.check_tftpd_conf(status)
       self.check_dhcpd_conf(status)
       return status


   def check_dhcpd_bin(self,status):
       """
       Check if dhcpd is installed
       """
       if not os.path.exists(self.config.dhcpd_bin):
          status.append(m("no_dhcpd"))

   def check_pxelinux_bin(self,status):
       """
       Check if pxelinux (part of syslinux) is installed
       """
       if not os.path.exists(self.config.pxelinux):
          status.append(m("no_pxelinux"))

   def check_tftpd_bin(self,status):
       """
       Check if tftpd is installed
       """
       if not os.path.exists(self.config.tftpd_bin):
          status.append(m("no_tftpd")) 

   def check_tftpd_dir(self,status):
       """
       Check if cobbler.conf's tftpboot directory exists
       """
       if not os.path.exists(self.config.tftpboot):
          status.append(m("no_dir") % self.config.tftpboot)
   

   def check_tftpd_conf(self,status):
       """
       Check that configured tftpd boot directory matches with actual
       Check that tftpd is enabled to autostart
       """
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
   

   def check_dhcpd_conf(self,status):
       """
       Check that dhcpd *appears* to be configured for pxe booting.
       We can't assure file correctness
       """
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


