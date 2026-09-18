"""
Authentication module that defers to Apache and trusts
what Apache trusts.
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import hmac

from cobbler import utils


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always "authn"
    """
    return "authn"


def authenticate(api_handle, username, password) -> bool:
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

    # If the secret is empty (e.g. web.ss was truncated by cobblerd while
    # regenerating it), never authenticate -- otherwise an empty password
    # would match via hmac.compare_digest("" == "").
    if not secret:
        return False

    # If either password or secret is not a string, reject
    if not isinstance(password, str) or not isinstance(secret, str):
        return False

    # Use timing-attack-safe comparison
    return hmac.compare_digest(password.encode("UTF-8"), secret.encode("UTF-8"))
