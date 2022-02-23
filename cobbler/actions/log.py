"""

Copyright 2009, Red Hat, Inc and Others
Bill Peck <bpeck@redhat.com>

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
        anamon_dir = pathlib.Path('/var/log/cobbler/anamon/').joinpath(self.system.name)
        if anamon_dir.is_dir():
            logs = list(filter(os.path.isfile, glob.glob(str(anamon_dir.joinpath('*')))))
        else:
            logs = []
            logging.info("No log-files found to delete for system: %s", self.system.name)

        for log in logs:
            try:
                with open(log, 'w') as f:
                    f.truncate()
            except IOError as e:
                self.logger.info("Failed to Truncate '%s':%s " % (log, e))
            except OSError as e:
                self.logger.info("Failed to Truncate '%s':%s " % (log, e))
