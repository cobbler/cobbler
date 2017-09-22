"""

Copyright 2009, Red Hat, Inc
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


import os
import os.path
import sys
import traceback
import clogger

import utils
from cexceptions import *
import glob

class LogTool:
    """
    Helpers for dealing with System logs, consoles, anamon, etc..
    """

    def __init__(self,config,system,api,logger=None):
        """
        Log library constructor requires a cobbler system object.
        """
        self.system      = system
        self.config      = config
        self.settings    = config.settings()
        self.api         = api
        if logger is None:
            logger = clogger.Logger()
        self.logger      = logger


    def clear(self):
        """
        Clears the system logs
        """
 
        consoles = self.settings.consoles
        logs = filter(os.path.isfile, 
                      glob.glob('%s/%s' % (consoles, self.system.name)))
        anamon_dir = '/var/log/cobbler/anamon/%s' % self.system.name
        if os.path.isdir(anamon_dir):
            logs.extend(filter(os.path.isfile, glob.glob('%s/*' % anamon_dir)))
        for log in logs:
            try:
                f = open(log, 'w')
                f.truncate()
                f.close()
            except IOError, e:
                self.logger.info("Failed to Truncate '%s':%s " % (log, e))
            except OSError, e:
                self.logger.info("Failed to Truncate '%s':%s " % (log, e))
        return 0

