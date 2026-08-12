"""
Process management module that always restarts a service through supervisord's XML-RPC API. Select this
explicitly when you know the host manages services via supervisord and want to skip the supervisord/systemd/SysV
auto-detection ``process_management.service`` performs.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import logging
from typing import TYPE_CHECKING
from xmlrpc.client import Fault, ServerProxy

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
    Restart a service through supervisord's XML-RPC API.

    :param api_handle: The api instance to resolve settings. Unused by this module, present to match the
                        process_management module contract.
    :param service_name: The name of the service to restart.
    :return: ``0`` on success. Any other value indicates failure.
    """
    with ServerProxy("http://localhost:9001/RPC2") as server:
        process_state = (
            -1
        )  # Not redundant because we could run otherwise in an UnboundLocalError
        try:
            process_info = server.supervisor.getProcessInfo(service_name)
            if not isinstance(process_info, dict):
                raise ValueError(
                    f"Returned Process Info didn't have the expected type dict! Found type {type(process_info)}."
                )
            process_state = process_info.get("state", -1)
            if process_state in (10, 20):
                server.supervisor.stopProcess(service_name)
            if server.supervisor.startProcess(service_name):  # returns a boolean
                return 0
            logger.error('Restarting service "%s" failed', service_name)
            return 1
        except Fault as client_fault:
            logger.error(
                'Restarting service "%s" failed (supervisord process state was "%s")',
                service_name,
                process_state,
                exc_info=client_fault,
            )
            return 1
