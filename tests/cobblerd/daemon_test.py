"""
Testmodule to verify the functionality of the "cobbler.cobblerd.daemon" module.
"""

import socket
import threading
from socketserver import BaseRequestHandler, TCPServer
from typing import TYPE_CHECKING, Any, cast

from cobbler.cobblerd import daemon

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_regen_ss_file_chowns_when_http_user_exists(mocker: "MockerFixture") -> None:
    """
    ``regen_ss_file()`` must still chown the Kerberos-auth socket file to the detected http user when that
    user actually exists on the system (RPM/DEB/dev-stack deployments running Apache). This is the existing
    behavior and must not change.
    """
    mocker.patch("cobbler.cobblerd.daemon.utils.get_family", return_value="redhat")
    mock_getpwnam = mocker.patch("cobbler.cobblerd.daemon.pwd.getpwnam")
    mock_getpwnam.return_value = (
        "apache",
        "x",
        48,
        48,
        "Apache",
        "/srv/www",
        "/sbin/nologin",
    )
    mock_lchown = mocker.patch("cobbler.cobblerd.daemon.os.lchown")
    mocker.patch("builtins.open", mocker.mock_open())

    daemon.regen_ss_file()

    mock_getpwnam.assert_called_once_with("apache")
    mock_lchown.assert_called_once_with("/var/lib/cobbler/web.ss", 48, -1)


def test_regen_ss_file_tolerates_missing_http_user(mocker: "MockerFixture") -> None:
    """
    In the minimal, Apache-less container image none of "wwwrun"/"apache"/"www-data" exist.
    ``regen_ss_file()`` must not crash the daemon at startup with the ``KeyError`` that
    ``pwd.getpwnam()`` raises for an unknown user -- it must skip the chown (and log about it) instead.
    """
    mocker.patch("cobbler.cobblerd.daemon.utils.get_family", return_value="suse")
    mock_getpwnam = mocker.patch(
        "cobbler.cobblerd.daemon.pwd.getpwnam", side_effect=KeyError("wwwrun")
    )
    mock_lchown = mocker.patch("cobbler.cobblerd.daemon.os.lchown")
    mocker.patch("builtins.open", mocker.mock_open())

    # Must not raise.
    daemon.regen_ss_file()

    mock_getpwnam.assert_called_once_with("wwwrun")
    mock_lchown.assert_not_called()


def _mock_settings(mocker: "MockerFixture", **overrides: Any) -> Any:
    values = {
        "xmlrpc_bind_address_v4": "127.0.0.1",
        "xmlrpc_bind_address_v6": "::1",
    }
    values.update(overrides)
    settings = mocker.MagicMock()
    for key, value in values.items():
        setattr(settings, key, value)
    return settings


def test_build_xmlrpc_listeners_builds_ipv4_and_ipv6_by_default(
    mocker: "MockerFixture",
) -> None:
    """
    By default ``_build_xmlrpc_listeners()`` must build one IPv4 listener (today's exact
    behavior) plus one IPv6 listener, both registered with the same XML-RPC interface
    instance, so IPv6-resolving clients can reach cobblerd too.
    """
    mocker.patch.dict("os.environ", {}, clear=True)
    mock_interface = mocker.MagicMock()
    mocker.patch(
        "cobbler.cobblerd.daemon.remote.ProxiedXMLRPCInterface",
        return_value=mock_interface,
    )
    mock_server_cls = mocker.patch("cobbler.cobblerd.daemon.remote.CobblerXMLRPCServer")
    mock_server_cls.side_effect = [mocker.MagicMock(), mocker.MagicMock()]
    cobbler_api = mocker.MagicMock()
    cobbler_api.settings.return_value = _mock_settings(mocker)

    xinterface, listeners = daemon._build_xmlrpc_listeners(cobbler_api, 25151)  # type: ignore[reportPrivateUsage]

    assert xinterface is mock_interface
    assert len(listeners) == 2
    mock_server_cls.assert_any_call(("127.0.0.1", 25151))
    mock_server_cls.assert_any_call(("::1", 25151), use_ipv6=True)
    for listener in listeners:
        listener.register_instance.assert_called_once_with(mock_interface)  # type: ignore


def test_build_xmlrpc_listeners_skips_ipv6_when_disabled(
    mocker: "MockerFixture",
) -> None:
    """
    Setting ``xmlrpc_bind_address_v6`` to the empty-string sentinel must disable the
    IPv6 listener entirely, yielding only the IPv4 one.
    """
    mocker.patch.dict("os.environ", {}, clear=True)
    mocker.patch(
        "cobbler.cobblerd.daemon.remote.ProxiedXMLRPCInterface",
        return_value=mocker.MagicMock(),
    )
    mock_server_cls = mocker.patch("cobbler.cobblerd.daemon.remote.CobblerXMLRPCServer")
    mock_server_cls.return_value = mocker.MagicMock()
    cobbler_api = mocker.MagicMock()
    cobbler_api.settings.return_value = _mock_settings(
        mocker, xmlrpc_bind_address_v6=""
    )

    _, listeners = daemon._build_xmlrpc_listeners(cobbler_api, 25151)  # type: ignore[reportPrivateUsage]

    assert len(listeners) == 1
    mock_server_cls.assert_called_once_with(("127.0.0.1", 25151))


