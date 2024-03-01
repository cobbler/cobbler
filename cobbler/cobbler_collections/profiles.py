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

from cobbler.cobbler_collections import collection
from cobbler.items import profile as profile
from cobbler import utils
from cobbler.cexceptions import CX


class Profiles(collection.Collection):
    """
    A profile represents a distro paired with an automatic OS installation template file.
    """

    @staticmethod
    def collection_type() -> str:
        return "profile"

    @staticmethod
    def collection_types() -> str:
        return "profiles"

    def factory_produce(self, api, item_dict):
        """
        Return a Distro forged from item_dict
        """
        new_profile = profile.Profile(api, **item_dict)
        new_profile.from_dict(item_dict)
        return new_profile

    def remove(self, name: str, with_delete: bool = True, with_sync: bool = True, with_triggers: bool = True,
               recursive: bool = False):
        """
        Remove element named 'name' from the collection

        :raises CX: In case the name of the object was not given or any other descendant would be orphaned.
        """
        name = name.lower()
        if not recursive:
            for v in self.api.systems():
                if v.profile is not None and v.profile.lower() == name:
                    raise CX("removal would orphan system: %s" % v.name)

        obj = self.find(name=name)
        if obj is None:
            raise CX("cannot delete an object that does not exist: %s" % name)

        if recursive:
            kids = obj.get_children()
            for k in kids:
                if self.api.find_profile(name=k) is not None:
                    self.api.remove_profile(k, recursive=recursive, delete=with_delete, with_triggers=with_triggers)
                else:
                    self.api.remove_system(k, recursive=recursive, delete=with_delete, with_triggers=with_triggers)

        if with_delete:
            if with_triggers:
                utils.run_triggers(self.api, obj, "/var/lib/cobbler/triggers/delete/profile/pre/*", [])

        if obj.parent is not None and obj.name in obj.parent.children:
            obj.parent.children.remove(obj.name)
            # ToDo: Only serialize parent object, use:
            #       Use self.collection_mgr.serialize_one_item(obj.parent)
            self.api.serialize()

        self.lock.acquire()
        try:
            del self.listing[name]
        finally:
            self.lock.release()
        self.collection_mgr.serialize_delete(self, obj)
        if with_delete:
            if with_triggers:
                utils.run_triggers(self.api, obj, "/var/lib/cobbler/triggers/delete/profile/post/*", [])
                utils.run_triggers(self.api, obj, "/var/lib/cobbler/triggers/change/*", [])
            if with_sync:
                lite_sync = self.api.get_sync()
                lite_sync.remove_single_profile(name)
