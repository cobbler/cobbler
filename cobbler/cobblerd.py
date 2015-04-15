"""
cobbler daemon for logging remote syslog traffic during automatic installation

Copyright 2007-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import binascii
import os
import pwd
import sys
import time

import api as cobbler_api
import remote
import utils


def core(api):
    cobbler_api = api
    settings = cobbler_api.settings()
    xmlrpc_port = settings.xmlrpc_port

    regen_ss_file()
    do_xmlrpc_tasks(cobbler_api, settings, xmlrpc_port)


def regen_ss_file():
    # this is only used for Kerberos auth at the moment.
    # it identifies XMLRPC requests from Apache that have already
    # been cleared by Kerberos.
    ssfile = "/var/lib/cobbler/web.ss"
    fd = open("/dev/urandom")
    data = fd.read(512)
    fd.close()

    fd = os.open(ssfile, os.O_CREAT | os.O_RDWR, 0600)
    os.write(fd, binascii.hexlify(data))
    os.close(fd)

    http_user = "apache"
    family = utils.get_family()
    if family == "debian":
        http_user = "www-data"
    elif family == "suse":
        http_user = "wwwrun"
    os.lchown("/var/lib/cobbler/web.ss", pwd.getpwnam(http_user)[2], -1)

    return 1


def do_xmlrpc_tasks(cobbler_api, settings, xmlrpc_port):
    do_xmlrpc_rw(cobbler_api, settings, xmlrpc_port)


def log(logger, msg):
    if logger is not None:
        logger.info(msg)
    else:
        print >>sys.stderr, msg


def do_xmlrpc_rw(cobbler_api, settings, port):

    xinterface = remote.ProxiedXMLRPCInterface(cobbler_api, remote.CobblerXMLRPCInterface)
    server = remote.CobblerXMLRPCServer(('127.0.0.1', port))
    server.logRequests = 0      # don't print stuff
    xinterface.logger.debug("XMLRPC running on %s" % port)
    server.register_instance(xinterface)

    while True:
        try:
            print "SERVING!"
            server.serve_forever()
        except IOError:
            # interrupted? try to serve again
            time.sleep(0.5)


if __name__ == "__main__":
    cobbler_api = cobbler_api.CobblerAPI()
    settings = cobbler_api.settings()
    regen_ss_file()
    do_xmlrpc_rw(cobbler_api, settings, 25151)
