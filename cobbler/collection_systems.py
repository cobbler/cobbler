"""
Systems are hostnames/MACs/IP names and the associated profile
they belong to.

Michael DeHaan <mdehaan@redhat.com>
"""

import item_system as system
import utils
import collection
import cexceptions

#--------------------------------------------

class Systems(collection.Collection):

    def factory_produce(self,config,seed_data):
        """
        Return a system forged from seed_data
        """
        return system.System(config).from_datastruct(seed_data)

    def filename(self):
        """
        Return a filename for System serialization
        """
        return "/var/lib/cobbler/systems"

    def remove(self,name):
        """
        Remove element named 'name' from the collection
        """
        if self.find(name):
            del self.listing[name]
            return True
        raise cexceptions.CobblerException("delete_nothing")

