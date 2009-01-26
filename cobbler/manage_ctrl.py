"""
Builds out DHCP info
This is the code behind 'cobbler sync'.

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
import time
import sub_process
import sys
import glob
import traceback
import errno
from shlex import shlex


import utils
from cexceptions import *
import templar 

import item_distro
import item_profile
import item_repo
import item_system

from utils import _

class ManageCtrl:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config,verbose=False,dns=None,dhcp=None):
        """
        Constructor
        """
        self.verbose     = verbose
        self.config      = config
        self.api         = config.api
        self.distros     = config.distros()
        self.profiles    = config.profiles()
        self.systems     = config.systems()
        self.settings    = config.settings()
        self.repos       = config.repos()
        self.templar     = templar.Templar(config)
        self.dns         = dns

    def write_dhcp_lease(self,port,host,ip,mac):
        return dhcp.write_dhcp_lease(port,host,ip,mac)

    def remove_dhcp_lease(self,port,host):
        return dhcp.remove_dhcp_lease(port,host)

    def write_dhcp_file(self):
        return dhcp.write_dhcp_file()

    def regen_ethers(self):
        return dhcp.regen_ethers()

    def regen_hosts(self):
        return dns.regen_hosts()

    def write_dns_files(self):
        return dns.write_bind_files()
