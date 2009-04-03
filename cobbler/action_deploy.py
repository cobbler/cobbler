"""
Replicate from a cobbler master.

Copyright 2009, Red Hat, Inc
Scott Henson <shenson@redhat.com>

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

import func_utils
from utils import _
from cexceptions import *
import random

class Deployer:
    def __init__(self,config):
        """
        Constructor
        """
        self.config    = config
        self.settings  = config.settings()
        self.api       = config.api
        self.virt_host = None

    # -------------------------------------------------------

    def find_host(self, virt_group):
        """
        Find a system in the virtual group specified
        """

        systems = self.api.find_system(virt_group=virt_group, return_list = True)
        if len(systems) == 0:
            raise CX("No systems were found in virtual group %s"%virt_group)
        return random.choice(systems)

    # -------------------------------------------------------

    def deploy(self, system, virt_host = None, virt_group=None):
        """
        Deploy the current system to the virtual host or virtual group
        """
        if virt_host is None and virt_group is not None:
            virt_host = self.find_host(virt_group)

        if virt_host is None and system.virt_group == '':
            virt_host = self.find_host(system.virt_group)

        if system.virt_host != '':
            virt_host = system.virt_host

        if virt_host is None:
            raise CX("No host specified for deployment.")

        if not func_utils.HAZFUNC:
            raise CX("Func is not available.")

        try:
            client = func_utils.func.Client(virt_host)
            rc = client.virt.install(self.settings.server, system.hostname, True)[virt_host]
            if rc != 0:
                raise CX("Func Error: %s"%rc[2])
            system.virt_host = virt_host
            self.api.add_system(system)
            return rc

        except func_utils.Func_Client_Exception, ex:
            raise CX("A Func Exception has occured: %s"%ex)
