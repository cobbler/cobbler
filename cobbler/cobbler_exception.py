"""
Custom error for fatal cobbler exceptions that come with human readable error messages.
These can be caught and printed without stack traces.

Michael DeHaan <mdehaan@redhat.com>
"""

import exceptions
import cobbler_msg

class CobblerException(exceptions.Exception):

   def __init__(self, value, args=[]):
       if type(args) == str or type(args) == int:
           args = (args)
       self.value = cobbler_msg.lookup(value) % args

   def __str__(self):
       return repr(self.value)

