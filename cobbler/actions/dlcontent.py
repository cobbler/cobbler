"""
Downloads bootloader content for all arches for when the user doesn't want to supply their own.

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

from cobbler import clogger
from cobbler import download_manager


class ContentDownloader(object):

    def __init__(self, collection_mgr, logger=None):
        """
        Constructor

        :param collection_mgr: The main collection manager instance which is used by the current running server.
        :param logger: The logger object which logs to the desired target.
        """
        self.collection_mgr = collection_mgr
        self.settings = collection_mgr.settings()
        if logger is None:
            logger = clogger.Logger()
        self.logger = logger

    def run(self, force=False):
        """
        Download bootloader content for all of the latest bootloaders, since the user has chosen to not supply their
        own. You may ask "why not get this from yum", we also want this to be able to work on Debian and further do not
        want folks to have to install a cross compiler. For those that don't like this approach they can still source
        their cross-arch bootloader content manually.

        :param force: If the target path should be overwritten, even if there are already files present.
        :type force: bool
        """

        content_server = "https://cobbler.github.io/loaders"
        dest = "/var/lib/cobbler/loaders"

        files = (
            ("%s/README" % content_server, "%s/README" % dest),
            ("%s/COPYING.yaboot" % content_server, "%s/COPYING.yaboot" % dest),
            ("%s/COPYING.syslinux" % content_server, "%s/COPYING.syslinux" % dest),
            ("%s/yaboot-1.3.17" % content_server, "%s/yaboot" % dest),
            ("%s/pxelinux.0-3.86" % content_server, "%s/pxelinux.0" % dest),
            ("%s/menu.c32-3.86" % content_server, "%s/menu.c32" % dest),
            ("%s/grub-0.97-x86.efi" % content_server, "%s/grub-x86.efi" % dest),
            ("%s/grub-0.97-x86_64.efi" % content_server, "%s/grub-x86_64.efi" % dest),
        )

        dlmgr = download_manager.DownloadManager(self.collection_mgr, self.logger)
        for src, dst in files:
            if os.path.exists(dst) and not force:
                self.logger.info("path %s already exists, not overwriting existing content, use --force if you wish to update" % dst)
                continue
            self.logger.info("downloading %s to %s" % (src, dst))
            dlmgr.download_file(src, dst)

# EOF
