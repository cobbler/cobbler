# (c) 2010
# Bill Peck <bpeck@redhat.com>
#
# License: GPLv2+

# Post install trigger for cobbler to
# power cycle the guest if needed

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


def register():
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/install/post/*"


def run(api, args, logger):
    # FIXME: make everything use the logger

    objtype = args[0]   # "target" or "profile"
    name = args[1]      # name of target or profile
    # boot_ip = args[2] # ip or "?"

    if objtype == "system":
        target = api.find_system(name)
    else:
        return 0

    if target and 'postreboot' in target.autoinstall_meta:
        # Run this in a thread so the system has a chance to finish and umount the filesystem
        current = reboot(api, target)
        current.start()

    return 0
