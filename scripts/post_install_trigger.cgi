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
# tweaked: Michael DeHaan <mdehaan@redhat.com>

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

    if form.has_key("system"):
        return form["system"][0]
    return 0 

def invoke(name):
    """
    Determine if this feature is enabled.
    """
    
    xmlrpc_server = ServerProxy(XMLRPC_SERVER)
    print xmlrpc_server.run_post_install_triggers(name)

    return True

#----------------------------------------------------------------------

def header():
    print "Content-type: text/plain"
    print

#----------------------------------------------------------------------

if __name__ == "__main__":
    cgitb.enable(format='text')
    header()
    name = parse_query()
    invoke(name)


