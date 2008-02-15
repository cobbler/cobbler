#============================================================================
# This library is free software; you can redistribute it and/or
# modify it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#============================================================================
# Copyright (C) 2006 Anthony Liguori <aliguori@us.ibm.com>
# Copyright (C) 2006 XenSource Inc.
# Copyright (C) 2007 Red Hat Inc., Michael DeHaan <mdehaan@redhat.com>
#============================================================================

"""
An enhanced XML-RPC client/server interface for Python.
"""

import re
import fcntl
from types import *
import os    
import errno
import traceback

from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import SocketServer
import xmlrpclib, socket, os, stat

#import mkdir

#
# Convert all integers to strings as described in the Xen API
#


def stringify(value):
    if isinstance(value, long) or \
       (isinstance(value, int) and not isinstance(value, bool)):
        return str(value)
    elif isinstance(value, dict):
        new_value = {}
        for k, v in value.items():
            new_value[stringify(k)] = stringify(v)
        return new_value
    elif isinstance(value, (tuple, list)):
        return [stringify(v) for v in value]
    else:
        return value


# We're forced to subclass the RequestHandler class so that we can work around
# some bugs in Keep-Alive handling and also enabled it by default
class XMLRPCRequestHandler(SimpleXMLRPCRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, request, client_address, server):
        SimpleXMLRPCRequestHandler.__init__(self, request, client_address,
                                            server)

    # this is inspired by SimpleXMLRPCRequestHandler's do_POST but differs
    # in a few non-trivial ways
    # 1) we never generate internal server errors.  We let the exception
    #    propagate so that it shows up in the Xend debug logs
    # 2) we don't bother checking for a _dispatch function since we don't
    #    use one
    def do_POST(self):
        addrport = self.client_address
        #if not connection.hostAllowed(addrport, self.hosts_allowed):
        #    self.connection.shutdown(1)
        #    return

        data = self.rfile.read(int(self.headers["content-length"]))
        rsp = self.server._marshaled_dispatch(data)

        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.send_header("Content-Length", str(len(rsp)))
        self.end_headers()

        self.wfile.write(rsp)
        self.wfile.flush()
        #if self.close_connection == 1:
        #    self.connection.shutdown(1)

def parents(dir, perms, enforcePermissions = False):
    """
    Ensure that the given directory exists, creating it if necessary, but not
    complaining if it's already there.

    @param dir The directory name.
    @param perms One of the stat.S_ constants.
    @param enforcePermissions Enforce our ownership and the given permissions,
    even if the directory pre-existed with different ones.
    """
    # Catch the exception here, rather than checking for the directory's
    # existence first, to avoid races.
    try:
        os.makedirs(dir, perms)
    except OSError, exn:
        if exn.args[0] != errno.EEXIST or not os.path.isdir(dir):
            raise
    if enforcePermissions:
        os.chown(dir, os.geteuid(), os.getegid())
        os.chmod(dir, stat.S_IRWXU)


# This is a base XML-RPC server for TCP.  It sets allow_reuse_address to
# true, and has an improved marshaller that logs and serializes exceptions.

class TCPXMLRPCServer(SocketServer.ThreadingMixIn, SimpleXMLRPCServer):
    allow_reuse_address = True

    def __init__(self, addr, requestHandler=None,
                 logRequests = 1):
        if requestHandler is None:
            requestHandler = XMLRPCRequestHandler
        SimpleXMLRPCServer.__init__(self, addr,
                                    (lambda x, y, z:
                                     requestHandler(x, y, z)),
                                    logRequests)

        flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
        flags |= fcntl.FD_CLOEXEC
        fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)

    def get_request(self):
        (client, addr) = SimpleXMLRPCServer.get_request(self)
        flags = fcntl.fcntl(client.fileno(), fcntl.F_GETFD)
        flags |= fcntl.FD_CLOEXEC
        fcntl.fcntl(client.fileno(), fcntl.F_SETFD, flags)
        return (client, addr)

    def _marshaled_dispatch(self, data, dispatch_method = None):
        params, method = xmlrpclib.loads(data)
        if False:
            # Enable this block of code to exit immediately without sending
            # a response.  This allows you to test client-side crash handling.
            import sys
            sys.exit(1)
        try:
            if dispatch_method is not None:
                response = dispatch_method(method, params)
            else:
                response = self._dispatch(method, params)

            if (response is None or
                not isinstance(response, dict) or
                'Status' not in response):
                #log.exception('Internal error handling %s: Invalid result %s',
                #              method, response)
                response = { "Status": "Failure",
                             "ErrorDescription":
                             ['INTERNAL_ERROR',
                              'Invalid result %s handling %s' %
                              (response, method)]}

            # With either Unicode or normal strings, we can only transmit
            # \t, \n, \r, \u0020-\ud7ff, \ue000-\ufffd, and \u10000-\u10ffff
            # in an XML document.  xmlrpclib does not escape these values
            # properly, and then breaks when it comes to parse the document.
            # To hack around this problem, we use repr here and exec above
            # to transmit the string using Python encoding.
            # Thanks to David Mertz <mertz@gnosis.cx> for the trick (buried
            # in xml_pickle.py).
            if isinstance(response, StringTypes):
                response = repr(response)[1:-1]

            response = (response,)
            response = xmlrpclib.dumps(response,
                                       methodresponse=1,
                                       allow_none=1)
        except Exception, exn:
            try:
                #if self.xenapi:
                #    if _is_not_supported(exn):
                #         errdesc = ['MESSAGE_METHOD_UNKNOWN', method]
                #    else:
                #         #log.exception('Internal error handling %s', method)
                #         errdesc = ['INTERNAL_ERROR', str(exn)]
                #
                #    response = xmlrpclib.dumps(
                #          ({ "Status": "Failure",
                #             "ErrorDescription": errdesc },),
                #          methodresponse = 1)
                #else:
                #    import xen.xend.XendClient
                if isinstance(exn, xmlrpclib.Fault):
                    response = xmlrpclib.dumps(exn)
                else:
                    # log.exception('Internal error handling %s', method)
                    response = xmlrpclib.dumps(
                            xmlrpclib.Fault(101, str(exn)))
            except Exception, exn2:
                # FIXME
                traceback.print_exc()

        return response


notSupportedRE = re.compile(r'method "(.*)" is not supported')
def _is_not_supported(exn):
    try:
        m = notSupportedRE.search(exn[0])
        return m is not None
    except:
        return False


# This is a XML-RPC server that sits on a Unix domain socket.
# It implements proper support for allow_reuse_address by
# unlink()'ing an existing socket.

class UnixXMLRPCRequestHandler(XMLRPCRequestHandler):
    def address_string(self):
        try:
            return XMLRPCRequestHandler.address_string(self)
        except ValueError, e:
            return self.client_address[:2]

class UnixXMLRPCServer(TCPXMLRPCServer):
    address_family = socket.AF_UNIX
    allow_address_reuse = True

    def __init__(self, addr, logRequests = 1):
        parents(os.path.dirname(addr), stat.S_IRWXU, True)
        if self.allow_reuse_address and os.path.exists(addr):
            os.unlink(addr)

        TCPXMLRPCServer.__init__(self, addr, 
                                 UnixXMLRPCRequestHandler, logRequests)
