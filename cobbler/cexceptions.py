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
import cobbler_msg

from rhpl.translate import _, N_, textdomain, utf8


class CobblerException(exceptions.Exception):

   def __init__(self, value, *args):
       """
       This is a translatable exception.  value is an entry in cobbler_msg's
       lookup table, args will be used for string substitution, if provided
       """
       self.value = cobbler_msg.lookup(value) % args

   def __str__(self):
       return repr(self.value)

