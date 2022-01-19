# (c) 2010
# Bill Peck <bpeck@redhat.com>
#
# License: GPLv2+

# Post install trigger for Cobbler to power cycle the guest if needed

from threading import Thread
import time


class reboot(Thread):
    def __init__(self, api, target):
        Thread.__init__(self)
        self.api = api
        self.target = target

    def run(self):
        time.sleep(30)
        self.api.reboot(self.target)


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/install/post/*"


def run(api, args) -> int:
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

    if target and "postreboot" in target.autoinstall_meta:
        # Run this in a thread so the system has a chance to finish and umount the filesystem
        current = reboot(api, target)
        current.start()

    return 0
