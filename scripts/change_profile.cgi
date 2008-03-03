#!/usr/bin/env python

# Michael DeHaan <mdehaan@redhat.com>
# (C) 2008 Red Hat Inc
#
# This software may be freely redistributed under the terms of the GNU
# general public license.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# what is this?  This is a 
# script to change cobbler profiles for the requestor
# from one profile to another, as specified by ?profile=foo
# ex: wget http://cobbler.example.org/cgi-bin/change_profile.cgi?profile=foo
# suitable to be called from kickstart,etc

import cgi
import cgitb
import time
import os
import sys
import socket
import xmlrpclib

# FIXME: edit these two variables to match your webui configuration
USERNAME = "cobbler"
PASSWORD = "cobbler"

COBBLER_BASE = "/var/www/cobbler"
XMLRPC_SERVER = "http://127.0.0.1/cobbler_api_rw"
DEFAULT_PROFILE = "default"

#----------------------------------------------------------------------

class ServerProxy(xmlrpclib.ServerProxy):

    def __init__(self, url=None):
        xmlrpclib.ServerProxy.__init__(self, url, allow_none=True)

#----------------------------------------------------------------------

def parse_query():

    form = cgi.parse()

    if form.has_key("profile"):
        profile = form["profile"][0]
    else:
        profile = DEFAULT_PROFILE
    system = autodetect()
    print "# incoming profile = %s" % profile
    print "# incoming system = %s" % system
    return (system["name"],profile)

#----------------------------------------------------------------------

def autodetect():

    # connect to cobblerd and get the list of systems
    
    try:
        xmlrpc_server = ServerProxy(XMLRPC_SERVER)
        systems = xmlrpc_server.get_systems()
    except:
        print "# could not contact cobblerd at %s" % XMLRPC_SERVER
        sys.exit(1)

    # if kssendmac was in the kernel options line, see
    # if a system can be found matching the MAC address.  This
    # is more specific than an IP match.

    if os.environ.has_key("HTTP_X_RHN_PROVISIONING_MAC_0"):
        # FIXME: will not key off other NICs
        devicepair = os.environ["HTTP_X_RHN_PROVISIONING_MAC_0"]
        mac = devicepair.split()[1].strip()
        # mac is the macaddress of the first nic reported by anaconda
        candidates = [system['name'] for system in systems if system['mac_address'].lower() == mac.lower()]
        if len(candidates) == 0:
	    print "# no system entries with MAC %s found" % mac
	    print "# trying IP lookup"
        elif len(candidates) > 1:
	    print "# multiple system entries with MAC %s found" % mac
	    sys.exit(1)
        elif len(candidates) == 1:
            print "# kickstart matched by MAC: %s" % mac
	    return candidates[0]

    # attempt to match by the IP.
    
    try:
        ip = os.environ["REMOTE_ADDR"]
    except:
        ip = "127.0.0.1" 

    candidates = []
    for x in systems:
        for y in x["interfaces"]:
            if x["interfaces"][y]["ip_address"] == ip:
                candidates.append(x)

    if len(candidates) == 0:
        print "# no system entries with ip %s found" % ip
        sys.exit(1)
    elif len(candidates) > 1:
        print "# multiple system entries with ip %s found" % ip
        sys.exit(1)
    elif len(candidates) == 1:
        return candidates[0]

#----------------------------------------------------------------------
    

def make_change(server,system,profile,token):
    print "# getting handle for: %s" % system
    handle = server.get_system_handle(system,token)
    print "# modifying system %s to %s" % (system,profile)
    server.modify_system(handle,"profile",profile,token)
    print "# saving system"
    server.save_system(handle,token)

#----------------------------------------------------------------------

def header():
    print "Content-type: text/plain"
    print

#----------------------------------------------------------------------

if __name__ == "__main__":
    cgitb.enable(format='text')
    header()
    server = ServerProxy(XMLRPC_SERVER)
    token = server.login(USERNAME,PASSWORD)
    (system, profile) = parse_query()
    print "# running for %s %s" % (system,profile)
    try:
       ip = os.environ["REMOTE_ADDR"]
    except:
       ip = "???"
    print "# requestor ip = %s" % ip
    print "# ============================="
    print "# system name = %s" % system
    make_change(server,system,profile,token)

