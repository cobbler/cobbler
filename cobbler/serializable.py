"""
Serializable interface, for documentation purposes

Michael DeHaan <mdehaan@redhat.com>
"""

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

