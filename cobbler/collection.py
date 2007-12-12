"""
Base class for any serializable list of things...

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import exceptions
from cexceptions import *
import serializable
import utils
import glob
import sub_process

import action_litesync
import item_system
import item_profile
import item_distro
import item_repo

from rhpl.translate import _, N_, textdomain, utf8

class Collection(serializable.Serializable):

    def __init__(self,config):
        """
        Constructor.
        """
        self.config = config
        self.clear()
        self.log_func = self.config.api.log
        self.lite_sync = None

    def factory_produce(self,config,seed_data):
        """
        Must override in subclass.  Factory_produce returns an Item object
        from datastructure seed_data
        """
        raise exceptions.NotImplementedError

    def clear(self):
        """
        Forget about objects in the collection.
        """
        self.listing = {}

    def find(self, name=None, return_list=False, **kargs):
        """
        Return first object in the collection that maches all item='value'
        pairs passed, else return None if no objects can be found.
        When return_list is set, can also return a list.  Empty list
        would be returned instead of None in that case.
        """

        matches = []

        # support the old style innovation without kwargs
        if name is not None:
            kargs["name"] = name

        # no arguments is an error, so we don't return a false match
        if len(kargs) == 0:
            raise CX(_("calling find with no arguments"))

        # performance: if the only key is name we can skip the whole loop
        if len(kargs) == 1 and kargs.has_key("name") and not return_list:
            return self.listing.get(kargs["name"].lower(), None)

        for (name, obj) in self.listing.iteritems():
            if obj.find_match(kargs):
                matches.append(obj)

        if not return_list:
            if len(matches) == 0:
                return None
            return matches[0]
        else:
            return matches

    def to_datastruct(self):
        """
        Serialize the collection
        """
        datastruct = [x.to_datastruct() for x in self.listing.values()]
        return datastruct

    def from_datastruct(self,datastruct):
        if datastruct is None:
            return
        for seed_data in datastruct:
            item = self.factory_produce(self.config,seed_data)
            self.add(item)

    def add(self,ref,save=False,with_copy=False,with_triggers=True,with_sync=True,quick_pxe_update=False):
        """
        Add an object to the collection, if it's valid.  Returns True
        if the object was added to the collection.  Returns False if the
        object specified by ref deems itself invalid (and therefore
        won't be added to the collection).

        with_copy is a bit of a misnomer, but lots of internal add operations
        can run with "with_copy" as False. True means a real final commit, as if
        entered from the command line (or basically, by a user).  
 
        With with_copy as False, the particular add call might just be being run 
        during deserialization, in which case extra semantics around the add don't really apply.
        So, in that case, don't run any triggers and don't deal with any actual files.

        """
        if self.lite_sync is None:
            self.lite_sync = action_litesync.BootLiteSync(self.config)

        # migration path for old API parameter that I've renamed.
        if with_copy and not save:
            save = with_copy

        if not save:
            # for people that aren't quite aware of the API
            # if not saving the object, you can't run these features
            with_triggers = False
            with_sync = False

        if ref is None or not ref.is_valid():
            raise CX(_("insufficient or invalid arguments supplied"))

        if ref.COLLECTION_TYPE != self.collection_type():
            raise CX(_("API error: storing wrong data type in collection"))

        if not save:
            # don't need to run triggers, so add it already ...
            self.listing[ref.name.lower()] = ref


        # perform filesystem operations
        if save:
            self.log_func("saving %s %s" % (self.collection_type(), ref.name))
            # failure of a pre trigger will prevent the object from being added
            if with_triggers:
                self._run_triggers(ref,"/var/lib/cobbler/triggers/add/%s/pre/*" % self.collection_type())
            self.listing[ref.name.lower()] = ref

            # save just this item if possible, if not, save
            # the whole collection
            self.config.serialize_item(self, ref)

            if with_sync:
                if isinstance(ref, item_system.System):
                    self.lite_sync.add_single_system(ref.name)
                elif isinstance(ref, item_profile.Profile):
                    self.lite_sync.add_single_profile(ref.name) 
                elif isinstance(ref, item_distro.Distro):
                    self.lite_sync.add_single_distro(ref.name)
                elif isinstance(ref, item_repo.Repo):
                    pass
                else:
                    print _("Internal error. Object type not recognized: %s") % type(ref)
            if not with_sync and quick_pxe_update:
                if isinstance(ref, item_system.System):
                    self.lite_sync.update_system_netboot_status(ref.name)

            # save the tree, so if neccessary, scripts can examine it.
            if with_triggers:
                self._run_triggers(ref,"/var/lib/cobbler/triggers/add/%s/post/*" % self.collection_type())
        
        # update children cache in parent object
        parent = ref.get_parent()
        if parent != None:
            parent.children[ref.name] = ref
        return True

    def _run_triggers(self,ref,globber):
        return utils.run_triggers(ref,globber)

    def printable(self):
        """
        Creates a printable representation of the collection suitable
        for reading by humans or parsing from scripts.  Actually scripts
        would be better off reading the YAML in the config files directly.
        """
        values = self.listing.values()[:] # copy the values
        values.sort() # sort the copy (2.3 fix)
        results = []
        for i,v in enumerate(values):
           results.append(v.printable())
        if len(values) > 0:
           return "\n\n".join(results)
        else:
           return _("No objects found")

    def __iter__(self):
        """
	Iterator for the collection.  Allows list comprehensions, etc
	"""
        for a in self.listing.values():
	    yield a

    def __len__(self):
        """
	Returns size of the collection
	"""
        return len(self.listing.values())

    def collection_type(self):
        """
        Returns the string key for the name of the collection (for use in messages for humans)
        """
        return exceptions.NotImplementedError


