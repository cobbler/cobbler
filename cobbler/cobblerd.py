"""
Cobbler daemon for logging remote syslog traffic during automatic installation

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

from cobbler import api as cobbler_api
from cobbler import remote
from cobbler import utils


def core(api):
    """
    Starts Cobbler.

    :param api: The cobbler_api instance which is used for this method.
    """
    cobbler_api = api
    settings = cobbler_api.settings()
    xmlrpc_port = settings.xmlrpc_port

    regen_ss_file()
    do_xmlrpc_tasks(cobbler_api, settings, xmlrpc_port)


def regen_ss_file():
    """
    This is only used for Kerberos auth at the moment. It identifies XMLRPC requests from Apache that have already been
    cleared by Kerberos.

    :return: 1 if this was successful.
    """
    ssfile = "/var/lib/cobbler/web.ss"
    fd = open("/dev/urandom", 'rb')
    data = fd.read(512)
    fd.close()

    fd = os.open(ssfile, os.O_CREAT | os.O_RDWR, 0o600)
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
    """
    This trys to bring up the Cobbler xmlrpc_api and restart it if it fails. Tailcall to ``do_xmlrpc_rw``.

    :param cobbler_api: The cobbler_api instance which is used for this method.
    :param settings: The Cobbler settings instance which is used for this method.
    :param xmlrpc_port: The port where xmlrpc should run on.
    """
    do_xmlrpc_rw(cobbler_api, settings, xmlrpc_port)


def log(logger, msg):
    """
    This logs something with the Cobbler Logger.

    :param logger: If this is not none then an info message is printed to the log target. In any other case stderr is
                   used.
    :param msg: The message to be logged.
    :type msg: str
    """
    if logger is not None:
        logger.info(msg)
    else:
        print(msg, file=sys.stderr)


def do_xmlrpc_rw(cobbler_api, settings, port):
    """
    This trys to bring up the Cobbler xmlrpc_api and restart it if it fails.

    :param cobbler_api: The cobbler_api instance which is used for this method.
    :param settings: The Cobbler settings instance which is used for this method.
    :param port: The port where the xmlrpc api should run on.
    """
    xinterface = remote.ProxiedXMLRPCInterface(cobbler_api, remote.CobblerXMLRPCInterface)
    server = remote.CobblerXMLRPCServer(('127.0.0.1', port))
    server.logRequests = 0      # don't print stuff
    xinterface.logger.debug("XMLRPC running on %s" % port)
    server.register_instance(xinterface)

    while True:
        try:
            print("SERVING!")
            server.serve_forever()
        except IOError:
            # interrupted? try to serve again
            time.sleep(0.5)


if __name__ == "__main__":
    cobbler_api = cobbler_api.CobblerAPI()
    settings = cobbler_api.settings()
    regen_ss_file()
    do_xmlrpc_rw(cobbler_api, settings, 25151)
