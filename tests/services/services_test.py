"""
Smoke tests for the ``cobbler.services`` package's Gunicorn entry point.

``cobbler/services.py`` was restructured into the ``cobbler/services`` package (with the actual
implementation moved to ``cobbler.services.svc``) so that a second WSGI app can be added alongside
it later. These tests exist to guard the one thing that must never break in that restructuring:
``gunicorn cobbler.services:application`` has to keep resolving to a callable with identical
behavior.
"""

from typing import Any, Dict, List

import cobbler.services


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
