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
import json
import glob
import logging
import os
from pathlib import Path
import stat
import re
import time
from typing import Optional

from cobbler.cexceptions import CX
from cobbler import utils

# Try the power command 3 times before giving up. Some power switches are flaky.
POWER_RETRIES = 3


def get_power_types() -> list:
    """
    Get possible power management types.

    :returns: Possible power management types
    """

    power_types = []
    fence_files = glob.glob("/usr/sbin/fence_*") + glob.glob("/sbin/fence_*")
    for x in fence_files:
        fence_name = os.path.basename(x).replace("fence_", "")
        if fence_name not in power_types:
            power_types.append(fence_name)
    power_types.sort()
    return power_types


def validate_power_type(power_type: str):
    """
    Check if a power management type is valid.

    :param power_type: Power management type.
    :raise CX: if power management type is invalid
    """

    power_types = get_power_types()
    if not power_types:
        raise CX("you need to have fence-agents installed")
    if power_type not in power_types:
        raise CX("power management type must be one of: %s" % ",".join(power_types))


def get_power_command(power_type: str) -> Optional[str]:
    """
    Get power management command path

    :param power_type: power management type
    :returns: power management command path
    """

    if power_type:
        # try /sbin, then /usr/sbin
        power_path1 = "/sbin/fence_%s" % power_type
        power_path2 = "/usr/sbin/fence_%s" % power_type
        for power_path in (power_path1, power_path2):
            if os.path.isfile(power_path) and os.access(power_path, os.X_OK):
                return power_path
    return None


