"""
A distro represents a network bootable matched set of kernels
and initrd files

Michael DeHaan <mdehaan@redhat.com
"""

import utils
import collection
import item_distro as distro
import cexceptions

class Distros(collection.Collection):

    def factory_produce(self,config,seed_data):
        """
        Return a Distro forged from seed_data
        """
        return distro.Distro(config).from_datastruct(seed_data)

    def filename(self):
        """
        Config file for distro serialization
        """
        return "/var/lib/cobbler/distros"

    def remove(self,name):
        """
        Remove element named 'name' from the collection
        """
        # first see if any Groups use this distro
        for v in self.config.profiles():
            if v.distro == name:
               raise cexceptions.CobblerException("orphan_profile",v.name)
        if self.find(name):
            del self.listing[name]
            return True
        raise cexceptions.CobblerException("delete_nothing")

