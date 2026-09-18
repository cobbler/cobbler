"""
Authentication module that defers to Apache and trusts
what Apache trusts.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import hmac
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
    Validate a username/password combo against the shared secret.

    Performs timing-attack-safe comparison using hmac.compare_digest().
    The username and api_handle parameters are not used for the check itself.

    :param api_handle: This parameter is not used.
    :param username: This parameter is not used.
    :param password: This should be the internal Cobbler secret.
    :return: True if the password matches the secret, otherwise False.
    """
    # Retrieve the shared secret once
    secret = utils.get_shared_secret()

    # If secret is not configured (returns -1), never authenticate
    if secret == -1:
        return False

    # If the secret is not a string, or is empty (e.g. web.ss was truncated
    # by cobblerd while regenerating it), reject. An empty secret must never
    # authenticate -- otherwise an empty password would match via
    # hmac.compare_digest("", "").
    if not isinstance(secret, str) or not secret:
        return False

    # Use timing-attack-safe comparison
    return hmac.compare_digest(password.encode("UTF-8"), secret.encode("UTF-8"))
