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

def run(api, args):
    objtype = args[1] # "system" or "profile"
    name    = args[2] # name of system or profile
    ip      = args[3] # ip or "?"

    fd = open("/var/log/cobbler/install.log","a+")
    fd.write("%s\t%s\t%s\tstop\t%s\n" % (objtype,name,ip,time.time()))
    fd.close()

    return 0
