"""
Custom exceptions for Cobbler

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import exceptions

class CobblerException(exceptions.Exception):

   def __init__(self, value, *args):
       self.value = value % args

   def __str__(self):
       return repr(self.value)

class CX(CobblerException):
   pass

