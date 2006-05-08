"""
Custom exceptions for Cobbler

Michael DeHaan <mdehaan@redhat.com>
"""

import exceptions
import cobbler_msg

class CobblerException(exceptions.Exception):

   def __init__(self, value, args=[]):
       """
       This is a translatable exception.  value is an entry in cobbler_msg's
       lookup table, args will be used for string substitution, if provided
       """
       if type(args) == str or type(args) == int:
           args = (args)
       self.value = cobbler_msg.lookup(value) % args

   def __str__(self):
       return repr(self.value)

