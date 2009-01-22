#!/usr/bin/python

import os
import glob
import sys
import cobbler.api as capi

if len(sys.argv) < 3:
    print "Missing required arguments"
    sys.exit(1)

objtype = sys.argv[1] # "system" or "profile"
name    = sys.argv[2] # name of system or profile
ip      = sys.argv[3] # ip or "?"

# TODO - check if anamon is enabled first
bootapi = capi.BootAPI()
settings = bootapi.settings()
anamon_enabled = settings.anamon_enabled
print "anamon_enabled = %s" % anamon_enabled

# Remove any files matched with the given glob pattern
def unlink_files(globex):
    for f in glob.glob(globex):
        if os.path.isfile(f):
            try:
                print "unlinking '%s'" % f
                os.unlink(f)
            except OSError, e:
                print "failed to unlink '%s'" % f
                pass

if anamon_enabled in [True, 1, "1"]:
    dirname = "/var/log/cobbler/anamon/%s" % name
    if os.path.isdir(dirname):
        unlink_files(os.path.join(dirname, "*"))

# TODO - log somewhere that we cleared a systems anamon logs
sys.exit(0)
