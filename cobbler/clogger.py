"""
Python standard logging doesn't super-intelligent and won't expose filehandles,
which we want.  So we're not using it.

Copyright 2009, Red Hat, Inc and Others
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

import logging
import logging.config
import os

# Temporary hack, a clean solution seems to be tricky.
# Defining a variable in our Apache startup code seem not to work, it is still set later when this code is executed via
# Cobbler.

# This is necessary to prevent apache to try to access the file
if os.geteuid() == 0:
    logging.config.fileConfig('/etc/cobbler/logging_config.conf')


class Logger:
    """
    Logger class for Cobbler which is wrapped around the Python3 standard logger.

    Please don't use this. Utilize the standard logger from Python3 so we can get rid of this eventually.
    """
    def __init__(self, logfile=None):
        """
        The default constructor.

        :param logfile: If this argument is passed, then the log will not be written to the default location.
        :type logfile: str
        """
        if not logfile:
            self.logger = logging.getLogger('root')
        else:
            self.logger = logging.getLogger(str(id(self)))
            self.logger.propagate = False
            self.logger.addHandler(logging.FileHandler(filename=logfile))

    def critical(self, msg: str):
        """
        A critical message which is related to a problem which will halt Cobbler.

        :param msg: The message to be logged.
        """
        self.logger.critical(msg)

    def error(self, msg: str):
        """
        An error message which means that Cobbler will not halt but the future actions may not be executed correctly.

        :param msg: The message to be logged.
        """
        self.logger.error(msg)

    def warning(self, msg: str):
        """
        A warning message which could possibly indicate performance or functional problems.

        :param msg: The message to be logged.
        """
        self.logger.warning(msg)

    def info(self, msg: str):
        """
        An informational message which should be written to the target log.

        :param msg: The message to be logged.
        """
        self.logger.info(msg)

    def debug(self, msg: str):
        """
        A message which is useful for finding errors or performance problems. Should not be visible in the production
        usage of Cobbler.

        :param msg: The message to be logged.
        """
        self.logger.debug(msg)

    def flat(self, msg: str):
        """
        This uses the print function from the std library. Avoid using this. This is only used for the report command
        in ``cobbler/actions/report.py``

        :param msg: The message to be logged.
        """
        print(msg)
