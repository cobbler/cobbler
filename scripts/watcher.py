# cobbler mod_python handler for observing kickstart activity
# 
# Copyright 2007, Red Hat, Inc
# Michael DeHaan <mdehaan@redhat.com>
# 
# This software may be freely redistributed under the terms of the GNU
# general public license.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import time
from mod_python import apache

def outputfilter(filter):


    # extract important info    
    request = filter.req
    connection = request.connection
    (address,port) = connection.remote_addr

    # open the logfile (directory be set writeable by installer)
    logfile = open("/var/log/cobbler/kicklog/%s" % address,"a+")

    log_it = True
    if request.the_request.find("cobbler_track") == -1 and request.the_request.find("ctr/") == -1":
        log_it = False

    if log_it:
        # write the timestamp
        t = time.localtime()
        seconds = str(time.mktime(t))
        logfile.write(seconds)
        logfile.write("\t")
        timestr = str(time.asctime(t))
        logfile.write(timestr)
        logfile.write("\t")

        # write the IP address of the client
        logfile.write(address)
        logfile.write("\t")

        # write the filename being requested
        logfile.write(request.the_request)
        # logfile.write(request.filename)
        logfile.write("\n")

    # if requesting this file, don't return it
    if request.the_request.find("watcher.py") != -1:
        filter.close()
        return

    # pass-through filter
    s = filter.read()
    while s:
        filter.write(s)
        s = filter.read()
    if s is None:
        filter.close()
    logfile.close()

