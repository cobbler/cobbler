import distro
import runtime
import profiles

"""
A distro represents a network bootable matched set of kernels
and initrd files
"""
class Distros(Collection):
    _item_factory = distro.Distro
    _filename = "/var/lib/cobbler/distros"

    def remove(self,name):
        """
        Remove element named 'name' from the collection
        """
        # first see if any Groups use this distro
        for k,v in profile.profiles().listing.items():
            if v.distro == name:
               runtime.set_error("orphan_files")
               return False
        if self.find(name):
            del self.listing[name]
            return True
        runtime.set_error("delete_nothing")
        return False

