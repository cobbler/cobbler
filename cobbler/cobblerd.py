"""
Cobbler daemon for logging remote syslog traffic during automatic installation
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import binascii
import logging
import logging.config
import os
import pwd
import time

from cobbler import remote, utils
from cobbler.api import CobblerAPI

if os.geteuid() == 0 and os.path.exists("/etc/cobbler/logging_config.conf"):
    logging.config.fileConfig("/etc/cobbler/logging_config.conf")


logger = logging.getLogger()


def core(cobbler_api: CobblerAPI) -> None:
    """
    Starts Cobbler.

    :param cobbler_api: The cobbler_api instance which is used for this method.
    """
    settings = cobbler_api.settings()
    xmlrpc_port = settings.xmlrpc_port

    regen_ss_file()
    do_xmlrpc_rw(cobbler_api, xmlrpc_port)


def regen_ss_file() -> None:
    """
    This is only used for Kerberos auth at the moment. It identifies XMLRPC requests from Apache that have already been
    cleared by Kerberos.
    """
    ssfile = "/var/lib/cobbler/web.ss"
    data = os.urandom(512)

    with open(ssfile, "wb", 0o660) as ss_file_fd:
        ss_file_fd.write(binascii.hexlify(data))

    http_user = "apache"
    family = utils.get_family()
    if family == "debian":
        http_user = "www-data"
    elif family == "suse":
        http_user = "wwwrun"
    os.lchown(ssfile, pwd.getpwnam(http_user)[2], -1)


def do_xmlrpc_rw(cobbler_api: CobblerAPI, port: int) -> None:
    """
    This trys to bring up the Cobbler xmlrpc_api and restart it if it fails.

    :param cobbler_api: The cobbler_api instance which is used for this method.
    :param port: The port where the xmlrpc api should run on.
    """
    xinterface = remote.ProxiedXMLRPCInterface(
        cobbler_api, remote.CobblerXMLRPCInterface
    )
    server = remote.CobblerXMLRPCServer(("127.0.0.1", port))
    # don't log requests; ignore mypy due to multiple inheritance & protocols being 3.8+
    server.logRequests = False  # type: ignore[attr-defined]
    logger.debug("XMLRPC running on %s", port)
    server.register_instance(xinterface)
    start_time = ""
    try:
        import psutil

        ps_util = psutil.Process(os.getpid())
        start_time = f" in {str(time.time() - ps_util.create_time())} seconds"
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
