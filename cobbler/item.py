"""
An Item is a serializable thing that can appear in a Collection

Michael DeHaan <mdehaan@redhat.com>
"""

import exceptions

import serializable

class Item(serializable.Serializable):

    def set_name(self,name):
        """
        All objects have names, and with the exception of System
        they aren't picky about it.
        """
        self.name = name
        return True

    def set_kernel_options(self,options_string):
        """
	Kernel options are a comma delimited list of key value pairs,
	like 'a=b,c=d,e=f'
	"""
        self.kernel_options = options_string
        return True

    def to_datastruct(self):
        """
	Returns an easily-marshalable representation of the collection.
	i.e. dictionaries/arrays/scalars.
	"""
        raise exceptions.NotImplementedError

    def is_valid(self):
        """
	The individual set_ methods will return failure if any set is
	rejected, but the is_valid method is intended to indicate whether
	the object is well formed ... i.e. have all of the important
	items been set, are they free of conflicts, etc.
	"""
        return False


