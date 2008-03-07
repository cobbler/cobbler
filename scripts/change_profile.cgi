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

COBBLER_BASE = "/var/www/cobbler"
XMLRPC_SERVER = "http://127.0.0.1/cobbler_api"
DEFAULT_PROFILE = "default"

#----------------------------------------------------------------------

class ServerProxy(xmlrpclib.ServerProxy):

    def __init__(self, url=None):
        xmlrpclib.ServerProxy.__init__(self, url, allow_none=True)

#----------------------------------------------------------------------

def parse_query():

    form = cgi.parse()
    
    mac = "-1"
    if os.environ.has_key("HTTP_X_RHN_PROVISIONING_MAC_0"):
        # FIXME: will not key off other NICs
        devicepair = os.environ["HTTP_X_RHN_PROVISIONING_MAC_0"]
        return devicepair.split()[1].strip()

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
    # get mac address, requires kssendmac on the kernel options line.
    else:
        return "-1"


#----------------------------------------------------------------------

def header():
    print "Content-type: text/plain"
    print

#----------------------------------------------------------------------

if __name__ == "__main__":
    cgitb.enable(format='text')
    header()
    server = ServerProxy(XMLRPC_SERVER)
    (mac, profile) = parse_query()
    try:
       ip = os.environ["REMOTE_ADDR"]
    except:
       ip = "???"
    print "# attempting to change system(mac=%s) to profile(%s)" % (mac,profile)
    server.change_profile(mac,profile)

