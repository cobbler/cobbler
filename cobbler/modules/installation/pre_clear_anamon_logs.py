"""
Cobbler Module Trigger that will clear the anamon logs.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2008-2009, Red Hat Inc.
# SPDX-FileCopyrightText: James Laska <jlaska@redhat.com>
# SPDX-FileCopyrightText: Bill Peck <bpeck@redhat.com>

import glob
import logging
import os
from typing import TYPE_CHECKING, List

from cobbler.cexceptions import CX
from cobbler.utils import filesystem_helpers

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


PATH_PREFIX = "/var/log/cobbler/anamon/"

logger = logging.getLogger()


def register() -> str:
    """
    This pure python trigger acts as if it were a legacy shell-trigger, but is much faster. The return of this method
    indicates the trigger type.

    :return: Always ``/var/lib/cobbler/triggers/install/pre/*``
    """
    return "/var/lib/cobbler/triggers/install/pre/*"


def run(api: "CobblerAPI", args: List[str]) -> int:
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
    def unlink_files(globex: str) -> None:
        for file in glob.glob(globex):
            if os.path.isfile(file):
                filesystem_helpers.rmfile(file)

    if settings.anamon_enabled:
        dirname = os.path.join(PATH_PREFIX, name)
        if os.path.isdir(dirname):
            unlink_files(os.path.join(dirname, "*"))

    logger.info('Cleared Anamon logs for "%s".', name)
    return 0
