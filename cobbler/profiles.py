import profile
import runtime

#--------------------------------------------

"""
A profile represents a distro paired with a kickstart file.
For instance, FC5 with a kickstart file specifying OpenOffice
might represent a 'desktop' profile.  For Xen, there are many
additional options, with client-side defaults (not kept here).
"""
class Profiles(Collection):
    _item_factory = profile.Profile

    def remove(self,name):
        """
        Remove element named 'name' from the collection
        """
        for k,v in self.api.get_systems().listing.items():
           if v.profile == name:
               runtime.set_error("orphan_system")
               return False
        if self.find(name):
            del self.listing[name]
            return True
        runtime.set_error("delete_nothing")
        return False