def test_build_xmlrpc_listeners_honors_ipv6_env_override(
    mocker: "MockerFixture",
) -> None:
    """
    ``COBBLER_XMLRPC_BIND_ADDRESS_V6`` must override the settings value, mirroring the
    existing ``COBBLER_XMLRPC_BIND_ADDRESS_V4`` behavior.
    """
    mocker.patch.dict(
        "os.environ", {"COBBLER_XMLRPC_BIND_ADDRESS_V6": "::2"}, clear=True
    )
    mocker.patch(
        "cobbler.cobblerd.daemon.remote.ProxiedXMLRPCInterface",
        return_value=mocker.MagicMock(),
    )
    mock_server_cls = mocker.patch("cobbler.cobblerd.daemon.remote.CobblerXMLRPCServer")
    mock_server_cls.side_effect = [mocker.MagicMock(), mocker.MagicMock()]
    cobbler_api = mocker.MagicMock()
    cobbler_api.settings.return_value = _mock_settings(mocker)

    daemon._build_xmlrpc_listeners(cobbler_api, 25151)  # type: ignore[reportPrivateUsage]

    mock_server_cls.assert_any_call(("::2", 25151), use_ipv6=True)


def test_build_xmlrpc_listeners_falls_back_to_ipv4_when_ipv6_bind_fails(
    mocker: "MockerFixture",
) -> None:
    """
    If constructing the IPv6 listener raises ``OSError`` (e.g. IPv6 disabled in the
    kernel/container), ``_build_xmlrpc_listeners()`` must log a warning and keep running
    with the IPv4 listener only, instead of crashing the daemon at startup.
    """
    mocker.patch.dict("os.environ", {}, clear=True)
    mocker.patch(
        "cobbler.cobblerd.daemon.remote.ProxiedXMLRPCInterface",
        return_value=mocker.MagicMock(),
    )
    mock_server_cls = mocker.patch("cobbler.cobblerd.daemon.remote.CobblerXMLRPCServer")
    mock_server_cls.side_effect = [mocker.MagicMock(), OSError("IPv6 disabled")]
    mock_warning = mocker.patch("cobbler.cobblerd.daemon.logger.warning")
    cobbler_api = mocker.MagicMock()
    cobbler_api.settings.return_value = _mock_settings(mocker)

    _, listeners = daemon._build_xmlrpc_listeners(cobbler_api, 25151)  # type: ignore[reportPrivateUsage]

    assert len(listeners) == 1
    mock_warning.assert_called_once()


def test_serve_xmlrpc_forever_dispatches_both_listeners_from_one_thread() -> None:
    """
    ``_serve_xmlrpc_forever()`` must multiplex multiple listener sockets on a single
    selector loop (no extra listener thread needed) and correctly dispatch to whichever
    socket has a pending connection.
    """
    handled: "list[tuple[str, Any]]" = []

    class LabeledTCPServer(TCPServer):
        allow_reuse_address = True
        family_label: str

        def __init__(self, address_family: int, label: str) -> None:
            self.address_family = address_family
            self.family_label = label
            super().__init__(
                ("127.0.0.1", 0) if address_family == socket.AF_INET else ("::1", 0),
                RecordingHandler,
            )

    class RecordingHandler(BaseRequestHandler):
        def handle(self) -> None:
            server = cast(LabeledTCPServer, self.server)
            handled.append((server.family_label, self.client_address))

    server_v4 = LabeledTCPServer(socket.AF_INET, "v4")
    server_v6 = LabeledTCPServer(socket.AF_INET6, "v6")

    serve_thread = threading.Thread(
        target=daemon._serve_xmlrpc_forever,  # type: ignore[reportPrivateUsage]
        args=([server_v4, server_v6],),
        daemon=True,
    )
    serve_thread.start()
    try:
        for family, server in (
            (socket.AF_INET, server_v4),
            (socket.AF_INET6, server_v6),
        ):
            client = socket.socket(family, socket.SOCK_STREAM)
            client.settimeout(2)
            client.connect(server.server_address[:2])
            client.close()

        import time

        for _ in range(50):
            if len(handled) == 2:
                break
            time.sleep(0.1)
    finally:
        server_v4.server_close()
        server_v6.server_close()

    assert sorted(label for label, _ in handled) == ["v4", "v6"]
