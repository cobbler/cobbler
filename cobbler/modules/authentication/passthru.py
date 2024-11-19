"""
Authentication module that defers to Apache and trusts
what Apache trusts.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from typing import TYPE_CHECKING

from cobbler import utils

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always "authn"
    """
    return "authn"


def authenticate(api_handle: "CobblerAPI", username: str, password: str) -> bool:
    """
    Validate a username/password combo.

    :param api_handle: This parameter is not used currently.
    :param username: This parameter is not used currently.
    :param password: This parameter is not used currently.
    :return: True always - authentication is handled by web server.
    """
    return True
