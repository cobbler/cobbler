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

import cexceptions
import os
import os.path
import sub_process
import traceback

class Enchant:

   def __init__(self,config,address,profile,system):
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
       if address is None:
           raise cexceptions.CobblerException("enchant_failed","no address specified")
       if system is None and profile is None:
           raise cexceptions.CobblerException("enchant_failed","no profile specified")
       if system is not None and self.config.systems().find(system) is None:
           raise cexceptions.CobblerException("enchant_failed","system name not found")
       if profile is not None and self.config.profiles().find(profile) is None:
           raise cexceptions.CobblerException("enchant_failed","profile name not found")

   def ssh_exec(self,cmd,catch_fail=True):
       """
       Invoke an SSH command.
       """
       cmd2 = "ssh root@%s %s" % (self.address,cmd)
       print "running: %s" % cmd2
       rc = sub_process.call(cmd2,shell=True)
       print "returns: %d" % rc
       if catch_fail and rc != 0:
           raise cexceptions.CobblerException("enchant_failed","ssh failure")

   def run(self):
       """
       Replace the OS of a remote system.
       """
       koan = os.path.basename(self.settings.koan_path)
       where_is_koan = os.path.join(self.settings.webdir,os.path.basename(koan))
       if not os.path.exists(where_is_koan):
           raise cexceptions.CobblerException("enchant_failed","koan is missing")

       try:
           self.ssh_exec("wget http://%s/cobbler/%s" % (self.settings.server, koan))
           self.ssh_exec("up2date install syslinux",catch_fail=False)
           self.ssh_exec("yum -y install syslinux",catch_fail=False)
           self.ssh_exec("rpm -Uvh %s --force --nodeps" % koan)
           if self.system:
               self.ssh_exec("koan --replace-self --system=%s --server=%s" % (self.system, self.settings.server))
           else:
               self.ssh_exec("koan --replace-self --profile=%s --server=%s" % (self.profile, self.settings.server))
           self.ssh_exec("/sbin/reboot")
           return True
       except:
           traceback.print_exc()
           raise cexceptions.CobblerException("enchant_failed","exception")
       return False # shouldn't be here

