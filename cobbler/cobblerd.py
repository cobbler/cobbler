"""
Cobbler daemon for logging remote syslog traffic during automatic installation
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import argparse
import binascii
import logging
import logging.config
import os
import pwd
import sys
import time
import traceback

import systemd.daemon  # type: ignore

try:
    import psutil  # type: ignore
except ModuleNotFoundError:
    # pylint: disable-next=invalid-name
    psutil = None  # type: ignore

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

    with open(ssfile, "w", 0o660, encoding="UTF-8") as ss_file_fd:
        ss_file_fd.write(str(binascii.hexlify(data)))

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
    if psutil is not None:
        ps_util = psutil.Process(os.getpid())
        start_time = f" in {str(time.time() - ps_util.create_time())} seconds"

    systemd.daemon.notify("READY=1")  # type: ignore
    while True:
        try:
            logger.info("Cobbler startup completed %s", start_time)
            # Start background load_items task
            xinterface.proxied.background_load_items()
            server.serve_forever()
        except IOError:
            # interrupted? try to serve again
            time.sleep(0.5)


def daemonize_self():
    """
    Demonizes the current process.
    """
    # daemonizing code:  http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66012
    logger.info("cobblerd started")
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError as e:
        print(f"fork #1 failed: {e.errno} ({e.strerror})", file=sys.stderr)
        sys.exit(1)

    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0o22)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # print "Daemon PID %d" % pid
            sys.exit(0)
    except OSError as e:
        print(f"fork #2 failed: {e.errno} ({e.strerror})", file=sys.stderr)
        sys.exit(1)

    with open("/dev/null", "r+", encoding="UTF-8") as dev_null:
        os.dup2(dev_null.fileno(), sys.stdin.fileno())
        os.dup2(dev_null.fileno(), sys.stdout.fileno())
        os.dup2(dev_null.fileno(), sys.stderr.fileno())


def main() -> int:
    """
    Main entrypoint for the cobbler daemon.
    """
    op = argparse.ArgumentParser()
    op.set_defaults(daemonize=True, log_level=None)
    op.add_argument(
        "-B",
        "--daemonize",
        dest="daemonize",
        action="store_true",
        help="run in background (default)",
    )
    op.add_argument(
        "-F",
        "--no-daemonize",
        dest="daemonize",
        action="store_false",
        help="run in foreground (do not daemonize)",
    )
    op.add_argument(
        "-f", "--log-file", dest="log_file", metavar="NAME", help="file to log to"
    )
    op.add_argument(
        "-l",
        "--log-level",
        dest="log_level",
        metavar="LEVEL",
        help="log level (ie. INFO, WARNING, ERROR, CRITICAL)",
    )
    op.add_argument(
        "--config",
        "-c",
        help="The location of the Cobbler configuration file.",
        default="/etc/cobbler/settings.yaml",
    )
    op.add_argument(
        "--enable-automigration",
        help='If given, overrule setting from "settings.yaml" and execute automigration.',
        dest="automigration",
        action="store_true",
    )
    op.add_argument(
        "--disable-automigration",
        help='If given, overrule setting from "settings.yaml" and do not execute automigration.',
        dest="automigration",
        action="store_false",
    )
    op.set_defaults(automigration=None)

    options = op.parse_args()

    # load the API now rather than later, to ensure cobblerd startup time is done before the service returns
    # Disable broad exception caught as this is desired on a top-level entrypoint
    # pylint: disable=broad-exception-caught
    api = None
    try:
        api = CobblerAPI(
            is_cobblerd=True,
            settingsfile_location=options.config,
            execute_settings_automigration=options.automigration,
        )
    except Exception as exc:
        if sys.exc_info()[0] == SystemExit:
            # pylint: disable-next=no-member
            return exc.code  # type: ignore
        else:
            # FIXME: log this too
            traceback.print_exc()
            return 1

    if options.daemonize:
        daemonize_self()

    try:
        core(api)
    except Exception as e:
        logger.error(e)
        traceback.print_exc()

    return 0


if __name__ == "__main__":
    sys.exit(main())
