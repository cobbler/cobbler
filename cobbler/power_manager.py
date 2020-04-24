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

from builtins import range
from builtins import object
import glob
import os
from pathlib import Path
import stat
import re
import time

from cobbler.cexceptions import CX
from cobbler import clogger
from cobbler import utils

# Try the power command 3 times before giving up.
# Some power switches are flakey

POWER_RETRIES = 3


def get_power_types():
    """
    Get possible power management types.

    :returns: Possible power management types
    :rtype: list
    """

    power_types = []
    fence_files = glob.glob("/usr/sbin/fence_*") + glob.glob("/sbin/fence_*")
    for x in fence_files:
        fence_name = os.path.basename(x).replace("fence_", "")
        if fence_name not in power_types:
            power_types.append(fence_name)
    power_types.sort()
    return power_types


def validate_power_type(power_type):
    """
    Check if a power management type is valid.

    :param power_type: Power management type.
    :type power_type: str
    :raise CX: if power management type is invalid
    """

    power_types = get_power_types()
    if not power_types:
        raise CX("you need to have fence-agents installed")
    if power_type not in power_types:
        raise CX("power management type must be one of: %s" % ",".join(power_types))


def get_power_command(power_type):
    """
    Get power management command path

    :param power_type: power management type
    :type power_type: str
    :returns: power management command path
    :rtype: str or None
    """

    if power_type:
        # try /sbin, then /usr/sbin
        power_path1 = "/sbin/fence_%s" % power_type
        power_path2 = "/usr/sbin/fence_%s" % power_type
        for power_path in (power_path1, power_path2):
            if os.path.isfile(power_path) and os.access(power_path, os.X_OK):
                return power_path
    return None


class PowerManager(object):
    """
    Handles power management in systems
    """

    def __init__(self, api, collection_mgr, logger=None):
        """
        Constructor

        :param api: Cobbler API
        :type api: CobblerAPI
        :param collection_mgr: collection manager
        :type collection_mgr: CollectionManager
        :param logger: A logger object to audit the actions of the object instance.
        :type logger: Logger
        """

        self.collection_mgr = collection_mgr
        self.settings = collection_mgr.settings()
        self.api = api
        if logger is None:
            logger = clogger.Logger()
        self.logger = logger

    def _check_power_conf(self, system, logger, user, password):
        """
        Prints a warning for invalid power configurations.

        :param user: The username for the power command of the system. This overrules the one specified in the system.
        :param password: The password for the power command of the system. This overrules the one specified in the
                         system.
        :param system: Cobbler system
        :type system: System
        :param logger: logger
        :type logger: Logger
        """

        if (system.power_pass or password) and system.power_identity_file:
            logger.warning("Both password and identity-file are specified")
        if system.power_identity_file:
            ident_path = Path(system.power_identity_file)
            if not ident_path.exists():
                logger.warning("identity-file " + system.power_identity_file + " does not exist")
            else:
                ident_stat = stat.S_IMODE(ident_path.stat().st_mode)
                if (ident_stat & stat.S_IRWXO) or (ident_stat & stat.S_IRWXG):
                    logger.warning("identity-file " + system.power_identity_file +
                                   " must not be read/write/exec by group or others")
        if not system.power_address:
            logger.warning("power-address is missing")
        if not (system.power_user or user):
            logger.warning("power-user is missing")
        if not (system.power_pass or password) and not system.power_identity_file:
            logger.warning("neither power-identity-file nor power-password specified")

    def _get_power_input(self, system, power_operation, logger, user, password):
        """
        Creates an option string for the fence agent from the system data. This is an internal method.

        :param system: Cobbler system
        :type system: System
        :param power_operation: power operation. Valid values: on, off, status. Rebooting is implemented as a set of 2
                                operations (off and on) in a higher level method.
        :type power_operation: str
        :param logger: logger
        :type logger: Logger
        :param user: user to override system.power_user
        :type user: str
        :param password: password to override system.power_pass
        :type password: str
        :return: The option string for the fencer agent.
        :rtype: str
        """

        self._check_power_conf(system, logger, user, password)
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

    def _power(self, system, power_operation, user=None, password=None, logger=None):
        """
        Performs a power operation on a system.
        Internal method

        :param system: Cobbler system
        :type system: System
        :param power_operation: power operation. Valid values: on, off, status. Rebooting is implemented as a set of 2
                                operations (off and on) in a higher level method.
        :type power_operation: str
        :param user: power management user. If user and password are not supplied, environment variables
                     COBBLER_POWER_USER and COBBLER_POWER_PASS will be used.
        :type user: str
        :param password: power management password
        :type password: str
        :param logger: logger
        :type logger: Logger
        :return: bool/None if power operation is 'status', return if system is on; otherwise, return None
        :rtype: bool or None
        :raise CX: if there are errors
        """

        if logger is None:
            logger = self.logger

        power_command = get_power_command(system.power_type)
        if not power_command:
            utils.die(logger, "no power type set for system")

        meta = utils.blender(self.api, False, system)
        meta["power_mode"] = power_operation

        logger.info("cobbler power configuration is:")
        logger.info("      type   : %s" % system.power_type)
        logger.info("      address: %s" % system.power_address)
        logger.info("      user   : %s" % system.power_user)
        logger.info("      id     : %s" % system.power_id)
        logger.info("      options: %s" % system.power_options)
        logger.info("identity_file: %s" % system.power_identity_file)

        # if no username/password data, check the environment
        if not system.power_user and not user:
            user = os.environ.get("COBBLER_POWER_USER", "")
        if not system.power_pass and not password:
            password = os.environ.get("COBBLER_POWER_PASS", "")

        power_input = self._get_power_input(system, power_operation, logger, user, password)

        logger.info("power command: %s" % power_command)
        logger.info("power command input: %s" % power_input)

        for x in range(0, POWER_RETRIES):
            output, rc = utils.subprocess_sp(logger, power_command, shell=False, input=power_input)
            # fencing agent returns 2 if the system is powered off
            if rc == 0 or (rc == 2 and power_operation == 'status'):
                # If the desired state is actually a query for the status
                # return different information than command return code
                if power_operation == 'status':
                    match = re.match(r'^(Status:|.+power\s=)\s(on|off)$', output, re.IGNORECASE | re.MULTILINE)
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

        :param system: Cobbler system
        :type system: System
        :param user: power management user
        :type user: str
        :param password: power management password
        :type password: str
        :param logger: logger
        :type logger: Logger
        """

        self._power(system, "on", user, password, logger)

    def power_off(self, system, user=None, password=None, logger=None):
        """
        Powers down a system that has power management configured.

        :param system: Cobbler system
        :type system: System
        :param user: power management user
        :type user: str
        :param password: power management password
        :type password: str
        :param logger: logger
        :type logger: Logger
        """

        self._power(system, "off", user, password, logger)

    def reboot(self, system, user=None, password=None, logger=None):
        """
        Reboot a system that has power management configured.

        :param system: Cobbler system
        :type system: System
        :param user: power management user
        :type user: str
        :param password: power management password
        :type password: str
        :param logger: logger
        :type logger: Logger
        """

        self.power_off(system, user, password, logger=logger)
        time.sleep(5)
        self.power_on(system, user, password, logger=logger)

    def get_power_status(self, system, user=None, password=None, logger=None):
        """
        Get power status for a system that has power management configured.

        :param system: Cobbler system
        :type system: System
        :param user: power management user
        :type user: str
        :param password: power management password
        :type password: str
        :param logger: logger
        :type logger: Logger
        :return: if system is powered on
        :rtype: bool
        """

        return self._power(system, "status", user, password, logger)
