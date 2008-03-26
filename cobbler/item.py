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

    def __init__(self,config,is_subobject=False):
        """
        Constructor.  Requires a back reference to the Config management object.
        
        NOTE: is_subobject is used for objects that allow inheritance in their trees.  This
        inheritance refers to conceptual inheritance, not Python inheritance.  Objects created
        with is_subobject need to call their set_parent() method immediately after creation
        and pass in a value of an object of the same type.  Currently this is only supported
        for profiles.  Subobjects blend their data with their parent objects and only require
        a valid parent name and a name for themselves, so other required options can be
        gathered from items further up the cobbler tree.

        Old cobbler:             New cobbler:
        distro                   distro
          profile                   profile
            system                     profile  <-- created with is_subobject=True
                                         system   <-- created as normal

        For consistancy, there is some code supporting this in all object types, though it is only usable
        (and only should be used) for profiles at this time.  Objects that are children of
        objects of the same type (i.e. subprofiles) need to pass this in as True.  Otherwise, just
        use False for is_subobject and the parent object will (therefore) have a different type.

        """
        self.config = config
        self.settings = self.config._settings
        self.clear(is_subobject)      # reset behavior differs for inheritance cases
        self.parent = ''              # all objects by default are not subobjects
        self.children = {}            # caching for performance reasons, not serialized
        self.owners = []
        self.log_func = self.config.api.log        

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
           parent = parent.get_parent()
        return None

    def set_name(self,name):
        """
        All objects have names, and with the exception of System
        they aren't picky about it.
        """
        if self.name not in ["",None] and self.parent not in ["",None] and self.name == self.parent:
            raise CX(_("self parentage is weird"))
        self.name = name
        return True

    def set_owners(self,data):
        """
        The owners field is a comment unless using an authz module that pays attention to it,
        like authz_ownership, which ships with Cobbler but is off by default.  Consult the Wiki
        docs for more info on CustomizableAuthorization.
        """
        owners = utils.input_string_or_list(data)
        self.owners = owners
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

    def find_match(self,kwargs):
        # used by find() method in collection.py
        data = self.to_datastruct()
        for (key, value) in kwargs.iteritems():
            if not self.find_match_single_key(data,key,value):
                return False
        return True
 

    def find_match_single_key(self,data,key,value):
        # special case for systems
        key_found_already = False
        if data.has_key("interfaces"):
            if key in [ "mac_address", "ip_address", "subnet", "gateway", "virt_bridge", "dhcp_tag", "hostname" ]:
                key_found_already = True
                for (name, interface) in data["interfaces"].iteritems(): 
                    if interface[key].lower() == value.lower():
                        return True

        if not data.has_key(key):
            if not key_found_already:
                raise CX(_("searching for field that does not exist: %s" % key))
            else:
                return False
        if value.lower() == data[key].lower():
            return True
        else:
            return False

