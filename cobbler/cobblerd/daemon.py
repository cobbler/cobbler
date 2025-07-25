"""
Cobbler daemon for logging remote syslog traffic during automatic installation
"""

import binascii
import logging
import os
import pwd
import sys
import time

import systemd.daemon  # type: ignore

from cobbler import remote, utils
from cobbler.api import CobblerAPI

try:
    import psutil  # type: ignore
except ModuleNotFoundError:
    # pylint: disable-next=invalid-name
    psutil = None  # type: ignore

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


def daemonize_self() -> None:
    """
    Deamonizes the current process.
    """
    # daemonizing code:  http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66012
    logger.info("cobblerd started")
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError as e:
        logger.error("fork #1 failed: %s (%s)", e.errno, e.strerror)
        sys.exit(1)

    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0o22)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            logger.info("Daemon PID %d", pid)
            sys.exit(0)
    except OSError as e:
        logger.error("fork #2 failed: %s (%s)", e.errno, e.strerror)
        sys.exit(1)

    with open("/dev/null", "r+", encoding="UTF-8") as dev_null:
        os.dup2(dev_null.fileno(), sys.stdin.fileno())
        os.dup2(dev_null.fileno(), sys.stdout.fileno())
        os.dup2(dev_null.fileno(), sys.stderr.fileno())
