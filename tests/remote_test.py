"""
Testmodule to verify the functionality of the "cobbler.remote" module.
"""

import socket

from cobbler.remote import CobblerXMLRPCServer


def test_cobbler_xmlrpc_server_defaults_to_ipv4() -> None:
    """
    ``CobblerXMLRPCServer`` must keep binding an IPv4 (``AF_INET``) socket by default, so existing
    deployments relying on ``xmlrpc_bind_address`` being an IPv4 address/hostname are unaffected.
    """
    server = CobblerXMLRPCServer(("127.0.0.1", 0))
    try:
        assert server.socket.family == socket.AF_INET
    finally:
        server.server_close()


def test_cobbler_xmlrpc_server_can_bind_ipv6() -> None:
    """
    ``CobblerXMLRPCServer`` must be able to bind an IPv6 (``AF_INET6``) socket when ``use_ipv6=True``
    is passed, and that socket must actually accept IPv6 client connections.
    """
    server = CobblerXMLRPCServer(("::1", 0), use_ipv6=True)
    try:
        assert server.socket.family == socket.AF_INET6

        port = server.server_address[1]
        client = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        try:
            client.settimeout(2)
            client.connect(("::1", port))
        finally:
            client.close()
    finally:
        server.server_close()
