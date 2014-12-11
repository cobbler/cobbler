"""
Power management library.  Encapsulate the logic to run power management
commands so that the Cobbler user does not have to remember different power
management tools syntaxes.  This makes rebooting a system for OS installation
much easier.

Copyright 2008-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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

import glob
import os
import re
import time

from cexceptions import CX
import clogger
import templar
import utils


def get_power_types():
    """
    Get possible power management types

    @return list possible power management types
    """

    power_types = []
    power_template = re.compile(r'fence_(.*)')
    fence_files = glob.glob("/usr/sbin/fence_*") + glob.glob("/sbin/fence_*")
    for x in fence_files:
        templated_x = power_template.search(x).group(1)
        if templated_x not in power_types:
            power_types.append(templated_x)
    power_types.sort()
    return power_types


def validate_power_type(power_type):
    """
    Check if a power management type is valid

    @param str power_type power management type
    @raise CX if power management type is invalid
    """

    power_types = get_power_types()
    if not power_types:
        raise CX("you need to have fence-agents installed")
    if power_type not in power_types:
        raise CX("power management type must be one of: %s" % ",".join(power_types))


def get_power_command(power_type):
    """
    Get power management command path

    @param str power_type power management type
    @return str power management command path
    """

    if power_type:
        # try /sbin, then /usr/sbin
        power_path1 = "/sbin/fence_%s" % power_type
        power_path2 = "/usr/sbin/fence_%s" % power_type
        for power_path in (power_path1, power_path2):
            if os.path.isfile(power_path) and os.access(power_path, os.X_OK):
                return power_path
    return None


def get_power_template(power_type):
    """
    Get power management template

    @param str power_type power management type
    @return str power management input template
    """

    if power_type:
        power_template = "/etc/cobbler/power/fence_%s.template" % power_type
        if os.path.isfile(power_template):
            f = open(power_template)
            template = f.read()
            f.close()
            return template

    # return a generic template if a specific one wasn't found
    return "action=$power_mode\nlogin=$power_user\npasswd=$power_pass\nipaddr=$power_address\nport=$power_id"


class PowerManager:
    """
    Handles power management in systems
    """

    def __init__(self, api, collection_mgr, logger=None):
        """
        Constructor

        @param CobblerAPI api Cobbler API
        @param CollectionManager collection_mgr collection manager
        @param Logger logger logger
        """

        self.collection_mgr = collection_mgr
        self.settings = collection_mgr.settings()
        self.api = api
        if logger is None:
            logger = clogger.Logger()
        self.logger = logger

    def _power(self, system, power_operation, user=None, password=None, logger=None):
        """
        Performs a power operation on a system.
        Internal method

        @param System system Cobbler system
        @param str power_operation power operation. Valid values: on, off, status.
                Rebooting is implemented as a set of 2 operations (off and on) in
                a higher level method.
        @param str user power management user. If user and password are not
                supplied, environment variables COBBLER_POWER_USER and
                COBBLER_POWER_PASS will be used.
        @param str password power management password
        @param Logger logger logger
        @return bool/None if power operation is 'status', return if system is on;
                otherwise, return None
        @raise CX if there are errors
        """

        if logger is None:
            logger = self.logger

        power_command = get_power_command(system.power_type)
        if not power_command:
            utils.die(logger, "no power type set for system")

        meta = utils.blender(self.api, False, system)
        meta["power_mode"] = power_operation

        # allow command line overrides of the username/password
        if user is not None:
            meta["power_user"] = user
        if password is not None:
            meta["power_pass"] = password

        logger.info("cobbler power configuration is:")
        logger.info("      type   : %s" % system.power_type)
        logger.info("      address: %s" % system.power_address)
        logger.info("      user   : %s" % system.power_user)
        logger.info("      id     : %s" % system.power_id)

        # if no username/password data, check the environment
        if meta.get("power_user", "") == "":
            meta["power_user"] = os.environ.get("COBBLER_POWER_USER", "")
        if meta.get("power_pass", "") == "":
            meta["power_pass"] = os.environ.get("COBBLER_POWER_PASS", "")

        template = get_power_template(system.power_type)
        tmp = templar.Templar(self.collection_mgr)
        template_data = tmp.render(template, meta, None, system)
        logger.info("power command: %s" % power_command)
        logger.info("power command input: %s" % template_data)

        # Try the power command 5 times before giving up.
        # Some power switches are flakey
        for x in range(0, 5):
            output, rc = utils.subprocess_sp(logger, power_command, shell=False, input=template_data)
            if rc == 0:
                # If the desired state is actually a query for the status
                # return different information than command return code
                if power_operation == 'status':
                    match = re.match('^(Status:|.+power\s=)\s(on|off)$', output, re.IGNORECASE | re.MULTILINE)
                    if match:
                        power_status = match.groups()[1]
                        if power_status.lower() == 'on':
                            return True
                        else:
                            return False
                    error_msg = "command succeeded (rc=%s), but output ('%s') was not understood" % (rc, output)
                    utils.die(logger, error_msg)
                    raise CX(error_msg)
                return None
            else:
                time.sleep(2)

        if not rc == 0:
            error_msg = "command failed (rc=%s), please validate the physical setup and cobbler config" % rc
            utils.die(logger, error_msg)
            raise CX(error_msg)

    def power_on(self, system, user=None, password=None, logger=None):
        """
        Powers up a system that has power management configured.

        @param System system Cobbler system
        @param str user power management user
        @param str password power management password
        @param Logger logger logger
        """

        self._power(system, "on", user, password, logger)

    def power_off(self, system, user=None, password=None, logger=None):
        """
        Powers down a system that has power management configured.

        @param System system Cobbler system
        @param str user power management user
        @param str password power management password
        @param Logger logger logger
        """

        self._power(system, "off", user, password, logger)

    def reboot(self, system, user=None, password=None, logger=None):
        """
        Reboot a system that has power management configured.

        @param System system Cobbler system
        @param str user power management user
        @param str password power management password
        @param Logger logger logger
        """

        self.power_off(system, user, password, logger=logger)
        time.sleep(5)
        self.power_on(system, user, password, logger=logger)

    def get_power_status(self, system, user=None, password=None, logger=None):
        """
        Get power status for a system that has power management configured.

        @param System system Cobbler system
        @param str user power management user
        @param str password power management password
        @param Logger logger logger
        @return bool if system is powered on
        """

        return self._power(system, "status", user, password, logger)
