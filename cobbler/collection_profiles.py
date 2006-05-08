"""
A profile represents a distro paired with a kickstart file.
For instance, FC5 with a kickstart file specifying OpenOffice
might represent a 'desktop' profile.  For Xen, there are many
additional options, with client-side defaults (not kept here).

Michael DeHaan <mdehaan@redhat.com>
"""

import item_profile as profile
import utils
import collection
from cobbler_exception import CobblerException

#--------------------------------------------

class Profiles(collection.Collection):

    def factory_produce(self,config,seed_data):
        return profile.Profile(config).from_datastruct(seed_data)

    def filename(self):
        return "/var/lib/cobbler/profiles"

    def remove(self,name):
        """
        Remove element named 'name' from the collection
        """
        for k,v in self.config.systems().listing.items():
           if v.profile == name:
               raise CobblerException("orphan_system")
        if self.find(name):
            del self.listing[name]
            return True
        raise CobblerException("delete_nothing")

