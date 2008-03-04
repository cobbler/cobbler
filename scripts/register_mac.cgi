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
# script to auto add systems who make a wget into cobbler.
# right now it requires "kssendmac" in kernel options and takes only 1 arg
# ex: wget http://cobbler.example.org/cgi-bin/regsister_mac?profile=foo
# suitable to be called from kickstart,etc

import cgi
#import cgitb
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
    mac = autodetect()
    print "# incoming profile = %s" % profile
    return (mac,profile)

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
        print "# discovered MAC: %s" % mac.lower()
        return mac.lower()
    else:
        print "# missing kssendmac in the kernel args?  Can't continue."
        return "BB:EE:EE:EE:EE:FF"

#----------------------------------------------------------------------
    

def make_change(server,mac,profile,token):
    print "# getting handle for: %s" % mac

    systems = server.get_systems()
    for s in systems:
       for i in s["interfaces"]:
           if s["interfaces"][i]["mac_address"].lower() == mac.lower():
              print "# found an existing record, will not continue"
              return

    # good, no system found, so we can add a new one.
    print "# creating new system record"
    handle = server.new_system(token)
    server.modify_system(handle,"profile",profile,token)
    server.modify_system(handle,"name",mac.replace(":","_"),token)
    intf_hash = {
        # FIXME: also include IP info if we have it?
        "macaddress-intf0" : mac
    }
    server.modify_system(handle,"modify-interface",intf_hash,token)
    print "# saving system"
    server.save_system(handle,token)

#----------------------------------------------------------------------

def header():
    print "Content-type: text/plain"
    print

#----------------------------------------------------------------------

if __name__ == "__main__":
    #cgitb.enable(format='text')
    header()
    server = ServerProxy(XMLRPC_SERVER)
    token = server.login(USERNAME,PASSWORD)
    (mac, profile) = parse_query()
    print "# running for %s %s" % (mac,profile)
    make_change(server,mac,profile,token)

