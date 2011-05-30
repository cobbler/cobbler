"""
This is some of the code behind 'cobbler sync'.

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

import traceback
import errno
import re
import clogger
from shlex import shlex


import utils
from cexceptions import *
import templar 

from utils import _


def register():
   """
   The mandatory cobbler module registration hook.
   """
   return "manage"


class TftpdPyManager:

    def what(self):
        return "tftpd"

    def __init__(self,config,logger):
        """
        Constructor
        """
        self.logger        = logger
	if self.logger is None:
	    self.logger = clogger.Logger()

        self.config        = config
        self.templar       = templar.Templar(config)
        self.settings_file = "/etc/xinetd.d/tftp"

    def regen_hosts(self):
        pass # not used

    def write_dns_files(self):
        pass # not used

    def write_boot_files_distro(self,distro):
        """
        Copy files in profile["boot_files"] into /tftpboot.  Used for vmware
        currently.
        """
        pass # not used.  Handed by tftp.py

    def write_boot_files(self):
        """
        Copy files in profile["boot_files"] into /tftpboot.  Used for vmware
        currently.
        """
        pass # not used.  Handed by tftp.py

    def add_single_distro(self,distro):
        pass # not used

    def write_tftpd_files(self):
        """
        xinetd files are written when manage_tftp is set in
        /var/lib/cobbler/settings.
        """
        template_file = "/etc/cobbler/tftpd.template"

        try:
            f = open(template_file,"r")
        except:
            raise CX(_("error reading template %s") % template_file)
        template_data = ""
        template_data = f.read()
        f.close()

        metadata = {
            "user"      : "nobody",
            "binary"    : "/usr/sbin/tftpd.py",
            "args"      : "-v"
        }

        self.logger.info("generating %s" % self.settings_file)
        self.templar.render(template_data, metadata, self.settings_file, None)

    def sync(self,verbose=True):
        """
        Write out files to /tftpdboot.  Unused for the python server
        """
        pass

    def update_netboot(self,name):
        """
        Write out files to /tftpdboot.  Unused for the python server
        """
        pass

    def add_single_system(self,name):
        """
        Write out files to /tftpdboot.  Unused for the python server
        """
        pass

def get_manager(config,logger):
    return TftpdPyManager(config,logger)

