"""
This is the func.virt based deploy code.
Also does power management

Copyright 2006-2009, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>
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

import utils
from cexceptions import *
from utils import _
import random

try:
   import func.overlord.client as func
   from func.CommonErrors import Func_Client_Exception
   FUNC=True
except ImportError:
   FUNC=False

def register():
   """
   The mandatory cobbler module registration hook.
   """
   return "deploy"


class FuncDeployer:

    def what(self):
        return "func.virt"

    def __init__(self,config,verbose=False):
        """
        Constructor
        """
        self.verbose     = verbose
        self.config      = config
        self.api         = config.api
        self.settings    = config.settings()

    # -------------------------------------------------------

    def __find_host(self, virt_group):
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

        if not FUNC:
            raise CX("Func is not available.")

        try:
            client = func.Client(virt_host)
            rc = client.virt.install(self.settings.server, system.hostname, True)[virt_host]
            if rc != 0:
                raise CX("Func Error: %s"%rc[2])
            system.virt_host = virt_host
            self.api.add_system(system)
            return rc

        except Func_Client_Exception, ex:
            raise CX("A Func Exception has occured: %s"%ex)

    # -------------------------------------------------------

    def delete(self, system):
        """
        Delete the virt system
        """
        raise CX("Removing a virtual instance is not implemented yet.")


def get_manager(config):
    return FuncDeployer(config)
