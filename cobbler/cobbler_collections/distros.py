"""
Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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

import os.path
import glob

from cobbler.actions import litesync
from cobbler.cobbler_collections import collection
from cobbler.items import distro as distro
from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.utils import _


class Distros(collection.Collection):
    """
    A distro represents a network bootable matched set of kernels and initrd files.
    """

    @staticmethod
    def collection_type() -> str:
        return "distro"

    @staticmethod
    def collection_types() -> str:
        return "distros"

    def factory_produce(self, collection_mgr, item_dict):
        """
        Return a Distro forged from item_dict
        """
        new_distro = distro.Distro(collection_mgr)
        new_distro.from_dict(item_dict)
        return new_distro

    def remove(self, name, with_delete=True, with_sync=True, with_triggers=True, recursive=False, logger=None):
        """
        Remove element named 'name' from the collection
        """
        name = name.lower()

        # first see if any Groups use this distro
        if not recursive:
            for v in self.collection_mgr.profiles():
                if v.distro and v.distro.lower() == name:
                    raise CX(_("removal would orphan profile: %s") % v.name)

        obj = self.find(name=name)

        if obj is not None:
            kernel = obj.kernel
            if recursive:
                kids = obj.get_children()
                for k in kids:
                    self.collection_mgr.api.remove_profile(k.name, recursive=recursive, delete=with_delete, with_triggers=with_triggers, logger=logger)

            if with_delete:
                if with_triggers:
                    utils.run_triggers(self.collection_mgr.api, obj, "/var/lib/cobbler/triggers/delete/distro/pre/*", [], logger)
                if with_sync:
                    lite_sync = litesync.CobblerLiteSync(self.collection_mgr, logger=logger)
                    lite_sync.remove_single_distro(name)
            self.lock.acquire()
            try:
                del self.listing[name]
            finally:
                self.lock.release()

            self.collection_mgr.serialize_delete(self, obj)

            if with_delete:
                if with_triggers:
                    utils.run_triggers(self.collection_mgr.api, obj, "/var/lib/cobbler/triggers/delete/distro/post/*", [], logger)
                    utils.run_triggers(self.collection_mgr.api, obj, "/var/lib/cobbler/triggers/change/*", [], logger)

            # look through all mirrored directories and find if any directory is holding
            # this particular distribution's kernel and initrd
            settings = self.collection_mgr.settings()
            possible_storage = glob.glob(settings.webdir + "/distro_mirror/*")
            path = None
            for storage in possible_storage:
                if os.path.dirname(obj.kernel).find(storage) != -1:
                    path = storage
                    continue

            # if we found a mirrored path above, we can delete the mirrored storage /if/
            # no other object is using the same mirrored storage.
            if with_delete and path is not None and os.path.exists(path) and kernel.find(settings.webdir) != -1:
                # this distro was originally imported so we know we can clean up the associated
                # storage as long as nothing else is also using this storage.
                found = False
                distros = self.api.distros()
                for d in distros:
                    if d.kernel.find(path) != -1:
                        found = True
                if not found:
                    utils.rmtree(path)


# EOF
