# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Cobbler contributors
"""
Kerberos/GSSAPI single-sign-on WSGI endpoint (``/sso_login``).

Unlike the release33 bridge, ``main``'s containerized deployment topology runs the HTTP-facing
services as a Gunicorn WSGI app with no Apache/nginx in front of it, so there is nothing to
terminate the SPNEGO/Kerberos negotiation on this branch's behalf. This module does that
negotiation itself, natively in Python, using the ``gssapi`` library:

1. A client makes a request to ``/sso_login`` with no ``Authorization`` header (or a malformed
   one). This module replies ``401 Unauthorized`` with a ``WWW-Authenticate: Negotiate`` header --
   the standard SPNEGO challenge, not an error condition. A Kerberos-aware HTTP client
   (``requests-gssapi``, a browser with SPNEGO configured, etc.) reacts to that challenge by
   retrying with an ``Authorization: Negotiate <base64 token>`` header carrying a real ticket.
2. This module base64-decodes that token and feeds it to ``gssapi`` to complete the server side of
   the negotiation, using a keytab configured via the ``KRB5_KTNAME`` environment variable (read
   from the server process's own environment via :data:`os.environ` -- this is a Kerberos/krb5
   convention, unrelated to the WSGI ``environ`` dict passed into :func:`application`).
3. Once negotiation completes, the client's Kerberos principal (``alice@EXAMPLE.COM``) is
   normalized to a plain username (``alice``) the same way the release33 bridge does -- by
   stripping everything from the first ``"@"`` onward -- and exchanged for a Cobbler session token
   via a normal XML-RPC ``login()`` call against cobblerd, using the shared secret cobblerd itself
   writes to ``/var/lib/cobbler/web.ss`` (see :func:`cobbler.utils.get_shared_secret`) in place of
   a password. This relies on ``cobbler.modules.authentication.passthru`` accepting that shared
   secret as a valid "password" for any username, exactly as it already does for the CLI and the
   legacy web UI.

``gssapi`` is only ever imported lazily, inside :func:`application`, never at module import time:
the package isn't necessarily installed (or a keytab configured) in every Cobbler deployment, and
this module must degrade to a clean ``501 Not Implemented`` rather than making Cobbler
unimportable/unstartable when it's absent.
"""

import base64
import json
import logging
import os
import xmlrpc.client
from typing import Any, Callable, Dict, List, Optional

from cobbler import utils
from cobbler.services import files

logger = logging.getLogger(__name__)

_WsgiStartResponse = Callable[[str, List[Any]], None]


def _json_response(
    start_response: _WsgiStartResponse,
    status: str,
    body: Dict[str, Any],
    extra_headers: Optional[List[Any]] = None,
) -> List[bytes]:
    """
    Build a small ``application/json`` response, the shape every response of this module uses.

    :param start_response: The WSGI ``start_response`` callable.
    :param status: The HTTP status line, e.g. ``"200 OK"``.
    :param body: The JSON-serializable response body.
    :param extra_headers: Additional response headers (e.g. ``WWW-Authenticate``), if any.
    """
    content = json.dumps(body).encode("utf-8")
    headers: List[Any] = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(content))),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    start_response(status, headers)
    return [content]


def _not_configured(start_response: _WsgiStartResponse) -> List[bytes]:
    """``501 Not Implemented``: ``gssapi`` isn't installed, or no keytab is configured."""
    return _json_response(
        start_response, "501 Not Implemented", {"error": "sso_not_configured"}
    )


def _negotiate_challenge(start_response: _WsgiStartResponse) -> List[bytes]:
    """
    ``401 Unauthorized`` with a ``WWW-Authenticate: Negotiate`` challenge -- the expected first
    leg of SPNEGO negotiation for a client with no established security context yet, not an error.
    """
    return _json_response(
        start_response,
        "401 Unauthorized",
        {"error": "no_authenticated_user"},
        extra_headers=[("WWW-Authenticate", "Negotiate")],
    )


