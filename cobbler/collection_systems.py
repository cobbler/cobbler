import item_system as system
import utils
import collection

#--------------------------------------------

"""
Systems are hostnames/MACs/IP names and the associated profile
they belong to.
"""
class Systems(collection.Collection):
    
    def factory_produce(self,config):
        return system.System(config)
    
    def filename(self):
        return "/var/lib/cobbler/systems"

    def remove(self,name):
        """
        Remove element named 'name' from the collection
        """
        if self.find(name):
            del self.listing[name]
            return True
        utils.set_error("delete_nothing")
        return False

