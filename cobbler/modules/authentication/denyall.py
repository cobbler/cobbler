"""
Authentication module that denies everything.
Used to disable the WebUI by default.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "authn"


def authenticate(api_handle: "CobblerAPI", username: str, password: str) -> bool:
    """
    Validate a username/password combo, always returning false.

    :returns: False
    """
    return False
