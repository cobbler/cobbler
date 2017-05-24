"""
(C) 2008-2009, Red Hat Inc.
James Laska <jlaska@redhat.com>
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

from cobbler.cexceptions import CX


def register():
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/install/pre/*"


def run(api, args, logger):
    # FIXME: use the logger

    if len(args) < 3:
        raise CX("invalid invocation")

    # objtype = args[0]      # "system" or "profile"
    name = args[1]          # name of system or profile
    # ip = args[2]           # ip or "?"

    settings = api.settings()
    anamon_enabled = str(settings.anamon_enabled)

    # Remove any files matched with the given glob pattern
    def unlink_files(globex):
        for f in glob.glob(globex):
            if os.path.isfile(f):
                try:
                    os.unlink(f)
                except OSError:
                    pass

    if str(anamon_enabled) in ["true", "1", "y", "yes"]:
        dirname = "/var/log/cobbler/anamon/%s" % name
        if os.path.isdir(dirname):
            unlink_files(os.path.join(dirname, "*"))

    # TODO - log somewhere that we cleared a systems anamon logs
    return 0
