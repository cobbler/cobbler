#!/usr/bin/env python

# This software may be freely redistributed under the terms of the GNU
# general public license.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# This script runs post install triggers in /var/lib/cobbler/triggers/install/post
# if the triggers are enabled in the settings file.
#
# (C) Tim Verhoeven <tim.verhoeven.be@gmail.com>, 2007
# tweaked: Michael DeHaan <mdehaan@redhat.com>, 2007-2008

import cgi
import cgitb
import time
import os
import sys
import socket
import xmlrpclib
from cobbler import sub_process as sub_process

COBBLER_BASE = "/var/www/cobbler"
XMLRPC_SERVER = "http://127.0.0.1/cobbler_api"

#----------------------------------------------------------------------

class ServerProxy(xmlrpclib.ServerProxy):

    def __init__(self, url=None):
        xmlrpclib.ServerProxy.__init__(self, url, allow_none=True)

#----------------------------------------------------------------------

def parse_query():
    """
    Read arguments from query string.
    """

    form = cgi.parse()

    mac = "?"

    if os.environ.has_key("X-RHN-Provisioning-MAC-0"):
        devicepair = os.environ["X-RHN-Provisioning-MAC-0"]
        mac = devicepair.split()[1].strip()

    ip = "?"
    if os.environ.has_key("REMOTE_ADDR"):
        ip = os.environ["REMOTE_ADDR"]

    name = "?"
    objtype = "?"
    if form.has_key("system"):
        name = form["system"][0]
        objtype = "system"
    elif form.has_key("profile"):
        name = form["profile"][0]
        objtype = "profile"

    mode = "?"
    if form.has_key("mode"):
        mode = form["mode"][0]

    return (mode,objtype,name,mac,ip)

def invoke(mode,objtype,name,mac,ip):
    """
    Determine if this feature is enabled.
    """
    
    xmlrpc_server = ServerProxy(XMLRPC_SERVER)
    print xmlrpc_server.run_install_triggers(mode,objtype,name,mac,ip)

    return True

#----------------------------------------------------------------------

def header():
    print "Content-type: text/plain"
    print

#----------------------------------------------------------------------

if __name__ == "__main__":
    cgitb.enable(format='text')
    header()
    (mode,objtype,name,mac,ip) = parse_query()
    invoke(mode,objtype,name,mac,ip)


