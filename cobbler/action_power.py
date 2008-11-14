"""
Power management library.  For cobbler objects with power management configured
encapsulate the logic to run power management commands so that the admin does not
have to use seperate tools and remember how each of the power management tools are
set up.  This makes power cycling a system for reinstallation much easier.

See https://fedorahosted.org/cobbler/wiki/PowerManagement

Copyright 2008, Red Hat, Inc
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
import sub_process
import sys

import utils
from cexceptions import *
import traceback

class PowerTool:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,system):
        """
        Power library constructor requires a cobbler system object.
        """
        self.system      = system

    def power(self, desired_state)
        """
        state is either "on" or "off".  Rebooting is implemented at the api.py
        level.
        """

        template = self.get_command_template()

        meta = utils.blender(self.system, False)
        meta["power_mode"] = desired_state

        cmd = templar.render(self, template, meta, None, self.system)
        cmd = cmd.strip()

        print "cobbler power configuration is:\n"

        pritn "      type   : %s" % self.system.power_type
        print "      address: %s" % self.system.power_address
        print "      user   : %s" % self.system.power_user
        print "      id     : %s" % self.system.power_id

        print ""

        print "- " % cmd

        tool_needed = cmd.split(" ")[0]
        if not os.path.exists(tool_needed):
           raise CX("error: %s is not installed" % tool_needed)

        rc = sub_process.call(cmd, shell=True)
        if not rc:
           raise CX("command failed, check physical setup and cobler config")

        return rc

    def get_command_template(self):
        if self.system.power_type in [ "", "none" ]:
            raise CX("Power management is not enabled for this system")
        if self.system.type == "bullpap":
            return "/etc/cobbler/power_bullpap.template"
        if self.system.type == "apc_snmp":
            return "/etc/cobbler/power_apc_snmp.template"
        if self.system.type == "ether-wake":
            return "/etc/cobbler/power_ether-wake.template"
        if self.system.type == "ipmilan":
            return "/etc/cobbler/power_ipmilan.template"
        if self.system.type == "drac":
            return "/etc/cobbler/power_drac.template"
        if self.system.type == "ipmitool":
            return "/etc/cobbler/power_ipmitool.template"
        if self.system.type == "ilo":
            return "/etc/cobbler/power_ilo.template"
        if self.system.type == "rsa":
            return "/etc/cobbler/power_rsa.template"
        raise CX("Invalid power management type for this system")

