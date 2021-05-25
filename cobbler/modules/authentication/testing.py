"""
Authentication module that denies everything.
Unsafe demo.  Allows anyone in with testing/testing.

Copyright 2007-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always "authn"
    """
    return "authn"


def authenticate(api_handle, username: str, password: str) -> bool:
    """
    Validate a username/password combo, returning True/False

    Thanks to http://trac.edgewall.org/ticket/845 for supplying the algorithm info.

    :param api_handle: This parameter is not used currently.
    :param username: The username which should be checked.
    :param password: The password which should be checked.
    :return: True if username is "testing" and password is "testing". Otherwise False.
    """

    if username == "testing" and password == "testing":
        return True
    return False
