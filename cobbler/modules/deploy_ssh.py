"""
This is the SSH based deploy code.
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
import func_utils
from cexceptions import *
from utils import _

def register():
   """
   The mandatory cobbler module registration hook.
   """
   return "deploy"


class SshDeployer:

    def what(self):
        return "ssh"

    def __init__(self,config,verbose=False):
        """
        Constructor
        """
        self.verbose     = verbose
        self.config      = config
        self.api         = config.api
        self.settings    = config.settings()

    # -------------------------------------------------------

    def deploy(self, system, virt_host = None, virt_group=None):
        """
        Deploy the current system to the virtual host or virtual group
        """
        if virt_group is not None:
            host_list = self.api.find_system(virt_group=virt_group, no_errors=True)
            

    # -------------------------------------------------------

    def start(self, system):
        """
        Start the virt system
        """
        pass

    # -------------------------------------------------------

    def stop(self, system):
        """
        Stop the virt system
        """
        pass

    # -------------------------------------------------------

    def restart(self, system):
        """
        Restart the virt system
        """
        pass

    # -------------------------------------------------------

    def delete(self, system):
        """
        Delete the virt system
        """
        pass


def get_manager(config):
    return FuncDeployer(config)
