import distutils.sysconfig
import sys
import os
from utils import _
import traceback
import cexceptions
import os
import sys
import time

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

def register():
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/install/post/*"

def run(api, args, logger):
    # FIXME: make everything use the logger, no prints, use util.subprocess_call, etc

    objtype = args[0] # "system" or "profile"
    name    = args[1] # name of system or profile
    ip      = args[2] # ip or "?"

    fd = open("/var/log/cobbler/install.log","a+")
    fd.write("%s\t%s\t%s\tstop\t%s\n" % (objtype,name,ip,time.time()))
    fd.close()

    return 0
