"""
Cobbler daemon for logging remote syslog traffic during automatic installation
"""

import binascii
import logging
import os
import pwd
import selectors
import sys
import time
from typing import List, Tuple

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

    fd = os.open(ssfile, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o660)
    with os.fdopen(fd, "w", encoding="UTF-8") as ss_file_fd:
        ss_file_fd.write(str(binascii.hexlify(data)))

    http_user = "apache"
    family = utils.get_family()
    if family == "debian":
        http_user = "www-data"
    elif family == "suse":
        http_user = "wwwrun"
    try:
        http_user_gid = pwd.getpwnam(http_user)[2]
    except KeyError:
        # Kerberos-auth-over-Apache is not applicable when no Apache/web-server user exists on the system
        # at all (e.g. the minimal, Apache-less container image) -- skip the chown rather than crashing the
        # daemon at startup. Deployments where "http_user" legitimately exists (RPM/DEB/dev-stack, still
        # running Apache) are unaffected and keep chown'ing exactly as before.
        logger.debug(
            'Not chowning "%s" to "%s": no such user found on this system.',
            ssfile,
            http_user,
        )
        return
    os.lchown(ssfile, http_user_gid, -1)


def _build_xmlrpc_listeners(
    cobbler_api: CobblerAPI, port: int
) -> Tuple["remote.ProxiedXMLRPCInterface", List["remote.CobblerXMLRPCServer"]]:
    """
    Build one ``CobblerXMLRPCServer`` per configured bind address: always an IPv4 (or
    hostname) listener, plus an IPv6 listener unless ``xmlrpc_bind_address_v6`` is
    empty. Both listeners register the same ``ProxiedXMLRPCInterface`` instance so they
    expose an identical API surface.

    :param cobbler_api: The cobbler_api instance which is used for this method.
    :param port: The port both listeners bind to.
    :return: The shared XML-RPC interface, plus the list of listeners. ``listeners[0]``
             is always the primary (IPv4) one.
    """
    xinterface = remote.ProxiedXMLRPCInterface(
        cobbler_api, remote.CobblerXMLRPCInterface
    )
    settings = cobbler_api.settings()
    bind_address_v4 = os.environ.get(
        "COBBLER_XMLRPC_BIND_ADDRESS_V4", settings.xmlrpc_bind_address_v4
    )
    bind_address_v6 = os.environ.get(
        "COBBLER_XMLRPC_BIND_ADDRESS_V6", settings.xmlrpc_bind_address_v6
    )

    listeners = [remote.CobblerXMLRPCServer((bind_address_v4, port))]
    if bind_address_v6:
        try:
            listeners.append(
                remote.CobblerXMLRPCServer((bind_address_v6, port), use_ipv6=True)
            )
        except OSError as error:
            logger.warning(
                "Could not start the IPv6 XML-RPC listener on [%s]:%s (%s); "
                "continuing with IPv4 only.",
                bind_address_v6,
                port,
                error,
            )

    for server in listeners:
        # don't log requests; ignore mypy due to multiple inheritance & protocols being 3.8+
        server.logRequests = False  # type: ignore[attr-defined]
        server.register_instance(xinterface)

    return xinterface, listeners


def _serve_xmlrpc_forever(servers: List["remote.CobblerXMLRPCServer"]) -> None:
    """
    Serve one or more already-bound-and-activated XML-RPC listener sockets from a single
    thread, by multiplexing them with a selector and dispatching whichever socket has a
    pending connection to its own server instance. ``ThreadingMixIn`` still hands each
    accepted connection off to its own thread, exactly as with a single listener.

    :param servers: The listener servers to multiplex.
    """
    with selectors.DefaultSelector() as selector:
        for server in servers:
            selector.register(server, selectors.EVENT_READ, server)
        while True:
            for key, _ in selector.select(timeout=0.5):
                key.data._handle_request_noblock()


def do_xmlrpc_rw(cobbler_api: CobblerAPI, port: int) -> None:
    """
    This tries to bring up the Cobbler xmlrpc_api and restart it if it fails.

    This method serves requests in an endless loop (restarting the server whenever ``serve_forever()`` raises an
    ``IOError``) and only returns if interrupted by a different exception.

    :param cobbler_api: The cobbler_api instance which is used for this method.
    :param port: The port where the xmlrpc api should run on.
    """
    xinterface, listeners = _build_xmlrpc_listeners(cobbler_api, port)
    logger.debug("XMLRPC running on %s", port)
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
            _serve_xmlrpc_forever(listeners)
        except IOError:
            # interrupted? try to serve again
            time.sleep(0.5)


def daemonize_self() -> None:
    """
    Daemonizes the current process.
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
