"""
A distro represents a network bootable matched set of kernels
and initrd files

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

import utils
import collection
import item_distro as distro
from cexceptions import *
import action_litesync
from utils import _
import os.path
import glob

class Distros(collection.Collection):

    def collection_type(self):
        return "distro"

    def factory_produce(self,config,seed_data):
        """
        Return a Distro forged from seed_data
        """
        return distro.Distro(config).from_datastruct(seed_data)

    def remove(self,name,with_delete=True,with_sync=True,with_triggers=True,recursive=False):
        """
        Remove element named 'name' from the collection
        """
        name = name.lower()

        # first see if any Groups use this distro
        if not recursive:
            for v in self.config.profiles():
                if v.distro.lower() == name:
                    raise CX(_("removal would orphan profile: %s") % v.name)

        obj = self.find(name=name)

        if obj is not None:
            kernel = obj.kernel
            if recursive:
                kids = obj.get_children()
                for k in kids:
                    self.config.api.remove_profile(k, recursive=True)

            if with_delete:
                if with_triggers: 
                    self._run_triggers(obj, "/var/lib/cobbler/triggers/delete/distro/pre/*")
                if with_sync:
                    lite_sync = action_litesync.BootLiteSync(self.config)
                    lite_sync.remove_single_profile(name)
            del self.listing[name]

            self.config.serialize_delete(self, obj)

            if with_delete:
                self.log_func("deleted distro %s" % name)
                if with_triggers: 
                    self._run_triggers(obj, "/var/lib/cobbler/triggers/delete/distro/post/*")

            # look through all mirrored directories and find if any directory is holding
            # this particular distribution's kernel and initrd
            possible_storage = glob.glob("/var/www/cobbler/ks_mirror/*")
            path = None
            for storage in possible_storage:
                if os.path.dirname(obj.kernel).find(storage) != -1:
                    path = storage
                    continue

            # if we found a mirrored path above, we can delete the mirrored storage /if/
            # no other object is using the same mirrored storage.
            if with_delete and path is not None and os.path.exists(path) and kernel.find("/var/www/cobbler") != -1:
               # this distro was originally imported so we know we can clean up the associated
               # storage as long as nothing else is also using this storage.
               found = False
               distros = self.api.distros()
               for d in distros:
                   if d.kernel.find(path) != -1:
                       found = True
               if not found:
                   utils.rmtree(path)

            return True

        raise CX(_("cannot delete object that does not exist: %s") % name)

