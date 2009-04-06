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
import time

import utils
from cexceptions import *
import templar

class PowerTool:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config,system,api,force_user=None,force_pass=None):
        """
        Power library constructor requires a cobbler system object.
        """
        self.system      = system
        self.config      = config
        self.settings    = config.settings()
        self.api         = api
        self.force_user  = force_user
        self.force_pass  = force_pass

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

        print "cobbler power configuration is:\n"

        print "      type   : %s" % self.system.power_type
        print "      address: %s" % self.system.power_address
        print "      user   : %s" % self.system.power_user
        print "      id     : %s" % self.system.power_id

        # if no username/password data, check the environment

        if meta.get("power_user","") == "":
            meta["power_user"] = os.environ.get("COBBLER_POWER_USER","")
        if meta.get("power_pass","") == "":
            meta["power_pass"] = os.environ.get("COBBLER_POWER_PASS","")

        print ""

        print "- %s" % cmd

        # now reprocess the command so we don't feed it through the shell
        cmd = cmd.split(" ")

        #tool_needed = cmd.split(" ")[0]
        #if not os.path.exists(tool_needed):
        #   print "warning: %s does not seem to be installed" % tool_needed

        # Try the power command 5 times before giving up.
        # Some power switches are flakey
        for x in range(0,5):
            rc = sub_process.call(cmd, shell=False, close_fds=True)
            if rc == 0:
                break
            else:
                time.sleep(2)

        if not rc == 0:
           raise CX("command failed (rc=%s), please validate the physical setup and cobbler config" % rc)

        return rc

    def get_command_template(self):

        """
        In case the user wants to customize the power management commands, 
        we source the code for each command from /etc/cobbler and run
        them through Cheetah.
        """

        if self.system.power_type in [ "", "none" ]:
            raise CX("Power management is not enabled for this system")

        powerdir=self.settings.power_template_dir
        map = {
            "bullpap"    : os.path.join(powerdir,"power_bullpap.template"),
            "apc_snmp"   : os.path.join(powerdir,"power_apc_snmp.template"),
            "ether-wake" : os.path.join(powerdir,"power_ether_wake.template"),
            "drac"       : os.path.join(powerdir,"power_drac.template"),
            "ipmitool"   : os.path.join(powerdir,"power_ipmitool.template"),
            "ipmilan"    : os.path.join(powerdir,"power_ipmilan.template"),
            "ilo"        : os.path.join(powerdir,"power_ilo.template"),
            "rsa"        : os.path.join(powerdir,"power_rsa.template"),
            "lpar"       : os.path.join(powerdir,"power_lpar.template"),
            "bladecenter": os.path.join(powerdir,"power_bladecenter.template"),
            "virsh"      : os.path.join(powerdir,"power_virsh.template"),
            "integrity"  : os.path.join(powerdir,"power_integrity.template"),
            "wti"        : os.path.join(powerdir,"power_wti.template"),
        }

        result = map.get(self.system.power_type, "")
        if result == "":
            raise CX("Invalid power management type for this system (%s, %s)" % (self.system.power_type, self.system.name))
        return result

