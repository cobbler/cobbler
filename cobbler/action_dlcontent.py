"""
Downloads bootloader content for all arches for when the user doesn't want to supply their own.

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
import urlgrabber
import clogger

class ContentDownloader:

   def __init__(self,config,logger=None):
       """
       Constructor
       """
       self.config   = config
       self.settings = config.settings()
       if logger is None:
           logger       = clogger.Logger()
       self.logger      = logger


   def run(self,force=False):
       """
       Download bootloader content for all of the latest bootloaders, since the user
       has chosen to not supply their own.  You may ask "why not get this from yum", though
       Fedora has no IA64 repo, for instance, and we also want this to be able to work on Debian and
       further do not want folks to have to install a cross compiler.  For those that don't like this approach
       they can still source their cross-arch bootloader content manually.
       """

       content_server = "http://dgoodwin.fedorapeople.org/loaders"
       dest = "/var/lib/cobbler/loaders"

       files = (
          ( "%s/README" % content_server, "%s/README" % dest ),
          ( "%s/COPYING.elilo" % content_server, "%s/COPYING.elilo" % dest ),
          ( "%s/COPYING.yaboot" % content_server, "%s/COPYING.yaboot" % dest),
          ( "%s/COPYING.syslinux" % content_server, "%s/COPYING.syslinux" % dest),
          ( "%s/elilo-3.8-ia64.efi" % content_server, "%s/elilo-ia64.efi" % dest ),
          ( "%s/yaboot-1.3.14-12" % content_server, "%s/yaboot" % dest),
          ( "%s/pxelinux.0-3.61" % content_server, "%s/pxelinux.0" % dest),
          ( "%s/menu.c32-3.61" % content_server, "%s/menu.c32" % dest),
          ( "%s/grub-0.97-x86.efi" % content_server, "%s/grub-x86.efi" % dest),
          ( "%s/grub-0.97-x86_64.efi" % content_server, "%s/grub-x86_64.efi" % dest),
       )

       self.logger.info("downloading content required to netboot all arches")
       for f in files:
          src = f[0]
          dst = f[1]
          if os.path.exists(dst) and not force:
             self.logger.info("path %s already exists, not overwriting existing content, use --force if you wish to update" % dst)
             continue
          self.logger.info("downloading %s to %s" % (src,dst))
          urlgrabber.urlgrab(src,dst)

       return True

