# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Cobbler contributors
"""
Tests for ``cobbler.services.sso``, the native Kerberos/GSSAPI SPNEGO negotiation endpoint.

``gssapi`` is not a hard dependency of the test environment (and must never be imported at module
import time by ``cobbler.services.sso`` itself -- see that module's docstring), so it is faked out
entirely here via a synthetic module injected into ``sys.modules``. No real KDC or keytab is
required to run these tests. The XML-RPC call that exchanges the negotiated principal for a
Cobbler session token is likewise mocked, mirroring ``tests/services/files_test.py``'s
``stub_remote`` pattern.
"""

import base64
import json
import sys
import types
import xmlrpc.client
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from cobbler.services import sso


class _Response:
    """Small helper that captures a WSGI ``start_response`` call and the resulting body."""

    def __init__(self) -> None:
        self.status: str = ""
        self.headers: List[Any] = []

    def start_response(self, status: str, headers: List[Any]) -> None:
        self.status = status
        self.headers = headers

    def header(self, name: str) -> Optional[str]:
        for key, value in self.headers:
            if key.lower() == name.lower():
                return value
        return None

    def has_header(self, name: str) -> bool:
        return any(key.lower() == name.lower() for key, _ in self.headers)


def _call(environ: Dict[str, Any]):
    resp = _Response()
    body_iter = sso.application(environ, resp.start_response)
    body = b"".join(body_iter)
    return resp, json.loads(body.decode("utf-8"))


def _environ(auth_header: Optional[str] = None) -> Dict[str, Any]:
    environ: Dict[str, Any] = {}
    if auth_header is not None:
        environ["HTTP_AUTHORIZATION"] = auth_header
    return environ


def _negotiate_header(raw_token: bytes = b"faketoken") -> str:
    return "Negotiate " + base64.b64encode(raw_token).decode("ascii")


@pytest.fixture(autouse=True)
def krb5_ktname(monkeypatch: pytest.MonkeyPatch) -> None:
    """By default, a keytab is "configured" -- individual tests override this."""
    monkeypatch.setenv("KRB5_KTNAME", "/etc/cobbler.keytab")


@pytest.fixture(autouse=True)
def stub_shared_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """Never touch the real ``/var/lib/cobbler/web.ss`` from a test."""
    monkeypatch.setattr(sso.utils, "get_shared_secret", lambda: "the-shared-secret")
    return "the-shared-secret"


