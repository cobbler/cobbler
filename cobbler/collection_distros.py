
import utils
import collection
import item_distro as distro
import collection_profiles as profiles

"""
A distro represents a network bootable matched set of kernels
and initrd files
"""
class Distros(collection.Collection):

    def factory_produce(self,config):
        return distro.Distro(config)

    def filename(self):
        return "/var/lib/cobbler/distros"

    def remove(self,name):
        """
        Remove element named 'name' from the collection
        """
        # first see if any Groups use this distro
        for k,v in self.config.profiles().listing.items():
            if v.distro == name:
               utils.set_error("orphan_files")
               return False
        if self.find(name):
            del self.listing[name]
            return True
        utils.set_error("delete_nothing")
        return False

