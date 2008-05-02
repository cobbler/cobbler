"""
Builds out DHCP info
This is the code behind 'cobbler sync'.

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
import time
import sub_process
import sys
import glob
import traceback
import errno
import popen2
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
