"""
Systems are hostnames/MACs/IP names and the associated profile
they belong to.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import item_system as system
import utils
import collection
from cexceptions import *
import action_litesync
from rhpl.translate import _, N_, textdomain, utf8

#--------------------------------------------

class Systems(collection.Collection):

    def collection_type(self):
        return "system"

    def factory_produce(self,config,seed_data):
        """
        Return a system forged from seed_data
        """
        return system.System(config).from_datastruct(seed_data)

    def remove(self,name,with_delete=True):
        """
        Remove element named 'name' from the collection
        """
        name = name.lower()
        obj = self.find(name=name)
        
        if obj is not None:

            if with_delete:
                self._run_triggers(obj, "/var/lib/cobbler/triggers/delete/system/pre/*")
                lite_sync = action_litesync.BootLiteSync(self.config)
                lite_sync.remove_single_system(name)
            self.config.serialize_delete(self, obj)
            if with_delete:
                self._run_triggers(obj, "/var/lib/cobbler/triggers/delete/system/post/*")
            del self.listing[name]

            return True
        raise CX(_("cannot delete an object that does not exist"))
    
     
