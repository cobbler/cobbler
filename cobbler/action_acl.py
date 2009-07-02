"""
Configures acls for various users/groups so they can access the cobbler command
line as non-root.

Copyright 2006-2008, Red Hat, Inc
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
            rc = utils.subprocess_call(self.logger,"setfacl -d %s" % cmd2,shell=True)
            if not rc == 0:
               utils.die(self.logger,"command failed")
            rc = utils.subprocess_call(self.logger,"setfacl %s" % cmd2,shell=True)
            if not rc == 0:
               utils.die(self.logger,"command failed")






