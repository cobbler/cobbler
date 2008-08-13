"""
Serializable interface, for documentation purposes.
Collections and Settings both support this interface.

Copyright 2006-2008, Red Hat, Inc
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

from utils import _
import exceptions

class Serializable:

   def filename(self):
       """
       Return the full path to the config file this object uses.
       """
       return None

   def from_datastruct(self,datastruct):
       """
       Return an object constructed with data from datastruct
       """
       raise exceptions.NotImplementedError

   def to_datastruct(self):
       """
       Return hash/array/scalar reprentation of self.
       This function must be the inverse of from_datastruct.
       """
       raise exceptions.NotImplementedError

