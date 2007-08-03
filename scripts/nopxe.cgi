#!/usr/bin/env python

# This software may be freely redistributed under the terms of the GNU
# general public license.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# This script disables the netboot flag for a given
# system if (and only if) pxe_just_once is enabled in settings.
# It must not be able to do anything else for security
# reasons.
#
#
# (C) Red Hat, 2007 
# Michael DeHaan <mdehaan@redhat.com>
#

import cgi
import cgitb
import time
import os
import sys
import socket
import xmlrpclib
from cobbler import sub_process as sub_process

COBBLER_BASE = "/var/www/cobbler"
XMLRPC_SERVER = "http://127.0.0.1:25151"

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

def disable(name):
    """
    Determine if this feature is enabled.
    """
    
    #try:
    xmlrpc_server = ServerProxy(XMLRPC_SERVER)
    print xmlrpc_server.disable_netboot(name)
    #except:
    #    print "# could not contact cobblerd at %s" % XMLRPC_SERVER
    #    sys.exit(1)

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
    disable(name)


