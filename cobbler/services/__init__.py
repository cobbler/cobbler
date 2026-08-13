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
    Requests for ``/httpboot/...`` and ``/images/...`` (UEFI HTTP(S) boot files, statically served
    by Apache's own ``Alias`` directives today -- not proxied, so no prefix-stripping happens for
    them) are likewise dispatched straight to :mod:`cobbler.services.files`. ``/healthz`` (a
    liveness check backed by an XML-RPC round trip against cobblerd, for Docker's ``HEALTHCHECK``
    and orchestration tooling) is dispatched there too. Everything else falls through to the
    existing XML-RPC-backed :mod:`cobbler.services.svc` app, unchanged.

    :param environ:
    :param start_response:
    :return:
    """
    raw_uri = environ.get("RAW_URI", "")
    path = raw_uri.partition("?")[0]
    if path == "/tree" or path.startswith("/tree/"):
        return files.application(environ, start_response)
    if path == "/httpboot" or path.startswith("/httpboot/"):
        return files.httpboot_application(environ, start_response)
    if path == "/images" or path.startswith("/images/"):
        return files.images_application(environ, start_response)
    if path == "/healthz":
        return files.healthz_application(environ, start_response)
    return svc.application(environ, start_response)
