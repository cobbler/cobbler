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

from builtins import Exception


class CobblerException(Exception):
    """
    This is the default cobbler exception where all other exceptions are inheriting from.
    """

    def __init__(self, value, *args):
        """
        Default constructor for the Exception.

        :param value: Usage of this variable not clear.
        :param args: Optional arguments which get passed to the Exception.
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
    This is a general exception which get's thrown often inside cobbler.
    """
    pass


class FileNotFoundException(CobblerException):
    """
    This means that the required file was not found during the process of opening it.
    """
    pass


class NotImplementedException(CobblerException):
    """
    On the command line interface not everything is always implemented. This is the exception which stated this.
    """
    pass
