"""
Enables the "cobbler enchant" command to apply profiles
to remote systems, whether or not they are running koan.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

from cexceptions import *
import os
import os.path
import sub_process
import traceback
from rhpl.translate import _, N_, textdomain, utf8


class Enchant:

   def __init__(self,config,address,profile,system,is_virt):
       """
       Constructor.
       config:  a configuration reference (see api module)
       sysname:  address of system to enchant (not necc. defined in cobbler)
       profile:  profile to make the system become
       """
       self.config = config
       self.settings = self.config.settings()
       self.address = address
       self.profile = profile
       self.system = system
       self.is_virt = is_virt
       if address is None:
           raise CX(_("enchant failed. no address specified"))
       if system is None and profile is None:
           raise CX(_("enchant failed. no profile specified"))
       if system is not None and self.config.systems().find(name=system) is None:
           raise CX(_("enchant failed. system not found"))
       if profile is not None and self.config.profiles().find(name=profile) is None:
           raise CX(_("enchant failed. profile name not found"))


   def ssh_exec(self,cmd,catch_fail=True):
       """
       Invoke an SSH command.
 -o 'HostKeyAlias NoHostKeyStorage'
       """
       cmd2 = "ssh -o 'StrictHostKeyChecking=no' -o 'HostKeyAlias nocobblerhostkey' root@%s %s" % (self.address,cmd)
       print "running: %s" % cmd2
       rc = sub_process.call(cmd2,shell=True)
       print "returns: %d" % rc
       if catch_fail and rc != 0:
           raise CX(_("enchant failed. SSH error."))

   def run(self):
       """
       Replace the OS of a remote system.
       """

       # clean out known hosts file to eliminate conflicts
       known_hosts = open("/root/.ssh/known_hosts","r")
       data = known_hosts.read()
       known_hosts.close()
       known_hosts = open("/root/.ssh/known_hosts","w+")
       for line in data.split("\n"):
           if not line.startswith("nocobblerhostkey"):
               known_hosts.write(line)
               known_hosts.write("\n")
       known_hosts.close()

       # make sure the koan rpm is present, if it's not there, user didn't run sync first
       # or it's not configured in /var/lib/cobbler/settings
       koan = os.path.basename(self.settings.koan_path)
       where_is_koan = os.path.join(self.settings.webdir,os.path.basename(koan))
       if not os.path.exists(where_is_koan) or os.path.isdir(where_is_koan):
           raise CX(_("koan_path is not correct in /var/lib/cobbler/settings, or need to run 'cobbler sync'."))

       try:
           self.ssh_exec("wget http://%s/cobbler/%s" % (self.settings.server, koan))
           # koan doesn't require libvirt-python, but uses it for koan --virt options if available
           # so, if --virt is requested, we have to make sure it's installed.  It's probably
           # reasonable to just assume it /IS/ installed though as Xen kernel usage is required.
           extra_virt_packages = ""
           if self.is_virt:
              extra_virt_packages = " libvirt-python libvirt"
           # package installation without knowing whether the target is yum-based or not
           self.ssh_exec("up2date install syslinux%s" % (extra_virt_packages), catch_fail=False)
           self.ssh_exec("yum -y install syslinux%s" % (extra_virt_packages), catch_fail=False)
           self.ssh_exec("rpm -Uvh %s --force --nodeps" % koan)
           # choose SSH command line based on whether this command was given --virt or not
           operation = "--replace-self"
           if self.is_virt:
               operation = "--virt"
           if self.system:
               self.ssh_exec("koan %s --system=%s --server=%s" % (operation, self.system, self.settings.server))
           else:
               self.ssh_exec("koan %s --profile=%s --server=%s" % (operation, self.profile, self.settings.server))
           # don't have to reboot for virt installs
           if not self.is_virt:
               self.ssh_exec("/sbin/reboot")
           return True
       except:
           traceback.print_exc()
           raise CX(_("enchant failed.  an exception occurred."))
       return False # shouldn't be here

