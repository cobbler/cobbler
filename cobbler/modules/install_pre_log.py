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
    return "/var/lib/cobbler/triggers/install/pre/*"

def run(api, args):
    objtype = args[0] # "system" or "profile"
    name    = args[1] # name of system or profile
    ip      = args[2] # ip or "?"

    fd = open("/var/log/cobbler/install.log","a+")
    fd.write("%s\t%s\t%s\tstart\t%s\n" % (objtype,name,ip,time.time()))
    fd.close()

    return 0
