#!/usr/bin/python

import os
import glob
import sys
import xmlrpclib

server = xmlrpclib.Server("http://127.0.0.1/cobbler_api")

if len(sys.argv) < 3:
    sys.exit(1)

objtype = sys.argv[1] # "system" or "profile"
name    = sys.argv[2] # name of system or profile
ip      = sys.argv[3] # ip or "?"

settings = server.get_settings()
anamon_enabled = str(settings.get("anamon_enabled",0))

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
sys.exit(0)
