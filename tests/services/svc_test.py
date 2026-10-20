# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Cobbler contributors
"""
Tests for ``cobbler.services.svc``'s XML-RPC target resolution (split-container support).

``CobblerSvc`` is stubbed out so these are unit tests and must not require a live cobblerd -
only the URL it is constructed with is of interest here.
"""

import pathlib
from typing import Any, Dict, Optional

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


@pytest.mark.parametrize(
    "uri,expected_subfile",
    [
        (
            "/op/autoinstall/system/example_system/file/built-in-user-data/subfile/user-data",
            "user-data",
        ),
        (
            "/op/autoinstall/system/example_system/file/built-in-user-data/subfile/meta-data",
            "meta-data",
        ),
        (
            "/op/autoinstall/system/example_system/file/built-in-user-data/subfile/vendor-data",
            "vendor-data",
        ),
        (
            "/op/autoinstall/system/example_system/file/built-in-user-data/subfile/network-config",
            "network-config",
        ),
        (
            # The bare seed URL cloud-init would fetch directly (no subfile appended yet).
            "/op/autoinstall/system/example_system/file/built-in-user-data/subfile/",
            "",
        ),
        (
            # Non cloud-init autoinstall types never add a "subfile" path segment at all.
            "/op/autoinstall/system/example_system/file/built-in-default.ks",
            None,
        ),
    ],
)
def test_fillup_form_dict_parses_subfile_path_segment(
    uri: str, expected_subfile: Optional[str]
) -> None:
    """
    The ``subfile/<name>`` URL path segment introduced for cloud-init sub-file selection must be parsed into a
    regular, explicit "subfile" form field by the generic label/value URL tokenizer, regardless of how many path
    segments precede it.
    """
    form: Dict[Any, Any] = {}
    # pylint: disable=protected-access
    svc.__fillup_form_dict(form, uri)  # type: ignore[attr-defined]

    assert form.get("subfile") == expected_subfile


class _StubCobblerSvcAutoinstall:
    """
    Records the keyword arguments ``application()`` actually dispatched to ``autoinstall()``, so tests can assert
    on exactly what reached the handler without needing a live cobblerd.
    """

    last_kwargs: Dict[str, Any] = {}

    def __init__(self, server: str = "") -> None:
        pass

    def autoinstall(
        self,
        profile: Optional[str] = None,
        system: Optional[str] = None,
        file: str = "",
        subfile: str = "",
        **kwargs: Any,
    ) -> str:
        _StubCobblerSvcAutoinstall.last_kwargs = {
            "profile": profile,
            "system": system,
            "file": file,
            "subfile": subfile,
            **kwargs,
        }
        return "ok"


@pytest.fixture
def stub_cobbler_svc_autoinstall(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(svc, "CobblerSvc", _StubCobblerSvcAutoinstall)
    return _StubCobblerSvcAutoinstall


def _call_application_with_uri(raw_uri: str, query_string: str = "") -> None:
    environ: Dict[str, Any] = {"RAW_URI": raw_uri, "QUERY_STRING": query_string}
    svc.application(environ, lambda status, headers: None)


def test_autoinstall_subfile_selected_via_url_path(
    monkeypatch: pytest.MonkeyPatch, stub_cobbler_svc_autoinstall: Any
) -> None:
    """
    A ``subfile/<name>`` URL path segment must reach ``autoinstall()``'s ``subfile`` parameter end-to-end through
    ``application()``'s dispatch.
    """
    _write_settings()
    monkeypatch.delenv("COBBLER_XMLRPC_HOST", raising=False)

    _call_application_with_uri(
        "/op/autoinstall/system/example_system/file/built-in-user-data/subfile/meta-data"
    )

    assert stub_cobbler_svc_autoinstall.last_kwargs["subfile"] == "meta-data"


def test_autoinstall_subfile_not_selected_via_query_string(
    monkeypatch: pytest.MonkeyPatch, stub_cobbler_svc_autoinstall: Any
) -> None:
    """
    Subfile selection must only ever work through the URL path, never through a query string. A client appending
    ``?subfile=meta-data`` (or any other "subfile"-named query parameter) must not influence which cloud-init
    sub-file gets rendered -- ``application()`` stores the parsed query string under its own nested
    ``query_string`` form field rather than spreading it into top-level keyword arguments, so it can never bind to
    ``autoinstall()``'s explicit ``subfile`` parameter.
    """
    _write_settings()
    monkeypatch.delenv("COBBLER_XMLRPC_HOST", raising=False)

    _call_application_with_uri(
        "/op/autoinstall/system/example_system/file/built-in-user-data",
        query_string="subfile=meta-data",
    )

    assert stub_cobbler_svc_autoinstall.last_kwargs["subfile"] == ""
    assert stub_cobbler_svc_autoinstall.last_kwargs["query_string"] == {
        "subfile": ["meta-data"]
    }


@pytest.mark.parametrize(
    "bare_segment_kwargs,expected_subfile",
    [
        ({"user-data": ""}, "user-data"),
        ({"vendor-data": ""}, "vendor-data"),
        ({"meta-data": ""}, "meta-data"),
        ({"network-config": ""}, "network-config"),
        ({}, ""),
    ],
)
def test_autoinstall_falls_back_to_kwargs_for_backwards_compatibility(
    monkeypatch: pytest.MonkeyPatch,
    bare_segment_kwargs: Dict[str, Any],
    expected_subfile: str,
) -> None:
    """
    Regression test: before the ``subfile/<name>`` URL path segment existed, the sub-file to render was selected by
    scanning for one of four literal keys directly in ``**kwargs`` -- the bare trailing segment form (e.g.
    ``file/<template>/user-data``, parsed by ``application()`` into a dangling ``{"user-data": ""}`` kwarg). This
    must keep being honored as a fallback whenever the explicit ``subfile`` parameter is empty, so URLs built
    against the previous convention don't silently break.
    """
    captured: Dict[str, Any] = {}

    class _StubRemote:
        def generate_autoinstall(
            self,
            obj_name: str,
            obj_type: str,
            _ref: str,
            file: str,
            subfile: str,
        ) -> str:
            captured["subfile"] = subfile
            return "ok"

    test_svc = svc.CobblerSvc(server="http://127.0.0.1")
    monkeypatch.setattr(svc.CobblerSvc, "remote", property(lambda self: _StubRemote()))

    test_svc.autoinstall(
        system="example_system", file="built-in-user-data", **bare_segment_kwargs
    )

    assert captured["subfile"] == expected_subfile


def test_autoinstall_explicit_subfile_takes_priority_over_kwargs_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    When the real ``subfile`` parameter is set (via the ``subfile/<name>`` URL path segment), it must win over the
    backwards-compatible kwargs fallback, never be overridden by it.
    """
    captured: Dict[str, Any] = {}

    class _StubRemote:
        def generate_autoinstall(
            self,
            obj_name: str,
            obj_type: str,
            _ref: str,
            file: str,
            subfile: str,
        ) -> str:
            captured["subfile"] = subfile
            return "ok"

    test_svc = svc.CobblerSvc(server="http://127.0.0.1")
    monkeypatch.setattr(svc.CobblerSvc, "remote", property(lambda self: _StubRemote()))

    test_svc.autoinstall(
        system="example_system",
        file="built-in-user-data",
        subfile="meta-data",
        **{"user-data": ""},
    )

    assert captured["subfile"] == "meta-data"
