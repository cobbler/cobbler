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
import utils
from cexceptions import *
from rhpl.translate import _, N_, textdomain, utf8

class Item(serializable.Serializable):

    TYPE_NAME = "generic"

    def __init__(self,config):
        """
        Constructor.  Requires a back reference to the Config management object.
        """
        self.config = config
        self.settings = self.config._settings
        self.clear()
        self.children = {}             # caching for performance reasons, not serialized
        self.conceptual_parent = None  # " "

    def clear(self):
        raise exceptions.NotImplementedError

    def get_children(self,sorted=True):
        """
        Get direct children of this object.
        """
        keys = self.children.keys()
        if sorted:
            keys.sort()
        results = []
        for k in keys:
            results.append(self.children[k])
        return results

    def get_descendants(self):
        """
        Get objects that depend on this object, i.e. those that
        would be affected by a cascading delete, etc.
        """
        results = []
        kids = self.get_children(sorted=False)
        results.extend(kids)
        for kid in kids:
            grandkids = kid.get_descendants()
            results.extend(grandkids)
        return results

    def get_parent(self):
        """
        For objects with a tree relationship, what's the parent object?
        """
        return None

    def get_conceptual_parent(self):
        """
        The parent may just be a superclass for something like a
        subprofile.  Get the first parent of a different type.
        """

        if self.conceptual_parent is not None:
            return self.conceptual_parent

        # FIXME: this is a workaround to get the type of an instance var
        # what's a more clean way to do this that's python 2.3 friendly?
        # this returns something like:  cobbler.item_system.System
        mtype = str(self).split(" ")[0][1:]
        parent = self.get_parent()
        while parent is not None:
           ptype = str(parent).split(" ")[0][1:]
           if mtype != ptype:
              self.conceptual_parent = parent
              return parent

        return None

    def set_name(self,name):
        """
        All objects have names, and with the exception of System
        they aren't picky about it.
        """
        self.name = name
        return True

    def set_kernel_options(self,options):
        """
	Kernel options are a space delimited list,
	like 'a=b c=d e=f g h i=j' or a hash.
	"""
        (success, value) = utils.input_string_or_hash(options,None)
        if not success:
            raise CX(_("invalid kernel options"))
        else:
            self.kernel_options = value
            return True

    def set_ksmeta(self,options):
        """
        A comma delimited list of key value pairs, like 'a=b,c=d,e=f' or a hash.
        The meta tags are used as input to the templating system
        to preprocess kickstart files
        """
        (success, value) = utils.input_string_or_hash(options,None)
        if not success:
            return False
        else:
            self.ks_meta = value
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


