"""
Process management module that always restarts a service via systemd (``systemctl restart``). Select this
explicitly when you know the host uses systemd and want to skip the supervisord/systemd/SysV auto-detection
``process_management.service`` performs.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import logging
from typing import TYPE_CHECKING

from cobbler import utils

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
    Restart a service via ``systemctl restart``.

    :param api_handle: The api instance to resolve settings. Unused by this module, present to match the
                        process_management module contract.
    :param service_name: The name of the service to restart.
    :return: ``0`` on success. Any other value indicates failure.
    """
    ret = utils.subprocess_call(["systemctl", "restart", service_name], shell=False)
    if ret != 0:
        logger.error('Restarting service "%s" failed', service_name)
    return ret
