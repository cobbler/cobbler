"""
Custom exceptions for Cobbler

Copyright 2006-2009, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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

import exceptions

TEST_MODE = False

class CobblerException(exceptions.Exception):

   def __init__(self, value, *args):
       self.value = value % args
       # this is a hack to work around some odd exception handling
       # in older pythons
       self.from_cobbler = 1

   def __str__(self):
       return repr(self.value)

class CX(CobblerException):
   pass

