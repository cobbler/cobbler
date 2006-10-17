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
import pexpect
# GOING AWAY
# import pxssh
import sub_process
import traceback

class Enchant:

   def __init__(self,config,sysname,profile):
       """
       Constructor.  
       config:  a configuration reference (see api module)
       sysname:  address of system to enchant (not necc. defined in cobbler)
       profile:  profile to make the system become
       """
       self.config = config
       self.settings = self.config.settings()
       self.username = "root"
       self.sysname = sysname
       if sysname is None:
           raise cexceptions.CobblerException("enchant_failed","no system name specified")
       self.profile = ''

   def ssh_exec(self,cmd):
       """
       Invoke an SSH command.
       """
       sub_process.call("ssh root:%s %s" % (self.sysname,cmd),shell=True)

   def run(self):
       """
       Replace the OS of a remote system.
       """
       koan = os.path.basename(self.settings.koan_path)
       sys  = self.config.systems().find(self.sysname)
       if sys is None:
           raise cexceptions.CobblerException("enchant_failed","system not in cobbler database")
       pro  = self.config.profiles().find(sys.profile)
       self.profile = pro.name
       if pro is None:
           raise cexceptions.CobblerException("enchant_failed","no such profile for system (%s): %s" % (self.sysname, self.profile))
       where_is_koan = os.path.join(self.settings.webdir,os.path.basename(koan))
       if not os.path.exists(where_is_koan):
           raise cexceptions.CobblerException("enchant_failed","koan is missing")

       try:
           self.ssh_exec(self.sysname, "wget http://%s/cobbler/%s" % (self.settings.server, koan))
           self.ssh_exec(self.sysname, "rpm -Uvh %s --force --nodeps" % koan))
           self.ssh_exec(self.sysname, "koan --replace-self --profile=%s --server=%s" % (self.profile, self.settings.server))
           # self.ssh_exec(self.sysname, "/sbin/reboot")
           return True
       except:
           traceback.print_exc()
           raise cexceptions.CobblerException("enchant_failed","exception")
       return False # shouldn't be here

