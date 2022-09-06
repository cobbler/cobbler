"""
TODO
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Bill Peck <bpeck@redhat.com>

import glob
import os
import os.path
import logging
import pathlib


class LogTool:
    """
    Helpers for dealing with System logs, anamon, etc..
    """

    def __init__(self, system, api):
        """
        Log library constructor requires a Cobbler system object.
        """
        self.system = system
        self.api = api
        self.settings = api.settings()
        self.logger = logging.getLogger()

    def clear(self):
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
                with open(log, "w") as f:
                    f.truncate()
            except IOError as e:
                self.logger.info("Failed to Truncate '%s':%s " % (log, e))
            except OSError as e:
                self.logger.info("Failed to Truncate '%s':%s " % (log, e))
