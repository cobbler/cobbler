#!/usr/bin/env python

# This software may be freely redistributed under the terms of the GNU
# general public license.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# based on:
# Cobbler ks-serving script
# July 5 2007
# Adam Wolf <adamwolf@feelslikeburning.com>
# http://feelslikeburning.com/projects/live-cd-restoring-with-cobbler/

import cgi
import cgitb
import time
import os
import sys
import socket
import xmlrpclib

COBBLER_BASE = "/var/www/cobbler"
XMLRPC_SERVER = "http://127.0.0.1:25151"

#----------------------------------------------------------------------

class ServerProxy(xmlrpclib.ServerProxy):

    def __init__(self, url=None):
        xmlrpclib.ServerProxy.__init__(self, url, allow_none=True)

#----------------------------------------------------------------------

def parse_query():

    form = cgi.parse()

    if form.has_key("system"):
        name = form["system"][0]
        type = "system"
    elif form.has_key("profile"):
        name = form["profile"][0]
        type = "profile"
    else:
        type = "system"
        name = autodetect_ip()
    return (name,type)

#----------------------------------------------------------------------

def autodetect_ip():

    ip = os.environ["REMOTE_ADDR"]
    xmlrpc_server = ServerProxy(XMLRPC_SERVER)
    systems = xmlrpc_server.get_systems()
    candidates = [system['name'] for system in systems if system['ip_address'] == ip]

    if len(candidates) == 0:
	print "# No system entries with ip %s found" % ip
	sys.exit(1)
    elif len(candidates) > 1:
	print "# Multiple system entries with ip %s found" % ip
	sys.exit(1)
    elif len(candidates) == 1:
	return candidates[0]

#----------------------------------------------------------------------

def serve_file(name):

    # never hurts to be safe...
    name = name.replace("/","")
    name = name.replace("..","")
    name = name.replace(";","")

    if type == "system":
        ks_path = "%s/kickstarts_sys/%s/ks.cfg" % (COBBLER_BASE, name)
    elif type == "profile":
        ks_path = "%s/kickstarts/%s/ks.cfg" % (COBBLER_BASE, name)

    if not os.path.exists(ks_path):
        print "# No such cobbler object"
        sys.exit(1)

    try:
        ksfile = open(ks_path)
    except:
        print "# Cannot open file %s" % ks_path
        sys.exit(1)

    for line in ksfile:
        print line.strip()
    ksfile.close()

#----------------------------------------------------------------------

def header():
    print "Content-type: text/plain"
    print

#----------------------------------------------------------------------

if __name__ == "__main__":
    cgitb.enable(format='text')
    header()
    (name, type) = parse_query()
    print "# kickstart for cobbler %s %s" % (type,name)
    print "# served on %s" % time.ctime() 
    print "# requestor ip = %s" % os.environ["REMOTE_ADDR"]
    print "# ============================="
    print " "
    serve_file(name)


