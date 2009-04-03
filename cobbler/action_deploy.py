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

import module_loader
from cexceptions import *

class Deployer:
    def __init__(self,config):
        """
        Constructor
        """
        self.config    = config
        self.settings  = config.settings()
        self.api       = config.api
        self.virt_host = None

    def deploy(self, system, virt_host = None, virt_group=None):
        """
        Deploy the current system to the virtual host or virtual group
        """
        deployer = module_loader.get_module_from_file(
            "deploy",
            "module",
            "deploy_func").get_manager(self.config)
        return deployer.deploy(system,
                               virt_host = virt_host,
                               virt_group = virt_group)

