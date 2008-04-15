#!/usr/bin/python

import os
import sys
import time

objtype = sys.argv[1] # "system" or "profile"
name    = sys.argv[2] # name of system or profile
mac     = sys.argv[3] # mac or "?"
ip      = sys.argv[4] # ip or "?"

fd = open("/var/log/cobbler/install.log","a+")
fd.write("%s\t%s\t%s\t%s\tstart\t%s\n" % (objtype,name,mac,ip,time.time()))
fd.close()

sys.exit(0)
