"""
Tests for svc/sso_login.py, the Kerberos/SPNEGO SSO bridge WSGI script.

svc/ is not a Python package (its scripts are stdlib-only mod_wsgi scripts, deployed as-is,
not imported as part of the ``cobbler`` package), so the module under test is loaded directly
from its file path via ``importlib``.
"""

import importlib.util
import io
import json
import xmlrpc.client
from pathlib import Path
from unittest import mock

SSO_LOGIN_PATH = Path(__file__).resolve().parent.parent.parent / "svc" / "sso_login.py"

_spec = importlib.util.spec_from_file_location("sso_login", SSO_LOGIN_PATH)
sso_login = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sso_login)


class StartResponseRecorder:
    """Minimal WSGI start_response stub that records what it was called with."""

    def __init__(self):
        self.status = None
        self.headers = None

    def __call__(self, status, headers):
        self.status = status
        self.headers = headers


def _fake_open_for(secret_content=None, settings_yaml_content="xmlrpc_port: 25151\n"):
    """
    Build a stand-in for builtins.open() that serves canned content for the two paths
    sso_login.application() reads, and raises FileNotFoundError for anything else.
    """
    files = {}
    if secret_content is not None:
        files["/var/lib/cobbler/web.ss"] = secret_content
    if settings_yaml_content is not None:
        files["/etc/cobbler/settings.yaml"] = settings_yaml_content

    def fake_open(path, *args, **kwargs):
        if path not in files:
            raise FileNotFoundError(path)
        return io.StringIO(files[path])

    return fake_open


def test_missing_remote_user_returns_401():
    environ = {}
    start_response = StartResponseRecorder()

    body = sso_login.application(environ, start_response)

    assert start_response.status == "401 UNAUTHORIZED"
    assert json.loads(b"".join(body)) == {"error": "no_authenticated_user"}


def test_unreadable_shared_secret_returns_403():
    environ = {"REMOTE_USER": "alice@EXAMPLE.COM"}
    start_response = StartResponseRecorder()

    with mock.patch("builtins.open", side_effect=OSError("no such file")):
        body = sso_login.application(environ, start_response)

    assert start_response.status == "403 FORBIDDEN"
    assert json.loads(b"".join(body)) == {"error": "sso_not_configured"}


def test_empty_shared_secret_returns_403():
    # cobblerd truncates /var/lib/cobbler/web.ss before rewriting it during startup/rotation.
    # An empty secret must never be forwarded to login() -- treat it like "not configured".
    environ = {"REMOTE_USER": "alice@EXAMPLE.COM"}
    start_response = StartResponseRecorder()

    fake_open = _fake_open_for(secret_content="")
    fake_server = mock.Mock()

    with mock.patch("builtins.open", side_effect=fake_open), mock.patch(
        "xmlrpc.client.ServerProxy", return_value=fake_server
    ):
        body = sso_login.application(environ, start_response)

    assert start_response.status == "403 FORBIDDEN"
    assert json.loads(b"".join(body)) == {"error": "sso_not_configured"}
    fake_server.login.assert_not_called()


def test_empty_settings_yaml_falls_back_to_default_port():
    # An empty settings.yaml makes yaml.safe_load() return None. This must not raise
    # AttributeError when looking up xmlrpc_port -- it should fall back to the default port.
    environ = {"REMOTE_USER": "alice@EXAMPLE.COM"}
    start_response = StartResponseRecorder()

    fake_open = _fake_open_for(secret_content="s3cr3t", settings_yaml_content="")
    fake_server = mock.Mock()
    fake_server.login.return_value = "abc123token"

    with mock.patch("builtins.open", side_effect=fake_open), mock.patch(
        "xmlrpc.client.ServerProxy", return_value=fake_server
    ) as server_proxy:
        body = sso_login.application(environ, start_response)

    assert start_response.status == "200 OK"
    assert json.loads(b"".join(body)) == {"username": "alice", "token": "abc123token"}
    server_proxy.assert_called_once_with("http://127.0.0.1:25151/", allow_none=True)


def test_missing_settings_yaml_returns_503():
    environ = {"REMOTE_USER": "alice@EXAMPLE.COM"}
    start_response = StartResponseRecorder()

    fake_open = _fake_open_for(secret_content="s3cr3t", settings_yaml_content=None)

    with mock.patch("builtins.open", side_effect=fake_open):
        body = sso_login.application(environ, start_response)

    assert start_response.status == "503 SERVICE UNAVAILABLE"
    assert json.loads(b"".join(body)) == {"error": "backend_unavailable"}


def test_backend_unavailable_returns_503():
    environ = {"REMOTE_USER": "alice@EXAMPLE.COM"}
    start_response = StartResponseRecorder()

    fake_open = _fake_open_for(secret_content="s3cr3t")
    fake_server = mock.Mock()
    fake_server.login.side_effect = ConnectionRefusedError("connection refused")

    with mock.patch("builtins.open", side_effect=fake_open), mock.patch(
        "xmlrpc.client.ServerProxy", return_value=fake_server
    ):
        body = sso_login.application(environ, start_response)

    assert start_response.status == "503 SERVICE UNAVAILABLE"
    assert json.loads(b"".join(body)) == {"error": "backend_unavailable"}


def test_login_fault_returns_403():
    environ = {"REMOTE_USER": "alice@EXAMPLE.COM"}
    start_response = StartResponseRecorder()

    fake_open = _fake_open_for(secret_content="s3cr3t")
    fake_server = mock.Mock()
    fake_server.login.side_effect = xmlrpc.client.Fault(1, "bad login")

    with mock.patch("builtins.open", side_effect=fake_open), mock.patch(
        "xmlrpc.client.ServerProxy", return_value=fake_server
    ):
        body = sso_login.application(environ, start_response)

    assert start_response.status == "403 FORBIDDEN"
    assert json.loads(b"".join(body)) == {"error": "login_rejected"}


def test_happy_path_returns_200_with_normalized_username_and_token():
    environ = {"REMOTE_USER": "alice@EXAMPLE.COM"}
    start_response = StartResponseRecorder()

    fake_open = _fake_open_for(secret_content="s3cr3t")
    fake_server = mock.Mock()
    fake_server.login.return_value = "abc123token"

    with mock.patch("builtins.open", side_effect=fake_open), mock.patch(
        "xmlrpc.client.ServerProxy", return_value=fake_server
    ) as server_proxy:
        body = sso_login.application(environ, start_response)

    assert start_response.status == "200 OK"
    assert json.loads(b"".join(body)) == {"username": "alice", "token": "abc123token"}
    fake_server.login.assert_called_once_with("alice", "s3cr3t")
    server_proxy.assert_called_once_with("http://127.0.0.1:25151/", allow_none=True)
