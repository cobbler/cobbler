"""
Configures acls for various users/groups so they can access the cobbler command
line as non-root.  Now that CLI is largely remoted (XMLRPC) this is largely just
useful for not having to log in (access to shared-secret) file but also grants
access to hand-edit various config files and other useful things.

Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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
import os.path
import shutil
import sys
import glob
import traceback
import errno
import utils
from cexceptions import *
from utils import _
import clogger

class AclConfig:

    def __init__(self,config,logger=None):
        """
        Constructor
        """
        self.config      = config
        self.api         = config.api
        self.settings    = config.settings()
        if logger is None:
            logger       = clogger.Logger()
        self.logger      = logger

    def run(self,adduser=None,addgroup=None,removeuser=None,removegroup=None):
        """
        Automate setfacl commands
        """

        ok = False
        if adduser:
            ok = True
            self.modacl(True,True,adduser)
        if addgroup:
            ok = True
            self.modacl(True,False,addgroup)
        if removeuser:
            ok = True
            self.modacl(False,True,removeuser)
        if removegroup:
            ok = True
            self.modacl(False,False,removegroup) 
        if not ok:
            raise CX("no arguments specified, nothing to do")
     
    def modacl(self,isadd,isuser,who):

        webdir = self.settings.webdir
        snipdir = self.settings.snippetsdir
        tftpboot = utils.tftpboot_location()

        PROCESS_DIRS = {
           "/var/log/cobbler"          : "rwx",
           "/var/log/cobbler/tasks"    : "rwx",
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
            rc = utils.subprocess_call(self.logger,"setfacl -d %s" % cmd2,shell=True)
            if not rc == 0:
               utils.die(self.logger,"command failed")
            rc = utils.subprocess_call(self.logger,"setfacl %s" % cmd2,shell=True)
            if not rc == 0:
               utils.die(self.logger,"command failed")






