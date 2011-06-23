"""
Hard links cobbler content together to save space.

Copyright 2009, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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
import utils
from cexceptions import *
import clogger

class HardLinker:

    def __init__(self,config,logger=None):
        """
        Constructor
        """
        #self.config   = config
        #self.api      = config.api
        #self.settings = config.settings()
        if logger is None:
            logger       = clogger.Logger()
        self.logger      = logger
        self.distro      = utils.check_dist()
        if self.distro == "ubuntu" or self.distro == "debian":
            self.hardlink      = "/usr/bin/hardlink"
            self.hardlink_args = "-f -p -o -t -v /var/www/cobbler/ks_mirror /var/www/cobbler/repo_mirror"
        else:
            self.hardlink      = "/usr/sbin/hardlink"
            self.hardlink_args = "-c -v /var/www/cobbler/ks_mirror /var/www/cobbler/repo_mirror"
        self.hardlink_cmd = "%s %s" % (self.hardlink, self.hardlink_args)


    def run(self):
        """
        Simply hardlinks directories that are cobbler managed.
        This is a /very/ simple command but may grow more complex
        and intelligent over time.
        """

        # FIXME: if these directories become configurable some
        # changes will be required here.

        if not os.path.exists(self.hardlink):
            utils.die(self.logger,"please install 'hardlink' (%s) to use this feature" % self.hardlink)

        self.logger.info("now hardlinking to save space, this may take some time.")

        rc = utils.subprocess_call(self.logger,self.hardlink_cmd,shell=True)
        # FIXME: how about settings? (self.settings.webdir)
        webdir = "/var/www/cobbler"
        if os.path.exists("/srv/www"):
            webdir = "/srv/www/cobbler"

        rc = utils.subprocess_call(self.logger,"/usr/sbin/hardlink -c -v "+webdir+"/ks_mirror /var/www/cobbler/repo_mirror",shell=True)

        return rc

