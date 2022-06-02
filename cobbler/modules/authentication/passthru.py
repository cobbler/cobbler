"""
Authentication module that defers to Apache and trusts
what Apache trusts.
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from cobbler import utils


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always "authn"
    """
    return "authn"


def authenticate(api_handle, username, password) -> bool:
    """
    Validate a username/password combo. Uses cobbler_auth_helper

    :param api_handle: This parameter is not used currently.
    :param username: This parameter is not used currently.
    :param password: This should be the internal Cobbler secret.
    :return: True if the password is the secret, otherwise false.
    """
    return password == utils.get_shared_secret()
