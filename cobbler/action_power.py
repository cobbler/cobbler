"""
Power management library.  For cobbler objects with power management configured
encapsulate the logic to run power management commands so that the admin does not
have to use seperate tools and remember how each of the power management tools are
set up.  This makes power cycling a system for reinstallation much easier.

See https://fedorahosted.org/cobbler/wiki/PowerManagement

Copyright 2008-2009, Red Hat, Inc
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
import traceback
import time
import re

import utils
import func_utils
from cexceptions import *
import templar
import clogger

class PowerTool:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config,system,api,force_user=None,force_pass=None,logger=None):
        """
        Power library constructor requires a cobbler system object.
        """
        self.system      = system
        self.config      = config
        self.settings    = config.settings()
        self.api         = api
        self.logger      = self.api.logger
        self.force_user  = force_user
        self.force_pass  = force_pass
        if logger is None:
            logger = clogger.Logger()
        self.logger      = logger

    def power(self, desired_state):
        """
        state is either "on" or "off".  Rebooting is implemented at the api.py
        level.

        The user and password need not be supplied.  If not supplied they
        will be taken from the environment, COBBLER_POWER_USER and COBBLER_POWER_PASS.
        If provided, these will override any other data and be used instead.  Users
        interested in maximum security should take that route.
        """

        template = self.get_command_template()
        template_file = open(template, "r")

        meta = utils.blender(self.api, False, self.system)
        meta["power_mode"] = desired_state

        # allow command line overrides of the username/password 
        if self.force_user is not None:
           meta["power_user"] = self.force_user
        if self.force_pass is not None:
           meta["power_pass"] = self.force_pass

        tmp = templar.Templar(self.api._config)
        cmd = tmp.render(template_file, meta, None, self.system)
        template_file.close()

        cmd = cmd.strip()

        self.logger.info("cobbler power configuration is:")

        self.logger.info("      type   : %s" % self.system.power_type)
        self.logger.info("      address: %s" % self.system.power_address)
        self.logger.info("      user   : %s" % self.system.power_user)
        self.logger.info("      id     : %s" % self.system.power_id)

        # if no username/password data, check the environment

        if meta.get("power_user","") == "":
            meta["power_user"] = os.environ.get("COBBLER_POWER_USER","")
        if meta.get("power_pass","") == "":
            meta["power_pass"] = os.environ.get("COBBLER_POWER_PASS","")

        self.logger.info("- %s" % cmd)

        # use shell so we can have mutliple power commands chained together
        cmd = ['/bin/sh','-c', cmd]

        # Try the power command 5 times before giving up.
        # Some power switches are flakey
        for x in range(0,5):
            output, rc = utils.subprocess_sp(self.logger, cmd, shell=False)
            if rc == 0:
                # If the desired state is actually a query for the status
                # return different information than command return code
                if desired_state == 'status':
                    match = re.match('(^Status:\s)(ON|OFF)', output)
                    if match:
                        power_status = match.groups()[1]
                        if power_status == 'ON':
                            return True
                        else:
                            return False
                    utils.die(self.logger,"command succeeded (rc=%s), but output ('%s') was not understood" % (rc, output))
                    return None
                break
            else:
                time.sleep(2)

        if not rc == 0:
           utils.die(self.logger,"command failed (rc=%s), please validate the physical setup and cobbler config" % rc)

        return rc

    def get_command_template(self):

        """
        In case the user wants to customize the power management commands, 
        we source the code for each command from /etc/cobbler and run
        them through Cheetah.
        """

        if self.system.power_type in [ "", "none" ]:
            utils.die(self.logger,"Power management is not enabled for this system")

        result = utils.get_power(self.system.power_type)
        if not result:
            utils.die(self.logger, "Invalid power management type for this system (%s, %s)" % (self.system.power_type, self.system.name))
        return result