def _rejected(start_response: _WsgiStartResponse, error: str) -> List[bytes]:
    """``403 Forbidden`` with the given machine-readable ``error`` key."""
    return _json_response(start_response, "403 Forbidden", {"error": error})


def application(
    environ: Dict[str, Any], start_response: _WsgiStartResponse
) -> List[bytes]:
    """
    WSGI entrypoint for ``/sso_login``: negotiate Kerberos/SPNEGO with the client and, on success,
    exchange the resulting principal for a normal Cobbler XML-RPC session token.

    :param environ: The WSGI environ.
    :param start_response: The WSGI ``start_response`` callable.
    """
    try:
        import gssapi  # pylint: disable=import-outside-toplevel  # type: ignore[import-not-found]
    except ImportError:
        return _not_configured(start_response)

    if not os.environ.get("KRB5_KTNAME"):
        return _not_configured(start_response)

    auth_header = environ.get("HTTP_AUTHORIZATION")
    if not auth_header or not auth_header.startswith("Negotiate "):
        return _negotiate_challenge(start_response)

    token_b64 = auth_header[len("Negotiate ") :]

    output_token: Optional[bytes] = None
    try:
        decoded_token = base64.b64decode(token_b64)
        server_creds = gssapi.Credentials(usage="accept")  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]
        context = gssapi.SecurityContext(creds=server_creds, usage="accept")  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]
        output_token = context.step(decoded_token)  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]
    except Exception:  # pylint: disable=broad-except
        # gssapi's own exception hierarchy (gssapi.exceptions.GSSError and friends) is not
        # exhaustively documented/stable enough to enumerate here, and a malformed base64 token
        # raises a plain binascii.Error/ValueError before gssapi is ever reached. Either way, this
        # must never propagate as an unhandled 500, and must never be mistaken for success.
        logger.warning("SSO negotiation failed", exc_info=True)
        return _rejected(start_response, "login_rejected")

    try:
        # Both of these are gssapi properties backed by C library calls (e.g.
        # initiator_name performs a gss_inquire_context under the hood) and can themselves
        # raise gssapi.exceptions.GSSError -- must not propagate as an unhandled 500 either.
        is_complete = context.complete  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]
        principal = str(context.initiator_name)  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]
    except Exception:  # pylint: disable=broad-except
        logger.warning("SSO negotiation post-check failed", exc_info=True)
        return _rejected(start_response, "login_rejected")

    if is_complete is not True:
        logger.warning("SSO negotiation incomplete for a client token")
        return _rejected(start_response, "negotiation_incomplete")

    username = principal.partition("@")[0]
    if not username:
        return _rejected(start_response, "empty_username")

    shared_secret = utils.get_shared_secret()
    try:
        # pylint: disable-next=protected-access
        remote = files._build_remote()  # type: ignore[reportPrivateUsage]
        token = remote.login(username, shared_secret)
    except (xmlrpc.client.Fault, xmlrpc.client.ProtocolError, OSError):
        # Mirrors cobbler.services.files.healthz_application's exception set: covers cobblerd
        # being unreachable/timing out (OSError), a malformed XML-RPC response
        # (ProtocolError), and settings.yaml itself being missing/unreadable (_build_remote()
        # opens it with a plain `open()`, which raises OSError/FileNotFoundError -- a subclass
        # of OSError -- on failure), in addition to an actual login rejection (Fault). All are
        # reported identically as "login_rejected" -- no new status code/error vocabulary is
        # introduced here since the frontend has already shipped against the existing one.
        return _rejected(start_response, "login_rejected")

    success_headers: List[Any] = [("Cache-Control", "no-store")]
    if output_token:
        success_headers.append(
            (
                "WWW-Authenticate",
                "Negotiate " + base64.b64encode(output_token).decode("ascii"),  # type: ignore[reportUnknownArgumentType]
            )
        )

    return _json_response(
        start_response,
        "200 OK",
        {"username": username, "token": token},
        extra_headers=success_headers,
    )
