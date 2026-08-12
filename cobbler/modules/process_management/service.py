"""
Default/backward-compatible process management module. Restarts services the way Cobbler always has: via
supervisord, systemd or SysV. This is the module used when cobblerd and the managed services (DHCP, DNS, ...) run
in the same process namespace/host.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import logging
from typing import TYPE_CHECKING

from cobbler import utils
from cobbler.modules.process_management import detection, supervisor, systemd

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI

logger = logging.getLogger()


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always "process_management"
    """
    return "process_management"


def restart_service(api_handle: "CobblerAPI", service_name: str) -> int:
    """
    Restart a service via the traditional, non-containerized process managers (supervisord, systemd, SysV).
    Checks which manager is present is done in the order just described, delegating to
    process_management.supervisor/process_management.systemd for the first two so that behavior stays identical
    whether a manager is auto-detected here or selected explicitly via those modules.

    :param api_handle: The api instance to resolve settings. Unused by this module, present to match the
                        process_management module contract.
    :param service_name: The name of the service to restart.
    :return: ``0`` on success. Any other value indicates failure.
    """
    if detection.is_supervisord():
        return supervisor.restart_service(api_handle, service_name)
    if detection.is_systemd():
        return systemd.restart_service(api_handle, service_name)
    if detection.is_service():
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
