"""
Validates whether the system is reasonably well configured for
serving up content.  This is the code behind 'cobbler check'.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
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
       self.checked_dist = utils.check_dist()
       self.check_name(status)
       self.check_selinux(status)
       if self.settings.manage_dhcp:
           mode = self.config.api.get_sync().dhcp.what()
           if mode == "isc": 
               self.check_dhcpd_bin(status)
               self.check_dhcpd_conf(status)
               self.check_service(status,"dhcpd")
           elif mode == "dnsmasq":
               self.check_dnsmasq_bin(status)
               self.check_service(status,"dnsmasq")

       if self.settings.manage_dns:
           mode = self.config.api.get_sync().dns.what()
           if mode == "bind":
               self.check_bind_bin(status)
               self.check_service(status,"named")
           elif mode == "dnsmasq" and not self.settings.manage_dhcp:
               self.check_dnsmasq_bin(status)
               self.check_service(status,"dnsmasq")

       self.check_service(status, "cobblerd")
    
       # self.check_bootloaders(status)
       self.check_tftpd_bin(status)
       self.check_tftpd_dir(status)
       self.check_tftpd_conf(status)
       self.check_httpd(status)
       self.check_iptables(status)
       self.check_yum(status)
       self.check_for_default_password(status)
       self.check_for_unreferenced_repos(status)
       self.check_for_unsynced_repos(status)
       
       # comment out until s390 virtual PXE is fully supported
       # self.check_vsftpd_bin(status)

       self.check_for_cman(status)

       return status

   def check_for_cman(self, status):
       # not doing rpm -q here to be cross-distro friendly
       if not os.path.exists("/sbin/fence_ilo"):
           status.append("fencing tools were not found, and are required to use the (optional) power management features. install cman to use them")
       return True

   def check_service(self, status, which, notes=""):
       if notes != "":
           notes = " (NOTE: %s)" % notes
       rc = 0
       if self.checked_dist == "redhat" or self.checked_dist == "suse":
           if os.path.exists("/etc/rc.d/init.d/%s" % which):
               rc = sub_process.call("/sbin/service %s status > /dev/null 2>/dev/null" % which, shell=True, close_fds=True)
           if rc != 0:
               status.append(_("service %s is not running%s") % (which,notes))
               return False
       elif self.checked_dist == "debian":
           if os.path.exists("/etc/init.d/%s" % which):
	       rc = sub_process.call("/etc/init.d/%s status /dev/null 2>/dev/null" % which, shell=True, close_fds=True)
	   if rc != 0:
	       status.append(_("service %s is not running%s") % which,notes)
               return False
       else:
           status.append(_("Unknown distribution type, cannot check for running service %s" % which))
           return False
       return True

   def check_iptables(self, status):
       if os.path.exists("/etc/rc.d/init.d/iptables"):
           rc = sub_process.call("/sbin/service iptables status >/dev/null 2>/dev/null", shell=True, close_fds=True)
           if rc == 0:
              status.append(_("since iptables may be running, ensure 69, 80, and %(xmlrpc)s are unblocked") % { "xmlrpc" : self.settings.xmlrpc_port })

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
          status.append(_("The 'server' field in /etc/cobbler/settings must be set to something other than localhost, or kickstarting features will not work.  This should be a resolvable hostname or IP for the boot server as reachable by all machines that will use it."))
       if self.settings.next_server == "127.0.0.1":
          status.append(_("For PXE to be functional, the 'next_server' field in /etc/cobbler/settings must be set to something other than 127.0.0.1, and should match the IP of the boot server on the PXE network."))

   def check_selinux(self,status):
       enabled = self.config.api.is_selinux_enabled()
       if enabled:
           prc2 = sub_process.Popen("/usr/sbin/getsebool -a",shell=True,stdout=sub_process.PIPE, close_fds=True)
           data2 = prc2.communicate()[0]
           for line in data2.split("\n"):
              if line.find("httpd_can_network_connect ") != -1:
                  if line.find("off") != -1:
                      status.append(_("Must enable selinux boolean to enable Apache and web services components, run: setsebool -P httpd_can_network_connect true"))
           data3 = sub_process.Popen("/usr/sbin/semanage fcontext -l | grep public_content_t",shell=True,stdout=sub_process.PIPE).communicate()[0]

           rule1 = False
           rule2 = False
           rule3 = False
           selinux_msg = "/usr/sbin/semanage fcontext -a -t public_content_t \"%s\""
           for line in data3.split("\n"):
               if line.startswith("/tftpboot/.*") and line.find("public_content_t") != -1:
                   rule1 = True
               if line.startswith("/var/lib/tftpboot/.*") and line.find("public_content_t") != -1:
                   rule2 = True
               if line.startswith("/var/www/cobbler/images/.*") and line.find("public_content_t") != -1:
                   rule3 = True

           rules = []
           if not os.path.exists("/tftpboot") and not rule1:
               rules.append(selinux_msg % "/tftpboot/.*")
           else:
               if not rule2:
                   rules.append(selinux_msg % "/var/lib/tftpboot/.*")
           if not rule3:
               rules.append(selinux_msg % "/var/www/cobbler/images/.*")
           if len(rules) > 0:
               status.append("you need to set some SELinux content rules to ensure cobbler works correctly in your SELinux environment, run the following: %s" % " && ".join(rules))

   def check_for_default_password(self,status):
       default_pass = self.settings.default_password_crypted
       if default_pass == "\$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.":
           status.append(_("The default password used by the sample templates for newly installed machines (default_password_crypted in /etc/cobbler/settings) is still set to 'cobbler' and should be changed"))


   def check_for_unreferenced_repos(self,status):
        repos = []
        referenced = []
        not_found = []
        for r in self.config.api.repos():
            repos.append(r.name)
        for p in self.config.api.profiles():
            my_repos = p.repos
            if my_repos != "<<inherit>>":
                referenced.extend(my_repos)
        for r in referenced:
            if r not in repos and r != "<<inherit>>":
                not_found.append(r)
        if len(not_found) > 0:
            status.append(_("One or more repos referenced by profile objects is no longer defined in cobbler: %s") % ", ".join(not_found))
       
   def check_for_unsynced_repos(self,status):
       need_sync = []
       for r in self.config.repos():
           if r.mirror_locally == 1:
               lookfor = os.path.join(self.settings.webdir, "repo_mirror", r.name)
               if not os.path.exists(lookfor):
                   need_sync.append(r.name)
       if len(need_sync) > 0:
           status.append(_("One or more repos need to be processed by cobbler reposync for the first time before kickstarting against them: %s") % ", ".join(need_sync))


   def check_httpd(self,status):
       """
       Check if Apache is installed.
       """
       if self.checked_dist == "suse":
           self.check_service(status,"apache2")
       else:
           self.check_service(status,"httpd")

   def check_dhcpd_bin(self,status):
       """
       Check if dhcpd is installed
       """
       if not os.path.exists(self.settings.dhcpd_bin):
           status.append(_("dhcpd isn't installed, but management is enabled in /etc/cobbler/settings"))

   def check_dnsmasq_bin(self,status):
       """
       Check if dnsmasq is installed
       """
       if not os.path.exists(self.settings.dnsmasq_bin):
           status.append(_("dnsmasq isn't installed, but management is enabled in /etc/cobbler/settings"))

   def check_bind_bin(self,status):
       """
       Check if bind is installed.
       """
       if not os.path.exists(self.settings.bind_bin):
           status.append(_("bind isn't installed, but management is enabled in /etc/cobbler/settings"))
       

   # FIXME: removed as we no longer source bootloaders from settings, it's now done
   # directly in pxegen.py -- do we want some checks here though?  

   #def check_bootloaders(self,status):
   #    """
   #    Check if network bootloaders are installed
   #    """
   #    for loader in self.settings.bootloaders.keys():
   #       filename = self.settings.bootloaders[loader]
   #       if not os.path.exists(filename):
   #           if filename.find("pxelinux") != -1:
   #              status.append(_("syslinux should be installed but is not, expecting to find something at %s" % filename))
   #           else:
   #              status.append(_("bootloader missing: %s" % filename))
   #           return

   def check_tftpd_bin(self,status):
       """
       Check if tftpd is installed
       """
       if not os.path.exists(self.settings.tftpd_bin):
          status.append(_("tftp-server is not installed."))
       else:
          self.check_service(status,"xinetd")

   def check_vsftpd_bin(self,status):
       """
       Check if vsftpd is installed
       """
       if not os.path.exists(self.settings.vsftpd_bin):
           status.append(_("vsftpd is not installed (NOTE: needed for s390x support only)"))
       else:
           self.check_service(status,"vsftpd","needed for 390x support only")
           
       bootloc = utils.tftpboot_location()
       if not os.path.exists("/etc/vsftpd/vsftpd.conf"):
           status.append("missing /etc/vsftpd/vsftpd.conf")   
       conf = open("/etc/vsftpd/vsftpd.conf")
       data = conf.read()
       lines = data.split("\n")
       ok = False
       for line in lines:
           if line.find("anon_root") != -1 and line.find(bootloc) != -1:
               ok = True
               break
       conf.close()
       if not ok:
           status.append("in /etc/vsftpd/vsftpd.conf the line 'anon_root=%s' should be added (needed for s390x support only)" % bootloc)

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
             if re_disable.search(line) and not line.strip().startswith("#"):
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

