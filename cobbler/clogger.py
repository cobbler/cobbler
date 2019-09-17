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

# Temporary hack, a clean solution seems to be tricky
# Defining a variable in our Apache startup code seem not to
# it is still set later when this code is executed via cobbler

# This is necessary to prevent apache to try to access the file
if os.access("/var/log/cobbler/cobbler.log", os.W_OK):
    logging.config.fileConfig('/etc/cobbler/logging_config.conf')


class Logger(object):
    def __init__(self, logfile=None):
        if not logfile:
            self.logger = logging.getLogger('root')
        else:
            self.logger = logging.getLogger(str(id(self)))
            self.logger.propagate = False
            self.logger.addHandler(logging.FileHandler(filename=logfile))

    def critical(self, msg):
        self.logger.critical(msg)

    def error(self, msg):
        self.logger.error(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def info(self, msg):
        self.logger.info(msg)

    def debug(self, msg):
        self.logger.debug(msg)

    def flat(self, msg):
        print(msg)
