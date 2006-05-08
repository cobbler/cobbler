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
               utils.set_error("orphan_system")
               return False
        if self.find(name):
            del self.listing[name]
            return True
        utils.set_error("delete_nothing")
        return False