@pytest.fixture
def stub_remote(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace ``files._build_remote`` (as reused by ``sso.py``) with a ``MagicMock`` remote."""
    mock_remote = MagicMock()
    monkeypatch.setattr(sso.files, "_build_remote", lambda: mock_remote)
    return mock_remote


@pytest.fixture
def fake_gssapi(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """
    Install a synthetic ``gssapi`` module into ``sys.modules`` so ``import gssapi`` inside
    ``sso.application`` succeeds and hands back mocks for ``Credentials``/``SecurityContext``.
    """
    module = types.ModuleType("gssapi")
    module.Credentials = MagicMock(name="Credentials")  # type: ignore[attr-defined]
    module.SecurityContext = MagicMock(name="SecurityContext")  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gssapi", module)
    return module


def _configure_context(
    fake_gssapi: types.ModuleType,
    *,
    complete: bool = True,
    initiator_name: str = "alice@EXAMPLE.COM",
    output_token: Optional[bytes] = None,
    step_side_effect: Optional[BaseException] = None,
) -> MagicMock:
    context = fake_gssapi.SecurityContext.return_value  # type: ignore[attr-defined]
    if step_side_effect is not None:
        context.step.side_effect = step_side_effect
    else:
        context.step.return_value = output_token
    context.complete = complete
    context.initiator_name = initiator_name
    return context


# ---------------------------------------------------------------------------------------------
# 1. gssapi unimportable -> 501
# ---------------------------------------------------------------------------------------------


def test_gssapi_unimportable_returns_501(monkeypatch: pytest.MonkeyPatch) -> None:
    # A None entry in sys.modules forces the "import gssapi" statement to raise ImportError,
    # regardless of whether the real package happens to be installed in the test environment.
    monkeypatch.setitem(sys.modules, "gssapi", None)

    resp, body = _call(_environ())

    assert resp.status == "501 Not Implemented"
    assert body == {"error": "sso_not_configured"}


# ---------------------------------------------------------------------------------------------
# 2. KRB5_KTNAME unset -> 501
# ---------------------------------------------------------------------------------------------


def test_krb5_ktname_unset_returns_501(
    monkeypatch: pytest.MonkeyPatch, fake_gssapi: types.ModuleType
) -> None:
    monkeypatch.delenv("KRB5_KTNAME", raising=False)

    resp, body = _call(_environ())

    assert resp.status == "501 Not Implemented"
    assert body == {"error": "sso_not_configured"}


# ---------------------------------------------------------------------------------------------
# 3. missing/malformed Authorization header -> 401 + WWW-Authenticate: Negotiate
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "auth_header",
    [None, "", "Basic dXNlcjpwYXNz", "Negotiate"],
    ids=["missing", "empty", "basic-scheme", "negotiate-with-no-token"],
)
def test_missing_or_malformed_authorization_header_returns_401(
    fake_gssapi: types.ModuleType, auth_header: Optional[str]
) -> None:
    resp, body = _call(_environ(auth_header))

    assert resp.status == "401 Unauthorized"
    assert body == {"error": "no_authenticated_user"}
    assert resp.header("WWW-Authenticate") == "Negotiate"


# ---------------------------------------------------------------------------------------------
# 4. context.step() raises a gssapi exception -> 403 login_rejected
# ---------------------------------------------------------------------------------------------


def test_context_step_raising_exception_returns_403_login_rejected(
    fake_gssapi: types.ModuleType,
) -> None:
    _configure_context(fake_gssapi, step_side_effect=RuntimeError("bad token"))

    resp, body = _call(_environ(_negotiate_header()))

    assert resp.status == "403 Forbidden"
    assert body == {"error": "login_rejected"}


# ---------------------------------------------------------------------------------------------
# 5. context.complete is False -> 403 negotiation_incomplete
# ---------------------------------------------------------------------------------------------


def test_negotiation_incomplete_returns_403(fake_gssapi: types.ModuleType) -> None:
    _configure_context(fake_gssapi, complete=False, output_token=b"more-please")

    resp, body = _call(_environ(_negotiate_header()))

    assert resp.status == "403 Forbidden"
    assert body == {"error": "negotiation_incomplete"}


# ---------------------------------------------------------------------------------------------
# 6. Happy path -> 200 with {"username": ..., "token": ...}
# ---------------------------------------------------------------------------------------------


def test_happy_path_returns_200_with_username_and_token(
    fake_gssapi: types.ModuleType, stub_remote: MagicMock, stub_shared_secret: str
) -> None:
    _configure_context(
        fake_gssapi,
        complete=True,
        initiator_name="alice@EXAMPLE.COM",
        output_token=b"mutual-auth-token",
    )
    stub_remote.login.return_value = "abc123token"

    resp, body = _call(_environ(_negotiate_header()))

    assert resp.status == "200 OK"
    assert body == {"username": "alice", "token": "abc123token"}
    stub_remote.login.assert_called_once_with("alice", stub_shared_secret)
    assert resp.header("WWW-Authenticate") == _negotiate_header(b"mutual-auth-token")


def test_happy_path_without_output_token_omits_www_authenticate_header(
    fake_gssapi: types.ModuleType, stub_remote: MagicMock
) -> None:
    _configure_context(
        fake_gssapi, complete=True, initiator_name="bob@EXAMPLE.COM", output_token=None
    )
    stub_remote.login.return_value = "xyz789token"

    resp, body = _call(_environ(_negotiate_header()))

    assert resp.status == "200 OK"
    assert body == {"username": "bob", "token": "xyz789token"}
    assert not resp.has_header("WWW-Authenticate")


def test_happy_path_sets_cache_control_no_store(
    fake_gssapi: types.ModuleType, stub_remote: MagicMock
) -> None:
    # The response body carries a bearer token; it must never be cached.
    _configure_context(
        fake_gssapi,
        complete=True,
        initiator_name="alice@EXAMPLE.COM",
        output_token=None,
    )
    stub_remote.login.return_value = "abc123token"

    resp, _body = _call(_environ(_negotiate_header()))

    assert resp.status == "200 OK"
    assert resp.header("Cache-Control") == "no-store"


# ---------------------------------------------------------------------------------------------
# 7. login() raises xmlrpc.client.Fault -> 403 login_rejected
# ---------------------------------------------------------------------------------------------


def test_login_fault_returns_403_login_rejected(
    fake_gssapi: types.ModuleType, stub_remote: MagicMock
) -> None:
    _configure_context(fake_gssapi, complete=True, initiator_name="alice@EXAMPLE.COM")
    stub_remote.login.side_effect = xmlrpc.client.Fault(1, "authentication failed")

    resp, body = _call(_environ(_negotiate_header()))

    assert resp.status == "403 Forbidden"
    assert body == {"error": "login_rejected"}


def test_login_oserror_returns_403_login_rejected(
    fake_gssapi: types.ModuleType, stub_remote: MagicMock
) -> None:
    """cobblerd unreachable/refused -- must not propagate as an unhandled 500."""
    _configure_context(fake_gssapi, complete=True, initiator_name="alice@EXAMPLE.COM")
    stub_remote.login.side_effect = ConnectionRefusedError("connection refused")

    resp, body = _call(_environ(_negotiate_header()))

    assert resp.status == "403 Forbidden"
    assert body == {"error": "login_rejected"}


def test_login_protocol_error_returns_403_login_rejected(
    fake_gssapi: types.ModuleType, stub_remote: MagicMock
) -> None:
    """A malformed XML-RPC response from cobblerd -- must not propagate as an unhandled 500."""
    _configure_context(fake_gssapi, complete=True, initiator_name="alice@EXAMPLE.COM")
    stub_remote.login.side_effect = xmlrpc.client.ProtocolError(
        "http://127.0.0.1:25151", 500, "Internal Server Error", {}
    )

    resp, body = _call(_environ(_negotiate_header()))

    assert resp.status == "403 Forbidden"
    assert body == {"error": "login_rejected"}


def test_build_remote_failure_returns_403_login_rejected(
    monkeypatch: pytest.MonkeyPatch, fake_gssapi: types.ModuleType
) -> None:
    """
    ``files._build_remote()`` itself can raise (e.g. a missing/unreadable
    ``/etc/cobbler/settings.yaml``, surfaced as ``FileNotFoundError``, an ``OSError``
    subclass) -- must not propagate as an unhandled 500 either.
    """
    _configure_context(fake_gssapi, complete=True, initiator_name="alice@EXAMPLE.COM")
    monkeypatch.setattr(
        sso.files,
        "_build_remote",
        MagicMock(side_effect=FileNotFoundError("settings.yaml missing")),
    )

    resp, body = _call(_environ(_negotiate_header()))

    assert resp.status == "403 Forbidden"
    assert body == {"error": "login_rejected"}


# ---------------------------------------------------------------------------------------------
# context.complete / context.initiator_name themselves raising a gssapi exception (both are
# properties backed by C library calls) -> 403 login_rejected, never an unhandled 500.
# ---------------------------------------------------------------------------------------------


class _ContextWithRaisingComplete:
    """A fake SecurityContext whose ``complete`` property raises, like a real GSSError would."""

    initiator_name = "alice@EXAMPLE.COM"

    def step(self, token: bytes) -> Optional[bytes]:  # pylint: disable=unused-argument
        return None

    @property
    def complete(self) -> bool:
        raise RuntimeError("gss_inquire_context failed")


class _ContextWithRaisingInitiatorName:
    """A fake SecurityContext whose ``initiator_name`` property raises."""

    complete = True

    def step(self, token: bytes) -> Optional[bytes]:  # pylint: disable=unused-argument
        return None

    @property
    def initiator_name(self) -> str:
        raise RuntimeError("gss_inquire_context failed")


def test_complete_property_raising_returns_403_login_rejected(
    fake_gssapi: types.ModuleType,
) -> None:
    fake_gssapi.SecurityContext.return_value = (  # type: ignore[attr-defined]
        _ContextWithRaisingComplete()
    )

    resp, body = _call(_environ(_negotiate_header()))

    assert resp.status == "403 Forbidden"
    assert body == {"error": "login_rejected"}


def test_initiator_name_property_raising_returns_403_login_rejected(
    fake_gssapi: types.ModuleType,
) -> None:
    fake_gssapi.SecurityContext.return_value = (  # type: ignore[attr-defined]
        _ContextWithRaisingInitiatorName()
    )

    resp, body = _call(_environ(_negotiate_header()))

    assert resp.status == "403 Forbidden"
    assert body == {"error": "login_rejected"}


# ---------------------------------------------------------------------------------------------
# Bonus: an empty normalized username (principal starting with "@") -> 403 empty_username
# ---------------------------------------------------------------------------------------------


def test_empty_normalized_username_returns_403(
    fake_gssapi: types.ModuleType, stub_remote: MagicMock
) -> None:
    _configure_context(fake_gssapi, complete=True, initiator_name="@EXAMPLE.COM")

    resp, body = _call(_environ(_negotiate_header()))

    assert resp.status == "403 Forbidden"
    assert body == {"error": "empty_username"}
    stub_remote.login.assert_not_called()
