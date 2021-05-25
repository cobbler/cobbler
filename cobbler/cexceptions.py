"""
Custom exceptions for Cobbler

Copyright 2006-2009, Red Hat, Inc and Others
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


class CobblerException(Exception):
    """
    This is the default Cobbler exception where all other exceptions are inheriting from.
    """

    def __init__(self, value, *args):
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

    def __str__(self):
        """
        This is the string representation of the base Cobbler Exception.
        :return: self.value as a string represented.
        """
        return repr(self.value)


class CX(CobblerException):
    """
    This is a general exception which gets thrown often inside Cobbler.
    """
    pass