class PowerManager:
    """
    Handles power management in systems
    """

    def __init__(self, api):
        """
        Constructor

        :param api: Cobbler API
        """
        self.api = api
        self.settings = api.settings()
        self.logger = logging.getLogger()

    def _check_power_conf(self, system, user, password):
        """
        Prints a warning for invalid power configurations.

        :param user: The username for the power command of the system. This overrules the one specified in the system.
        :param password: The password for the power command of the system. This overrules the one specified in the
                         system.
        :param system: Cobbler system
        :type system: System
        """

        if (system.power_pass or password) and system.power_identity_file:
            self.logger.warning("Both password and identity-file are specified")
        if system.power_identity_file:
            ident_path = Path(system.power_identity_file)
            if not ident_path.exists():
                self.logger.warning("identity-file " + system.power_identity_file + " does not exist")
            else:
                ident_stat = stat.S_IMODE(ident_path.stat().st_mode)
                if (ident_stat & stat.S_IRWXO) or (ident_stat & stat.S_IRWXG):
                    self.logger.warning("identity-file %s must not be read/write/exec by group or others",
                                        system.power_identity_file)
        if not system.power_address:
            self.logger.warning("power-address is missing")
        if not (system.power_user or user):
            self.logger.warning("power-user is missing")
        if not (system.power_pass or password) and not system.power_identity_file:
            self.logger.warning("neither power-identity-file nor power-password specified")

    def _get_power_input(self, system, power_operation: str, user: str, password: str) -> str:
        """
        Creates an option string for the fence agent from the system data. This is an internal method.

        :param system: Cobbler system
        :type system: System
        :param power_operation: power operation. Valid values: on, off, status. Rebooting is implemented as a set of 2
                                operations (off and on) in a higher level method.
        :param user: user to override system.power_user
        :param password: password to override system.power_pass
        :return: The option string for the fencer agent.
        """

        self._check_power_conf(system, user, password)
        power_input = ""
        if power_operation is None or power_operation not in ['on', 'off', 'status']:
            raise CX("invalid power operation")
        power_input += "action=" + power_operation + "\n"
        if system.power_address:
            power_input += "ip=" + system.power_address + "\n"
        if system.power_user:
            power_input += "username=" + system.power_user + "\n"
        if system.power_id:
            power_input += "plug=" + system.power_id + "\n"
        if system.power_pass:
            power_input += "password=" + system.power_pass + "\n"
        if system.power_identity_file:
            power_input += "identity-file=" + system.power_identity_file + "\n"
        if system.power_options:
            power_input += system.power_options + "\n"
        return power_input

    def _power(self, system, power_operation: str, user: Optional[str] = None,
               password: Optional[str] = None) -> Optional[bool]:
        """
        Performs a power operation on a system.
        Internal method

        :param system: Cobbler system
        :type system: System
        :param power_operation: power operation. Valid values: on, off, status. Rebooting is implemented as a set of 2
                                operations (off and on) in a higher level method.
        :param user: power management user. If user and password are not supplied, environment variables
                     COBBLER_POWER_USER and COBBLER_POWER_PASS will be used.
        :param password: power management password
        :return: bool/None if power operation is 'status', return if system is on; otherwise, return None
        :raise CX: if there are errors
        """

        power_command = get_power_command(system.power_type)
        if not power_command:
            utils.die("no power type set for system")

        power_info = {"type": system.power_type, "address": system.power_address, "user": system.power_user,
                      "id": system.power_id, "options": system.power_options,
                      "identity_file": system.power_identity_file}

        self.logger.info("cobbler power configuration is: %s", json.dumps(power_info))

        # if no username/password data, check the environment
        if not system.power_user and not user:
            user = os.environ.get("COBBLER_POWER_USER", "")
        if not system.power_pass and not password:
            password = os.environ.get("COBBLER_POWER_PASS", "")

        power_input = self._get_power_input(system, power_operation, user, password)

        self.logger.info("power command: %s", power_command)
        self.logger.info("power command input: %s", power_input)

        rc = -1

        for x in range(0, POWER_RETRIES):
            output, rc = utils.subprocess_sp(power_command, shell=False, input=power_input)
            # Allowed return codes: 0, 1, 2
            # Source: https://github.com/ClusterLabs/fence-agents/blob/master/doc/FenceAgentAPI.md#agent-operations-and-return-values
            if power_operation in ("on", "off", "reboot"):
                if rc == 0:
                    return None
            elif power_operation == "status":
                if rc in (0, 2):
                    match = re.match(r'^(Status:|.+power\s=)\s(on|off)$', output, re.IGNORECASE | re.MULTILINE)
                    if match:
                        power_status = match.groups()[1]
                        if power_status.lower() == 'on':
                            return True
                        else:
                            return False
                    error_msg = "command succeeded (rc=%s), but output ('%s') was not understood" % (rc, output)
                    utils.die(error_msg)
                    raise CX(error_msg)
            time.sleep(2)

        if not rc == 0:
            error_msg = "command failed (rc=%s), please validate the physical setup and cobbler config" % rc
            utils.die(error_msg)
            raise CX(error_msg)

    def power_on(self, system, user: Optional[str] = None, password: Optional[str] = None):
        """
        Powers up a system that has power management configured.

        :param system: Cobbler system
        :type system: System
        :param user: power management user
        :param password: power management password
        """

        self._power(system, "on", user, password)

    def power_off(self, system, user: Optional[str] = None, password: Optional[str] = None):
        """
        Powers down a system that has power management configured.

        :param system: Cobbler system
        :type system: System
        :param user: power management user
        :param password: power management password
        """

        self._power(system, "off", user, password)

    def reboot(self, system, user: Optional[str] = None, password: Optional[str] = None):
        """
        Reboot a system that has power management configured.

        :param system: Cobbler system
        :type system: System
        :param user: power management user
        :param password: power management password
        """

        self.power_off(system, user, password)
        time.sleep(5)
        self.power_on(system, user, password)

    def get_power_status(self, system, user: Optional[str] = None, password: Optional[str] = None) -> Optional[bool]:
        """
        Get power status for a system that has power management configured.

        :param system: Cobbler system
        :type system: System
        :param user: power management user
        :param password: power management password
        :return: if system is powered on
        """

        return self._power(system, "status", user, password)
