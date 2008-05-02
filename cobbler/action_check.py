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
import sub_process
import action_sync
import utils
from utils import _
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
       if self.settings.manage_dhcp:
           mode = self.config.api.get_sync().manager.what()
           if mode == "isc_and_bind": 
               self.check_dhcpd_bin(status)
               self.check_dhcpd_conf(status)
               self.check_service(status,"dhcpd")
           elif mode == "dnsmasq":
               self.check_dnsmasq_bin(status)
               self.check_service(status,"dnsmasq")
           else:
               status.append(_("configured management mode in modules.conf is unknown"))
       # FIXME: add in checks for bind config
       if self.settings.manage_dns:
           mode = self.config.api.get_sync().manager.what()
           if mode == "isc_and_bind":
               self.check_bind_bin(status)
               self.check_service(status,"named")
               pass

       self.check_service(status, "cobblerd")
    
       self.check_bootloaders(status)
       self.check_tftpd_bin(status)
       self.check_tftpd_dir(status)
       self.check_tftpd_conf(status)
       self.check_httpd(status)
       self.check_iptables(status)
       self.check_yum(status)

       return status

   def check_service(self, status, which):
     if utils.check_dist() == "redhat":
        if os.path.exists("/etc/rc.d/init.d/%s" % which):
          rc = sub_process.call("/sbin/service %s status >/dev/null 2>/dev/null" % which, shell=True)
          if rc != 0:
            status.append(_("service %s is not running") % which)
     elif utils.check_dist() == "debian":
        if os.path.exists("/etc/init.d/%s" % which):
	  rc = sub_process.call("/etc/init.d/%s status /dev/null 2>/dev/null" % which, shell=True)
	  if rc != 0:
	    status.append(_("service %s is not running") % which)
     else:
       status.append(_("Unknown distribution type, cannot check for running service %s" % which))

   def check_iptables(self, status):
       if os.path.exists("/etc/rc.d/init.d/iptables"):
           rc = sub_process.call("/sbin/service iptables status >/dev/null 2>/dev/null", shell=True)
           if rc == 0:
              status.append(_("since iptables may be running, ensure 69, 80, %(syslog)s, and %(xmlrpc)s are unblocked") % { "syslog" : self.settings.syslog_port, "xmlrpc" : self.settings.xmlrpc_port })

   def check_yum(self,status):
       if not os.path.exists("/usr/bin/createrepo"):
           status.append(_("createrepo package is not installed, needed for cobbler import and cobbler reposync, install createrepo?"))
       if not os.path.exists("/usr/bin/reposync"):
           status.append(_("reposync is not installed, need for cobbler reposync, install/upgrade yum-utils?"))
       if not os.path.exists("/usr/bin/yumdownloader"):
           status.append(_("yumdownloader is not installed, needed for cobbler repo add with --rpm-list parameter, install/upgrade yum-utils?"))

   def check_name(self,status):
       """
       If the server name in the config file is still set to localhost
       kickstarts run from koan will not have proper kernel line
       parameters.
       """
       if self.settings.server == "127.0.0.1":
          status.append(_("The 'server' field in /var/lib/cobbler/settings must be set to something other than localhost, or kickstarting features will not work.  This should be a resolvable hostname or IP for the boot server as reachable by all machines that will use it."))
       if self.settings.next_server == "127.0.0.1":
          status.append(_("For PXE to be functional, the 'next_server' field in /var/lib/cobbler/settings must be set to something other than 127.0.0.1, and should match the IP of the boot server on the PXE network."))

   def check_httpd(self,status):
       """
       Check if Apache is installed.
       """
       self.check_service(status,"httpd")


   def check_dhcpd_bin(self,status):
       """
       Check if dhcpd is installed
       """
       if not os.path.exists(self.settings.dhcpd_bin):
           status.append(_("dhcpd isn't installed, but management is enabled in /var/lib/cobbler/settings"))

   def check_dnsmasq_bin(self,status):
       """
       Check if dnsmasq is installed
       """
       if not os.path.exists(self.settings.dnsmasq_bin):
           status.append(_("dnsmasq isn't installed, but management is enabled in /var/lib/cobbler/settings"))

   def check_bind_bin(self,status):
       """
       Check if bind is installed.
       """
       if not os.path.exists(self.settings.bind_bin):
           status.append(_("bind isn't installed, but management is enabled in /var/lib/cobbler/settings"))
       

   def check_bootloaders(self,status):
       """
       Check if network bootloaders are installed
       """
       for loader in self.settings.bootloaders.keys():
          filename = self.settings.bootloaders[loader]
          if not os.path.exists(filename):
              if filename.find("pxelinux") != -1:
                 status.append(_("syslinux should be installed but is not, expecting to find something at %s" % filename))
              else:
                 status.append(_("bootloader missing: %s" % filename))
              return

   def check_tftpd_bin(self,status):
       """
       Check if tftpd is installed
       """
       if not os.path.exists(self.settings.tftpd_bin):
          status.append(_("tftp-server is not installed."))
       else:
          self.check_service(status,"xinetd")

   def check_tftpd_dir(self,status):
       """
       Check if cobbler.conf's tftpboot directory exists
       """
       bootloc = utils.tftpboot_location()
       if not os.path.exists(bootloc):
          status.append(_("please create directory: %(dirname)s") % { "dirname" : bootloc })


   def check_tftpd_conf(self,status):
       """
       Check that configured tftpd boot directory matches with actual
       Check that tftpd is enabled to autostart
       """
       if os.path.exists(self.settings.tftpd_conf):
          f = open(self.settings.tftpd_conf)
          re_disable = re.compile(r'disable.*=.*yes')
          for line in f.readlines():
             if re_disable.search(line):
                 status.append(_("change 'disable' to 'no' in %(file)s") % { "file" : self.settings.tftpd_conf })
       else:
          status.append(_("file %(file)s does not exist") % { "file" : self.settings.tftpd_conf })
       
       bootloc = utils.tftpboot_location()
       if not os.path.exists(bootloc):
          status.append(_("directory needs to be created: %s" % bootloc))


   def check_dhcpd_conf(self,status):
       """
       NOTE: this code only applies if cobbler is *NOT* set to generate
       a dhcp.conf file

       Check that dhcpd *appears* to be configured for pxe booting.
       We can't assure file correctness.  Since a cobbler user might
       have dhcp on another server, it's okay if it's not there and/or
       not configured correctly according to automated scans.
       """
       if not (self.settings.manage_dhcp == 0):
           return

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
              status.append(_("expecting next-server entry in %(file)s") % { "file" : self.settings.dhcpd_conf })
           if not match_file:
              status.append(_("missing file: %(file)s") % { "file" : self.settings.dhcpd_conf })
       else:
           status.append(_("missing file: %(file)s") % { "file" : self.settings.dhcpd_conf })


