"""
Configures acls for various users/groups so they can access the cobbler command
line as non-root.

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import os.path
import shutil
import sub_process
import sys
import glob
import traceback
import errno
import utils
from cexceptions import *
from utils import _


class AclConfig:

    def __init__(self,config):
        """
        Constructor
        """
        self.config      = config
        self.api         = config.api
        self.settings    = config.settings()
        #self.distros     = config.distros()
        #self.profiles    = config.profiles()
        #self.systems     = config.systems()
        #self.repos       = config.repos()

    def run(self,adduser=None,addgroup=None,removeuser=None,removegroup=None):
        """
        Automate setfacl commands
        """

        if adduser:
            self.modacl(True,True,adduser)
        if addgroup:
            self.modacl(True,False,addgroup)
        if removeuser:
            self.modacl(False,True,removeuser)
        if removegroup:
            self.modacl(False,False,removegroup) 
             
    def modacl(self,isadd,isuser,who):

        webdir = self.settings.webdir
        snipdir = self.settings.snippetsdir
        tftpboot = utils.tftpboot_location()
        PROCESS_DIRS = {
           webdir                      : "rwx",
           "/var/log/cobbler"          : "rwx",
           "/var/lib/cobbler"          : "rwx",
           "/etc/cobbler"              : "rwx",
           tftpboot                    : "rwx",
           "/var/lib/cobbler/triggers" : "rwx"
        }
        if not snipdir.startswith("/var/lib/cobbler/"):
            PROCESS_DIRS[snipdir] = "r"

        cmd = "-R"
        
        if isadd:
           cmd = "%s -m" % cmd
        else:
           cmd = "%s -x" % cmd

        if isuser:
           cmd = "%s u:%s" % (cmd,who)
        else:
           cmd = "%s g:%s" % (cmd,who)

        for d in PROCESS_DIRS:
            how = PROCESS_DIRS[d]
            if isadd:
               cmd2 = "%s:%s" % (cmd,how)
            else:
               cmd2 = cmd

            cmd2 = "%s %s" % (cmd2,d)
            print "- setfacl -d %s" % cmd2
            rc = sub_process.call("setfacl -d %s" % cmd2,shell=True)
            if not rc == 0:
               raise CX(_("command failed"))
            print "- setfacl %s" % cmd2
            rc = sub_process.call("setfacl %s" % cmd2,shell=True)
            if not rc == 0:
               raise CX(_("command failed"))






