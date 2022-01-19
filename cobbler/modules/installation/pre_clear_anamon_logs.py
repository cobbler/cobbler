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
import logging
import os

from cobbler import utils
from cobbler.cexceptions import CX


PATH_PREFIX = "/var/log/cobbler/anamon/"

logger = logging.getLogger()


def register() -> str:
    """
    This pure python trigger acts as if it were a legacy shell-trigger, but is much faster. The return of this method
    indicates the trigger type.

    :return: Always ``/var/lib/cobbler/triggers/install/pre/*``
    """
    return "/var/lib/cobbler/triggers/install/pre/*"


def run(api, args) -> int:
    """
    The list of args should have one element:
        - 1: the name of the system or profile

    :param api: The api to resolve metadata with.
    :param args: This should be a list as described above.
    :return: "0" on success.
    :raises CX: Raised in case of missing arguments.
    """
    if len(args) < 3:
        raise CX("invalid invocation")

    name = args[1]

    settings = api.settings()

    # Remove any files matched with the given glob pattern
    def unlink_files(globex):
        for f in glob.glob(globex):
            if os.path.isfile(f):
                utils.rmfile(f)

    if settings.anamon_enabled:
        dirname = os.path.join(PATH_PREFIX, name)
        if os.path.isdir(dirname):
            unlink_files(os.path.join(dirname, "*"))

    logger.info('Cleared Anamon logs for "%s".', name)
    return 0
