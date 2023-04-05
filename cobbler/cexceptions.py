"""
Custom exceptions for Cobbler
"""
from typing import Any, Iterable

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>


class CobblerException(Exception):
    """
    This is the default Cobbler exception where all other exceptions are inheriting from.
    """

    def __init__(self, value: Any, *args: Iterable[str]):
        """
        Default constructor for the Exception.

        Bad example: ``CobblerException("Profile %s not found" % profile_name)``

        Good example: ``CobblerException("Profile %s not found", profile_name)``

        :param value: The string representation of the Exception. Do not glue strings and pass them as one. Instead pass
                      them as params and let the constructor of the Exception build the string like (same as it should
                      be done with logging calls). Example see above.
        :param args: Optional arguments which replace a ``%s`` in a Python string.
        """
        self.value = value % args
        # this is a hack to work around some odd exception handling in older pythons
        self.from_cobbler = 1

    def __str__(self) -> str:
        """
        This is the string representation of the base Cobbler Exception.
        :return: self.value as a string represented.
        """
        return repr(self.value)


class CX(CobblerException):
    """
    This is a general exception which gets thrown often inside Cobbler.
    """
