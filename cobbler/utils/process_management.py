"""
TODO
"""

import logging
import os
import xmlrpc
from xmlrpc.client import ServerProxy

from cobbler import utils

logger = logging.getLogger()


def is_systemd() -> bool:
    """
    Return whether this system uses systemd.

    This method currently checks if the path ``/usr/lib/systemd/systemd`` exists.
    """
    return os.path.exists("/usr/lib/systemd/systemd")


def is_supervisord() -> bool:
    """
    Return whether this system uses supervisord.

    This method currently checks if there is a running supervisord instance on ``localhost``.
    """
    with ServerProxy("http://localhost:9001/RPC2") as server:
        try:
            server.supervisor.getState()
        except OSError:
            return False
        return True


def is_service() -> bool:
    """
    Return whether this system uses service.

    This method currently checks if the path ``/usr/sbin/service`` exists.
    """
    return os.path.exists("/usr/sbin/service")


def service_restart(service_name: str):
    """
    Restarts a daemon service independent of the underlining process manager. Currently, supervisord, systemd and SysV
    are supported. Checks which manager is present is done in the order just described.

    :param service_name: The name of the service
    :returns: If the system is SystemD or SysV based the return code of the restart command.
    """
    if is_supervisord():
        with ServerProxy("http://localhost:9001/RPC2") as server:
            try:
                process_state = (
                    -1
                )  # Not redundant because we could run otherwise in an UnboundLocalError
                process_state = server.supervisor.getProcessInfo(service_name).get(
                    "state"
                )
                if process_state in (10, 20):
                    server.supervisor.stopProcess(service_name)
                if server.supervisor.startProcess(service_name):  # returns a boolean
                    return 0
                logger.error('Restarting service "%s" failed', service_name)
                return 1
            except xmlrpc.client.Fault as client_fault:
                logger.error(
                    'Restarting service "%s" failed (supervisord process state was "%s")',
                    service_name,
                    process_state,
                    exc_info=client_fault,
                )
                return 1
    elif is_systemd():
        restart_command = ["systemctl", "restart", service_name]
    elif is_service():
        restart_command = ["service", service_name, "restart"]
    else:
        logger.warning(
            'We could not restart service "%s" due to an unsupported process manager!',
            service_name,
        )
        return 1

    ret = utils.subprocess_call(restart_command, shell=False)
    if ret != 0:
        logger.error('Restarting service "%s" failed', service_name)
    return ret
