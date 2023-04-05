"""
Cobbler Trigger Module that managed the logs associated with a Cobbler system.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Bill Peck <bpeck@redhat.com>

import glob
import logging
import os
import os.path
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.system import System


class LogTool:
    """
    Helpers for dealing with System logs, anamon, etc..
    """

    def __init__(self, system: "System", api: "CobblerAPI"):
        """
        Log library constructor requires a Cobbler system object.
        """
        self.system = system
        self.api = api
        self.settings = api.settings()
        self.logger = logging.getLogger()

    def clear(self) -> None:
        """
        Clears the system logs
        """
        anamon_dir = pathlib.Path("/var/log/cobbler/anamon/").joinpath(self.system.name)
        if anamon_dir.is_dir():
            logs = list(
                filter(os.path.isfile, glob.glob(str(anamon_dir.joinpath("*"))))
            )
        else:
            logs = []
            logging.info(
                "No log-files found to delete for system: %s", self.system.name
            )

        for log in logs:
            try:
                with open(log, "w", encoding="UTF-8") as log_fd:
                    log_fd.truncate()
            except IOError as error:
                self.logger.info("Failed to Truncate '%s':%s ", log, error)
