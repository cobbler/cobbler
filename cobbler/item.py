"""
An Item is a serializable thing that can appear in a Collection

Michael DeHaan <mdehaan@redhat.com>
"""

import serializable

class Item(serializable.Serializable):

    """
    constructor must be of format:
    def __init__(self,seed_data)
    where seed_data is a hash of argument_name/value pairs
    see profile.py for example
    """

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


