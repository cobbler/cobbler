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
import subprocess
import pexpect
import pxssh
import traceback

class Enchant:

   def __init__(self,config,sysname,profile,system,password):
       """
       Constructor.  All arguments required.
       """
       self.config = config
       self.settings = self.config.settings()
       self.username = "root"
       self.sysname = sysname
       self.profile = profile
       self.system = system
       self.password = password
 
   def call(self,cmd):
       """
       Invoke something over SSH.
       """
       print "ssh -> %s" % cmd
       self.ssh.sendline(cmd)
       self.ssh.prompt()

   def run(self):
       """
       Replace the OS of a remote system.
       """
       try:
           ssh = self.ssh = pxssh.pxssh()
           if not ssh.login(self.sysname, self.username, self.password):
               raise cexceptions.CobblerException("enchant_failed","SSH login denied")
           else:
               self.call("wget http://%s/cobbler/koan.rpm -o /koan.rpm" % self.settings.server)
               self.call("rpm -Uvh koan.rpm --force")
               if self.profile is not None:
                   self.call("koan --replace-self --profile=%s --server=%s" % (self.profile, self.settings.server))
                   return True
               if self.system is not None:
                   self.call("koan --replace-self --system=%s --server=%s" % (self.system, self.settings.server))
                   return True
       except:
           traceback.print_exc()
           return False
       return False # shouldn't be here

