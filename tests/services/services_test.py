"""
Smoke tests for the ``cobbler.services`` package's Gunicorn entry point.

``cobbler/services.py`` was restructured into the ``cobbler/services`` package (with the actual
implementation moved to ``cobbler.services.svc``) so that a second WSGI app can be added alongside
it later. These tests exist to guard the one thing that must never break in that restructuring:
``gunicorn cobbler.services:application`` has to keep resolving to a callable with identical
behavior.
"""

from typing import Any, Dict, List

import pytest

import cobbler.services
import cobbler.services.files
import cobbler.services.svc


def test_application_is_callable() -> None:
    """
    ``cobbler.services.application`` must resolve to a callable, exactly as Gunicorn's
    ``gunicorn cobbler.services:application`` expects.
    """
    assert callable(cobbler.services.application)


def test_application_delegates_to_svc() -> None:
    """
    The package-level ``application`` must behave identically to the previous flat-module one, i.e.
    it must still be reachable with a minimal WSGI environ and return the same response.
    """
    environ: Dict[str, Any] = {"RAW_URI": "/op/index", "QUERY_STRING": ""}
    captured: Dict[str, Any] = {}

    def fake_start_response(status: str, headers: List[Any]) -> None:
        captured["status"] = status
        captured["headers"] = headers

    result = cobbler.services.application(environ, fake_start_response)

    assert result == [b"no mode specified"]
    assert captured["status"] == "200 OK"


def test_tree_paths_dispatch_to_files_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A request path of the shape ``/tree/...`` (i.e. the client-facing ``/cblr/svc/tree/...`` URL
    with Apache's proxy prefix already stripped) must be dispatched to
    ``cobbler.services.files.application``, not the XML-RPC-backed ``svc`` app.
    """
    calls: List[Dict[str, Any]] = []

    def fake_files_app(environ: Dict[str, Any], start_response: Any) -> List[bytes]:
        calls.append(environ)
        start_response("200 OK", [])
        return [b"from files app"]

    monkeypatch.setattr(cobbler.services.files, "application", fake_files_app)

    environ: Dict[str, Any] = {
        "RAW_URI": "/tree/mydistro/repodata/repomd.xml",
        "QUERY_STRING": "",
    }
    result = cobbler.services.application(environ, lambda status, headers: None)

    assert result == [b"from files app"]
    assert len(calls) == 1


def test_httpboot_paths_dispatch_to_files_httpboot_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A request path of the shape ``/httpboot/...`` (Traefik has no on-disk static serving, so this
    is proxied straight to Gunicorn rather than served by a proxy ``Alias`` the way Apache's
    ``cobbler.conf`` does today) must be dispatched to
    ``cobbler.services.files.httpboot_application``.
    """
    calls: List[Dict[str, Any]] = []

    def fake_httpboot_app(environ: Dict[str, Any], start_response: Any) -> List[bytes]:
        calls.append(environ)
        start_response("200 OK", [])
        return [b"from httpboot app"]

    monkeypatch.setattr(
        cobbler.services.files, "httpboot_application", fake_httpboot_app
    )

    environ: Dict[str, Any] = {"RAW_URI": "/httpboot/grub.cfg", "QUERY_STRING": ""}
    result = cobbler.services.application(environ, lambda status, headers: None)

    assert result == [b"from httpboot app"]
    assert len(calls) == 1


def test_images_paths_dispatch_to_files_images_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A request path of the shape ``/images/...`` must be dispatched to
    ``cobbler.services.files.images_application``.
    """
    calls: List[Dict[str, Any]] = []

    def fake_images_app(environ: Dict[str, Any], start_response: Any) -> List[bytes]:
        calls.append(environ)
        start_response("200 OK", [])
        return [b"from images app"]

    monkeypatch.setattr(cobbler.services.files, "images_application", fake_images_app)

    environ: Dict[str, Any] = {"RAW_URI": "/images/boot.img", "QUERY_STRING": ""}
    result = cobbler.services.application(environ, lambda status, headers: None)

    assert result == [b"from images app"]
    assert len(calls) == 1


def test_healthz_path_dispatches_to_files_healthz_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A request path of ``/healthz`` must be dispatched to
    ``cobbler.services.files.healthz_application``, not the XML-RPC-backed ``svc`` app.
    """
    calls: List[Dict[str, Any]] = []

    def fake_healthz_app(environ: Dict[str, Any], start_response: Any) -> List[bytes]:
        calls.append(environ)
        start_response("200 OK", [])
        return [b"OK"]

    monkeypatch.setattr(cobbler.services.files, "healthz_application", fake_healthz_app)

    environ: Dict[str, Any] = {"RAW_URI": "/healthz", "QUERY_STRING": ""}
    result = cobbler.services.application(environ, lambda status, headers: None)

    assert result == [b"OK"]
    assert len(calls) == 1


def test_non_tree_paths_still_dispatch_to_svc_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Every non-``/tree/...`` request path must keep reaching ``cobbler.services.svc.application``,
    exactly as before this task's dispatch logic was added.
    """
    calls: List[Dict[str, Any]] = []
    original = cobbler.services.svc.application

    def spying_svc_app(environ: Dict[str, Any], start_response: Any) -> List[bytes]:
        calls.append(environ)
        return original(environ, start_response)

    monkeypatch.setattr(cobbler.services.svc, "application", spying_svc_app)

    environ: Dict[str, Any] = {"RAW_URI": "/op/index", "QUERY_STRING": ""}
    result = cobbler.services.application(environ, lambda status, headers: None)

    assert result == [b"no mode specified"]
    assert len(calls) == 1
