"""
An Item is a serializable thing that can appear in a Collection

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
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

    def set_ksmeta(self,options_string):
        """
        A comma delimited list of key value pairs, like 'a=b,c=d,e=f'.
        The meta tags are used as input to the templating system
        to preprocess kickstart files
        """
        self.ks_meta = options_string
        tokens = self.ks_meta.split(",")
        for t in tokens:
            tokens2 = t.split("=")
            if len(tokens2) != 2:
                return False
        return True

    def load_item(self,datastruct,key,default=''):
        """
        Used in subclass from_datastruct functions to load items from
        a hash.  Intented to ease backwards compatibility of config
        files during upgrades.
        """
        if datastruct.has_key(key):
            return datastruct[key]
        return default

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


