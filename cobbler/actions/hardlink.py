"""
Hard links Cobbler content together to save space.

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

from builtins import object
import os
from cobbler import utils

from cobbler import clogger


class HardLinker(object):

    def __init__(self, collection_mgr, logger=None):
        """
        Constructor
        """
        # self.collection_mgr   = collection_mgr
        # self.api      = collection_mgr.api
        # self.settings = collection_mgr.settings()
        self.hardlink = None
        if logger is None:
            logger = clogger.Logger()
        self.logger = logger
        self.family = utils.get_family()

        # Getting the path to hardlink
        for possible_location in ["/usr/bin/hardlink", "/usr/sbin/hardlink"]:
            if os.path.exists(possible_location):
                self.hardlink = possible_location
        if not self.hardlink:
            utils.die(self.logger, "please install 'hardlink' to use this feature")

        # Setting the args for hardlink accodring to the distribution
        if self.family == "debian":
            self.hardlink_args = "-f -p -o -t -v /var/www/cobbler/distro_mirror /var/www/cobbler/repo_mirror"
        elif self.family == "suse":
            self.hardlink_args = "-f -v /var/www/cobbler/distro_mirror /var/www/cobbler/repo_mirror"
        else:
            self.hardlink_args = "-c -v /var/www/cobbler/distro_mirror /var/www/cobbler/repo_mirror"
        self.hardlink_cmd = "%s %s" % (self.hardlink, self.hardlink_args)

    def run(self):
        """
        Simply hardlinks directories that are Cobbler managed.
        This is a /very/ simple command but may grow more complex
        and intelligent over time.
        """

        # FIXME: if these directories become configurable some
        # changes will be required here.

        self.logger.info("now hardlinking to save space, this may take some time.")

        rc = utils.subprocess_call(self.logger, self.hardlink_cmd, shell=True)
        # FIXME: how about settings? (self.settings.webdir)
        webdir = "/var/www/cobbler"
        if os.path.exists("/srv/www"):
            webdir = "/srv/www/cobbler"

        rc = utils.subprocess_call(self.logger, self.hardlink + " -c -v " + webdir + "/distro_mirror /var/www/cobbler/repo_mirror", shell=True)

        return rc
