"""
A profile represents a distro paired with a kickstart file.
For instance, FC5 with a kickstart file specifying OpenOffice
might represent a 'desktop' profile.  For Virt, there are many
additional options, with client-side defaults (not kept here).

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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

import item_profile as profile
import utils
import collection
from cexceptions import *
import action_litesync
from utils import _

#--------------------------------------------

class Profiles(collection.Collection):

    def collection_type(self):
        return "profile"

    def factory_produce(self,config,seed_data):
        return profile.Profile(config).from_datastruct(seed_data)

    def remove(self,name,with_delete=True,with_sync=True,with_triggers=True,recursive=False):
        """
        Remove element named 'name' from the collection
        """

        name = name.lower()

        if not recursive:
            for v in self.config.systems():
                if v.profile is not None and v.profile.lower() == name:
                    raise CX(_("removal would orphan system: %s") % v.name)

        obj = self.find(name=name)
        if obj is not None:
            if recursive:
                kids = obj.get_children()
                for k in kids:
                    if k.COLLECTION_TYPE == "profile":
                        self.config.api.remove_profile(k, recursive=recursive, delete=with_delete, with_triggers=with_triggers)
                    else:
                        self.config.api.remove_system(k, recursive=recursive, delete=with_delete, with_triggers=with_triggers)
 
            if with_delete:
                if with_triggers: 
                    self._run_triggers(self.config.api, obj, "/var/lib/cobbler/triggers/delete/profile/pre/*")
                if with_sync:
                    lite_sync = action_litesync.BootLiteSync(self.config)
                    lite_sync.remove_single_profile(name)
            del self.listing[name]
            self.config.serialize_delete(self, obj)
            if with_delete:
                self.log_func("deleted profile %s" % name)
                if with_triggers: 
                    self._run_triggers(self.config.api, obj, "/var/lib/cobbler/triggers/delete/profile/post/*")
                    self._run_triggers(self.config.api, obj, "/var/lib/cobbler/triggers/change/*")

            return True

        raise CX(_("cannot delete an object that does not exist: %s") % name)
