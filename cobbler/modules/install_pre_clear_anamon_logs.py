import distutils.sysconfig
import sys
import os
from utils import _
import traceback
import cexceptions

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

import os
import glob
import sys


def register():
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/install/pre/*"

def run(api, args, logger):
    # FIXME: use the logger

    if len(args) < 3:
        raise CX("invalid invocation")

    objtype = args[0] # "system" or "profile"
    name    = args[1] # name of system or profile
    ip      = args[2] # ip or "?"

    settings = api.settings()
    anamon_enabled = str(settings.anamon_enabled)

    # Remove any files matched with the given glob pattern
    def unlink_files(globex):
        for f in glob.glob(globex):
            if os.path.isfile(f):
                try:
                    os.unlink(f)
                except OSError, e:
                    pass

    if str(anamon_enabled) in [ "true", "1", "y", "yes"]:
        dirname = "/var/log/cobbler/anamon/%s" % name
        if os.path.isdir(dirname):
            unlink_files(os.path.join(dirname, "*"))

    # TODO - log somewhere that we cleared a systems anamon logs
    return 0


