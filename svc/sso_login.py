"""
This module is a mod_wsgi application that bridges an Apache-authenticated
Kerberos/SPNEGO identity to a Cobbler XML-RPC login token.

SECURITY CONTRACT: This script performs *no* authentication of its own. It
must only ever be reachable through an Apache ``<Location>`` block that
itself performs Kerberos/SPNEGO negotiation (``mod_auth_gssapi``,
``Require valid-user``) before this script is invoked. The only signal this
script trusts is the WSGI ``REMOTE_USER`` environ key, which is populated by
Apache/mod_auth_gssapi *after* a successful Kerberos negotiation. This
script must never read any HTTP header (e.g. ``HTTP_X_REMOTE_USER`` or
similar) as a substitute for ``REMOTE_USER`` -- HTTP headers can be set by
any client and are not a trustworthy authentication signal on their own.

Copyright 2010, Red Hat, Inc and Others

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
# Only add standard python modules here. When running under a virtualenv other modules are not
# available at this point.

import json
import xmlrpc.client

import yaml


def application(environ, start_response):

    remote_user = environ.get("REMOTE_USER")

    if not remote_user:
        # This is the expected/normal case when the caller has no Kerberos ticket yet.
        return _json_response(start_response, "401 UNAUTHORIZED", {"error": "no_authenticated_user"})

    username = remote_user.split("@", 1)[0]

    if not username:
        return _json_response(start_response, "403 FORBIDDEN", {"error": "empty_username"})

    try:
        with open("/var/lib/cobbler/web.ss", encoding="UTF-8") as web_secret_fd:
            shared_secret = web_secret_fd.read()
    except OSError:
        return _json_response(start_response, "403 FORBIDDEN", {"error": "sso_not_configured"})

    if not shared_secret:
        # cobblerd truncates web.ss before rewriting it during startup/rotation. Never
        # forward an empty secret to login() -- treat this the same as "not configured".
        return _json_response(start_response, "403 FORBIDDEN", {"error": "sso_not_configured"})

    # Read config for the XMLRPC port to connect to:
    try:
        with open("/etc/cobbler/settings.yaml", encoding="UTF-8") as main_settingsfile:
            ydata = yaml.safe_load(main_settingsfile)
    except (OSError, yaml.YAMLError):
        return _json_response(start_response, "503 SERVICE UNAVAILABLE", {"error": "backend_unavailable"})
    remote_port = (ydata or {}).get("xmlrpc_port", 25151)

    server = xmlrpc.client.ServerProxy(f"http://127.0.0.1:{remote_port}/", allow_none=True)
    try:
        token = server.login(username, shared_secret)
    except xmlrpc.client.Fault:
        return _json_response(start_response, "403 FORBIDDEN", {"error": "login_rejected"})
    except (OSError, xmlrpc.client.ProtocolError):
        # cobblerd is down/restarting or otherwise unreachable (e.g. ConnectionRefusedError,
        # socket.timeout, xmlrpc.client.ProtocolError).
        return _json_response(start_response, "503 SERVICE UNAVAILABLE", {"error": "backend_unavailable"})

    return _json_response(start_response, "200 OK", {"username": username, "token": token})


def _json_response(start_response, status, body):
    content = json.dumps(body).encode("utf-8")
    response_headers = [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(content))),
    ]
    start_response(status, response_headers)
    return [content]
