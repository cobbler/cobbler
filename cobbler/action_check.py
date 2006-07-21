"""
Validates whether the system is reasonably well configured for
serving up content.  This is the code behind 'cobbler check'.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import re
import cobbler_msg

class BootCheck:

   def __init__(self,config):
       """
       Constructor
       """
       self.config   = config
       self.settings = config.settings()

   def run(self):
       """
       Returns None if there are no errors, otherwise returns a list
       of things to correct prior to running application 'for real'.
       (The CLI usage is "cobbler check" before "cobbler sync")
       """
       status = []
       self.check_name(status)
       self.check_dhcpd_bin(status)
       self.check_pxelinux_bin(status)
       self.check_tftpd_bin(status)
       self.check_tftpd_dir(status)
       self.check_tftpd_conf(status)
       self.check_dhcpd_conf(status)
       self.check_httpd(status)
       return status

   def check_name(self,status):
       """
       If the server name in the config file is still set to localhost
       kickstarts run from koan will not have proper kernel line
       parameters.
       """
       if self.settings.server == "localhost":
          status.append(cobbler_msg.lookup("bad_server"))

   def check_httpd(self,status):
       """
       Check if Apache is installed.
       """
       if not os.path.exists(self.settings.httpd_bin):
          status.append(cobbler_msg.lookup("no_httpd"))


   def check_dhcpd_bin(self,status):
       """
       Check if dhcpd is installed
       """
       if not os.path.exists(self.settings.dhcpd_bin):
          status.append(cobbler_msg.lookup("no_dhcpd"))

   def check_pxelinux_bin(self,status):
       """
       Check if pxelinux (part of syslinux) is installed
       """
       if not os.path.exists(self.settings.pxelinux):
          status.append(cobbler_msg.lookup("no_pxelinux"))

   def check_tftpd_bin(self,status):
       """
       Check if tftpd is installed
       """
       if not os.path.exists(self.settings.tftpd_bin):
          status.append(cobbler_msg.lookup("no_tftpd"))

   def check_tftpd_dir(self,status):
       """
       Check if cobbler.conf's tftpboot directory exists
       """
       if not os.path.exists(self.settings.tftpboot):
          status.append(cobbler_msg.lookup("no_dir") % self.settings.tftpboot)


   def check_tftpd_conf(self,status):
       """
       Check that configured tftpd boot directory matches with actual
       Check that tftpd is enabled to autostart
       """
       if os.path.exists(self.settings.tftpd_conf):
          f = open(self.settings.tftpd_conf)
          re_disable = re.compile(r'disable.*=.*yes')
          found_bootdir = False
          for line in f.readlines():
             if re_disable.search(line):
                 status.append(cobbler_msg.lookup("chg_attrib") % ('disable','no',self.settings.tftpd_conf))
             if line.find("-s %s" % self.settings.tftpboot) != -1:
                 found_bootdir = True
          if not found_bootdir:
              status.append(cobbler_msg.lookup("chg_attrib") % ('server_args',"-s %s" % self.settings.tftpboot, self.settings.tftpd_conf))
       else:
          status.append(cobbler_msg.lookup("no_exist") % self.settings.tftpd_conf)


   def check_dhcpd_conf(self,status):
       """
       Check that dhcpd *appears* to be configured for pxe booting.
       We can't assure file correctness.  Since a cobbler user might
       have dhcp on another server, it's okay if it's not there and/or
       not configured correctly according to automated scans.
       """
       if os.path.exists(self.settings.dhcpd_conf):
           match_next = False
           match_file = False
           f = open(self.settings.dhcpd_conf)
           for line in f.readlines():
               if line.find("next-server") != -1:
                   match_next = True
               if line.find("filename") != -1:
                   match_file = True
           if not match_next:
              status.append(cobbler_msg.lookup("no_line") % (self.settings.dhcpd_conf, 'next-server ip-address'))
           if not match_file:
              status.append(cobbler_msg.lookup("no_line") % (self.settings.dhcpd_conf, 'filename "%s/pxelinux.0";' % self.settings.tftpboot))
       else:
           status.append(cobbler_msg.lookup("no_exist") % self.settings.dhcpd_conf)


