# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Cobbler contributors
"""
Tests for ``cobbler.services.svc``'s XML-RPC target resolution (split-container support).

``CobblerSvc`` is stubbed out so these are unit tests and must not require a live cobblerd -
only the URL it is constructed with is of interest here.
"""

import pathlib
from typing import Any, Dict

import pytest
import yaml

from cobbler.services import svc

SETTINGS_PATH = pathlib.Path("/etc/cobbler/settings.yaml")


class _StubCobblerSvc:
    """Records the ``server`` URL it was constructed with and exposes no operations, so
    ``application()`` falls through to its "Unknown endpoint!" 404 branch without needing any
    real XML-RPC interaction."""

    last_server = ""

    def __init__(self, server: str = "") -> None:
        _StubCobblerSvc.last_server = server


@pytest.fixture
def stub_cobbler_svc(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(svc, "CobblerSvc", _StubCobblerSvc)
    return _StubCobblerSvc


def _write_settings(**extra: Any) -> None:
    content: Dict[str, Any] = {"xmlrpc_port": 25151}
    content.update(extra)
    SETTINGS_PATH.write_text(yaml.dump(content), encoding="UTF-8")


def _call_application() -> None:
    environ: Dict[str, Any] = {"RAW_URI": "/op/index", "QUERY_STRING": ""}
    svc.application(environ, lambda status, headers: None)


def test_application_defaults_to_localhost_when_unset(
    monkeypatch: pytest.MonkeyPatch, stub_cobbler_svc: Any
) -> None:
    """
    Neither the settings file nor the environment variable set an xmlrpc_host - the
    default must be "127.0.0.1", i.e. today's exact non-containerized behavior.
    """
    _write_settings()
    monkeypatch.delenv("COBBLER_XMLRPC_HOST", raising=False)

    _call_application()

    assert stub_cobbler_svc.last_server == "http://127.0.0.1:25151"


def test_application_uses_settings_value_when_env_var_unset(
    monkeypatch: pytest.MonkeyPatch, stub_cobbler_svc: Any
) -> None:
    _write_settings(xmlrpc_host="cobblerd")
    monkeypatch.delenv("COBBLER_XMLRPC_HOST", raising=False)

    _call_application()

    assert stub_cobbler_svc.last_server == "http://cobblerd:25151"


def test_application_env_var_takes_precedence_over_settings_value(
    monkeypatch: pytest.MonkeyPatch, stub_cobbler_svc: Any
) -> None:
    _write_settings(xmlrpc_host="cobblerd")
    monkeypatch.setenv("COBBLER_XMLRPC_HOST", "from-env")

    _call_application()

    assert stub_cobbler_svc.last_server == "http://from-env:25151"
