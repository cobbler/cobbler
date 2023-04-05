"""
Post install trigger for Cobbler to power cycle the guest if needed
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2010 Bill Peck <bpeck@redhat.com>

import time
from threading import Thread
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.system import System


class RebootSystemThread(Thread):
    """
    TODO
    """

    def __init__(self, api: "CobblerAPI", target: "System"):
        Thread.__init__(self)
        self.api = api
        self.target = target

    def run(self) -> None:
        time.sleep(30)
        self.api.power_system(self.target, "reboot")


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/install/post/*"


def run(api: "CobblerAPI", args: List[str]) -> int:
    """
    Obligatory trigger hook.

    :param api: The api to resolve information with.
    :param args: This is an array containing two objects.
                 0: The str "system". All other content will result in an early exit of the trigger.
                 1: The name of the target system.
    :return: ``0`` on success.
    """
    objtype = args[0]
    name = args[1]

    if objtype == "system":
        target = api.find_system(name)
    else:
        return 0

    if isinstance(target, list):
        raise ValueError("Ambigous match for search result!")

    if target and "postreboot" in target.autoinstall_meta:
        # Run this in a thread so the system has a chance to finish and umount the filesystem
        current = RebootSystemThread(api, target)
        current.start()

    return 0
