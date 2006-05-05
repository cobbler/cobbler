import profile
import utils
import collection

#--------------------------------------------

"""
A profile represents a distro paired with a kickstart file.
For instance, FC5 with a kickstart file specifying OpenOffice
might represent a 'desktop' profile.  For Xen, there are many
additional options, with client-side defaults (not kept here).
"""
class Profiles(collection.Collection):
    
    def class_container(self):
        return profile.Profile
    
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

