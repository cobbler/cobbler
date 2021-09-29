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
import logging.config
import os
import pwd
import time

from cobbler import remote, utils
from cobbler.api import CobblerAPI

if os.geteuid() == 0 and os.path.exists('/etc/cobbler/logging_config.conf'):
    logging.config.fileConfig('/etc/cobbler/logging_config.conf')


logger = logging.getLogger()


def core(cobbler_api: CobblerAPI):
    """
    Starts Cobbler.

    :param cobbler_api: The cobbler_api instance which is used for this method.
    """
    settings = cobbler_api.settings()
    xmlrpc_port = settings.xmlrpc_port

    regen_ss_file()
    do_xmlrpc_rw(cobbler_api, xmlrpc_port)


def regen_ss_file():
    """
    This is only used for Kerberos auth at the moment. It identifies XMLRPC requests from Apache that have already been
    cleared by Kerberos.
    """
    ssfile = "/var/lib/cobbler/web.ss"
    with open("/dev/urandom", 'rb') as fd:
        data = fd.read(512)

    with open(ssfile, 'wb', 0o660) as fd:
        fd.write(binascii.hexlify(data))

    http_user = "apache"
    family = utils.get_family()
    if family == "debian":
        http_user = "www-data"
    elif family == "suse":
        http_user = "wwwrun"
    os.lchown("/var/lib/cobbler/web.ss", pwd.getpwnam(http_user)[2], -1)


def do_xmlrpc_rw(cobbler_api: CobblerAPI, port):
    """
    This trys to bring up the Cobbler xmlrpc_api and restart it if it fails.

    :param cobbler_api: The cobbler_api instance which is used for this method.
    :param port: The port where the xmlrpc api should run on.
    """
    xinterface = remote.ProxiedXMLRPCInterface(cobbler_api, remote.CobblerXMLRPCInterface)
    server = remote.CobblerXMLRPCServer(('127.0.0.1', port))
    server.logRequests = 0      # don't print stuff
    logger.debug("XMLRPC running on %s", port)
    server.register_instance(xinterface)
    start_time = ""
    try:
        import psutil
        p = psutil.Process(os.getpid())
        start_time = " in %s seconds" % str(time.time() - p.create_time())
    except ModuleNotFoundError:
        # This is not critical, but debug only - just install python3-psutil
        pass

    while True:
        try:
            logger.info("Cobbler startup completed %s", start_time)
            server.serve_forever()
        except IOError:
            # interrupted? try to serve again
            time.sleep(0.5)


if __name__ == "__main__":
    core(CobblerAPI())
