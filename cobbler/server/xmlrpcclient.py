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
# Copyright (C) 2007 XenSource Inc.
# Copyright (C) 2007 Red Hat Inc, Michael DeHaan <mdehaan@redhat.com>

from httplib import FakeSocket, HTTPConnection, HTTP
import socket
import string
import xmlrpclib
from types import StringTypes

class HTTPUnixConnection(HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.host)

class HTTPUnix(HTTP):
    _connection_class = HTTPUnixConnection

class UnixTransport(xmlrpclib.Transport):
    def request(self, host, handler, request_body, verbose=0):
        self.__handler = handler
        return xmlrpclib.Transport.request(self, host, '/RPC2',
                                           request_body, verbose)
    def make_connection(self, host):
        return HTTPUnix(self.__handler)

# See xmlrpclib2.TCPXMLRPCServer._marshalled_dispatch.
def conv_string(x):
    if isinstance(x, StringTypes):
        s = string.replace(x, "'", r"\047")
        exec "s = '" + s + "'"
        return s
    else:
        return x


class ServerProxy(xmlrpclib.ServerProxy):
    def __init__(self, uri, transport=None, encoding=None, verbose=0,
                 allow_none=1):
        if transport == None:
            (protocol, rest) = uri.split(':', 1)
            if protocol == 'httpu':
                uri = 'http:' + rest
                transport = UnixTransport()
            else:
                raise ValueError("only httpu://path/to/socket is supported")
        xmlrpclib.ServerProxy.__init__(self, uri, transport, encoding,
                                       verbose, allow_none)


    def __request(self, methodname, params):
        response = xmlrpclib.ServerProxy.__request(self, methodname, params)

        if isinstance(response, tuple):
            return tuple([conv_string(x) for x in response])
        else:
            return conv_string(response)

