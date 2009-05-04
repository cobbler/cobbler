"""
Networks in cobbler allow network-level attributes to be defined and
to be inherited by systems/interfaces which belong to the network.
Also allows for intelligent allocation of addresses within networks.

Copyright 2009, Red Hat, Inc
John Eckersberg <jeckersb@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import item_network as network
import utils
import collection
from cexceptions import *
from utils import _
import os.path

TESTMODE = False

#--------------------------------------------

class Networks(collection.Collection):

    def collection_type(self):
        return "network"

    def factory_produce(self,config,seed_data):
        """
        Return a repo forged from seed_data
        """
        return network.Network(config).from_datastruct(seed_data)

    def remove(self,name,with_delete=True,with_sync=True,with_triggers=True,recursive=False):
        """
        Remove element named 'name' from the collection
        """

        # NOTE: with_delete isn't currently meaningful for networks
        # but is left in for consistancy in the API.  Unused.
        name = name.lower()
        obj = self.find(name=name)
        if obj is not None:
            if with_delete:
                if with_triggers:
                    self._run_triggers(self.config.api, obj, "/var/lib/cobbler/triggers/delete/network/pre/*")

            del self.listing[name]
            self.config.serialize_delete(self, obj)

            if with_delete:
                self.log_func("deleted network %s" % name)
                if with_triggers:
                    self._run_triggers(self.config.api, obj, "/var/lib/cobbler/triggers/delete/network/post/*")

            if with_delete and not self.api.is_cobblerd:
                self.api._internal_cache_update("network", name, remove=True)

            return True
        raise CX(_("cannot delete an object that does not exist: %s") % name)

