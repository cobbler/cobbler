# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: based on code copyright 2007 Albert P. Tobey <tobert@gmail.com>
# SPDX-FileCopyrightText: additions: 2007-2009 Michael DeHaan <michael.dehaan AT gmail>
"""
Gunicorn entry point for Cobbler's WSGI service(s): ``gunicorn cobbler.services:application``.
"""

from typing import Any, Callable, Dict, List

from cobbler.services import svc

# Placeholder for future dispatch logic between svc's XML-RPC backed app and a future direct-disk file-serving app.


def application(
    environ: Dict[str, Any], start_response: Callable[[str, List[Any]], None]
) -> List[bytes]:
    """
    WSGI entrypoint for Gunicorn.

    :param environ:
    :param start_response:
    :return:
    """
    return svc.application(environ, start_response)
