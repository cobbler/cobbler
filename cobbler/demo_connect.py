#!/usr/bin/python

"""
work in progress:  demo connection code for Cobbler read-write API 
uses SSL+XMLRPC (though just XMLRPC will still work)
adapted from Virt-Factory's old vf_nodecomm source
XMLRPCSSL portions based on http://linux.duke.edu/~icon/misc/xmlrpcssl.py

Copyright 2007, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>
Adrian Likins <alikins@redhat.com>
Scott Seago <sseago@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import sys
import socket

from M2Crypto import SSL
from M2Crypto.m2xmlrpclib import SSL_Transport, Server
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler


# workaround for bz #237902
class CobblerTransport(SSL_Transport):
    def __init__(self, ssl_context=None, use_datetime=0):
        self._use_datetime = use_datetime
        SSL_Transport.__init__(self,ssl_context=ssl_context)

def demo_connect(username,password,server):
    my_ctx = SSL.Context('sslv23')
    # my_ctx.load_client_ca("foo.pem")
    # my_ctx.load_cert("bar.pem","baz.pem")
    my_ctx.set_session_id_ctx("xmlrpcssl")
    my_ctx.set_allow_unknown_ca(True)
    my_ctx.set_verify(0,-1) # full anonymous (we hope)
    my_uri = "https://%s:443/cobbler_api_rw" % server
    print "connecting to: %s" % my_uri
    my_rserver = Server(my_uri, CobblerTransport(ssl_context = my_ctx))
    token = my_rserver.login(username,password)
    print "got a token: %s" % token
    rc = my_rserver.test(token)
    print "got test results: %s" % rc

if __name__ == "__main__":
    USERNAME = "mdehaan"
    PASSWORD = "llamas2007"
    SERVER   = "mdehaan.rdu.redhat.com"
    demo_connect(USERNAME,PASSWORD,SERVER)




