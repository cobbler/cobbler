import system
import runtime

#--------------------------------------------

"""
Systems are hostnames/MACs/IP names and the associated profile
they belong to.
"""
class Systems(Collection):
    _item_factory = system.System

    def remove(self,name):
        """
        Remove element named 'name' from the collection
        """
        if self.find(name):
            del self.listing[name]
            return True
        runtime.set_error("delete_nothing")
        return False

