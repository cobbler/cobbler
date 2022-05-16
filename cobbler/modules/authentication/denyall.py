"""
Authentication module that denies everything.
Used to disable the WebUI by default.
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "authn"


def authenticate(api_handle, username, password) -> bool:
    """
    Validate a username/password combo, returning True/False

    Thanks to http://trac.edgewall.org/ticket/845 for supplying
    the algorithm info.
    """
    return False
