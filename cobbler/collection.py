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

from rhpl.translate import _, N_, textdomain, utf8

class Collection(serializable.Serializable):

    def __init__(self,config):
        """
	Constructor.
	"""
        self.config = config
        self.clear()

    def factory_produce(self,config,seed_data):
        """
        Must override in subclass.  Factory_produce returns an Item object
        from datastructure seed_data
        """
        raise exceptions.NotImplementedError

    def filename(self):
        """
        Must override in subclass.  See Serializable
        """
        raise exceptions.NotImplementedError

    def clear(self):
        """
        Forget about objects in the collection.
        """
        self.listing = {}

    def find(self,name):
        """
        Return anything named 'name' in the collection, else return None if
        no objects can be found.
        """
        n1 = name.lower()
        for key in self.listing.keys():
            if key.lower() == n1:
                return self.listing[name]
        return None

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

    def add(self,ref,with_copy=False):
        """
        Add an object to the collection, if it's valid.  Returns True
        if the object was added to the collection.  Returns False if the
        object specified by ref deems itself invalid (and therefore
        won't be added to the collection).
        """
        if ref is None or not ref.is_valid():
            raise CX(_("invalid parameter"))
        self.listing[ref.name] = ref

        # perform filesystem operations
        if with_copy:
            lite_sync = action_litesync.BootLiteSync(self.config)
            if isinstance(ref, item_system.System):
                lite_sync.add_single_system(ref.name)
            elif isinstance(ref, item_profile.Profile):
                lite_sync.add_single_profile(ref.name) 
            elif isinstance(ref, item_distro.Distro):
                lite_sync.add_single_distro(ref.name)
            else:
                print _("Internal error. Object type not recognized: %s") % type(ref)
        
            # save the tree, so if neccessary, scripts can examine it.
            self.config.api.serialize()
    
            self._run_triggers(ref,"/var/lib/cobbler/triggers/add/%s/*" % self.collection_type())

        return True

    def _run_triggers(self,ref,globber):
        triggers = glob.glob(globber)
        for file in triggers:
            sub_process.call("%s %s" % (file,ref.name), shell=True)

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


