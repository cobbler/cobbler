# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: based on code copyright 2007 Albert P. Tobey <tobert@gmail.com>
# SPDX-FileCopyrightText: additions: 2007-2009 Michael DeHaan <michael.dehaan AT gmail>
"""
Gunicorn entry point for Cobbler's WSGI service(s): ``gunicorn cobbler.services:application``.
"""

from typing import Any, Callable, Dict, List

from cobbler.services import files, svc


def application(
    environ: Dict[str, Any], start_response: Callable[[str, List[Any]], None]
) -> List[bytes]:
    """
    WSGI entrypoint for Gunicorn.

    Dispatches requests for the direct-disk distro tree file server (client-facing
    ``/cblr/svc/tree/...``, seen here -- after Apache's ``ProxyPass`` strips the ``/cblr/svc/``
    prefix -- as ``/tree/...`` in ``environ["RAW_URI"]``) to :mod:`cobbler.services.files`.
    Everything else falls through to the existing XML-RPC-backed :mod:`cobbler.services.svc` app,
    unchanged.

    :param environ:
    :param start_response:
    :return:
    """
    raw_uri = environ.get("RAW_URI", "")
    path = raw_uri.partition("?")[0]
    if path == "/tree" or path.startswith("/tree/"):
        return files.application(environ, start_response)
    return svc.application(environ, start_response)
