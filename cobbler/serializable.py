"""
Serializable interface, for documentation purposes.
Collections and Settings both support this interface.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
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

