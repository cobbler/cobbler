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
import traceback

import utils
from cexceptions import *
import templar

class PowerTool:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,system,api):
        """
        Power library constructor requires a cobbler system object.
        """
        self.system      = system
        self.api         = api

    def power(self, desired_state):
        """
        state is either "on" or "off".  Rebooting is implemented at the api.py
        level.
        """

        template = self.get_command_template()
        template_file = open(template, "r")

        meta = utils.blender(self.api, False, self.system)
        meta["power_mode"] = desired_state

        tmp = templar.Templar(self.api._config)
        cmd = tmp.render(template_file, meta, None, self.system)
        template_file.close()

        cmd = cmd.strip()

        print "cobbler power configuration is:\n"

        print "      type   : %s" % self.system.power_type
        print "      address: %s" % self.system.power_address
        print "      user   : %s" % self.system.power_user
        print "      id     : %s" % self.system.power_id

        print ""

        print "- %s" % cmd

        tool_needed = cmd.split(" ")[0]
        if not os.path.exists(tool_needed):
           raise CX("error: %s is not installed" % tool_needed)

        rc = sub_process.call(cmd, shell=True)
        if not rc == 0:
           raise CX("command failed (rc=%s), please validate the physical setup and cobler config" % rc)

        return rc

    def get_command_template(self):

        """
        In case the user wants to customize the power management commands, 
        we source the code for each command from /etc/cobbler and run
        them through Cheetah.
        """

        if self.system.power_type in [ "", "none" ]:
            raise CX("Power management is not enabled for this system")

        map = {
            "bullpap"    : "/etc/cobbler/power_bullpap.template",
            "apc_snmp"   : "/etc/cobbler/power_apc_snmp.template",
            "ether-wake" : "/etc/cobbler/power_ether_wake.template",
            "ipmilan"    : "/etc/cobbler/power_ipmilan.template",
            "drac"       : "/etc/cobbler/power_drac.template",
            "ipmitool"   : "/etc/cobbler/power_ipmitool.template",
            "ipmilan"    : "/etc/cobbler/power_ipmilan.template",
            "ilo"        : "/etc/cobbler/power_ilo.template",
            "rsa"        : "/etc/cobbler/power_rsa.template"
        }

        result = map.get(self.system.power_type, "")
        if result == "":
            raise CX("Invalid power management type for this system (%s, %s)" % (self.system.power_type, self.system.name))
        return result

