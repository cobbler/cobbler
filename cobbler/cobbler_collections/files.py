"""
Copyright 2010, Kelsey Hightower
Kelsey Hightower <kelsey.hightower@gmail.com>

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
from cobbler.items import file as file
from cobbler import utils
from cobbler.cexceptions import CX


class Files(collection.Collection):
    """
    Files provide a container for file resources.
    """

    @staticmethod
    def collection_type() -> str:
        return "file"

    @staticmethod
    def collection_types() -> str:
        return "files"

    def factory_produce(self, api, item_dict):
        """
        Return a File forged from item_dict
        """
        new_file = file.File(api, **item_dict)
        new_file.from_dict(item_dict)
        return new_file

    def remove(self, name, with_delete: bool = True, with_sync: bool = True, with_triggers: bool = True,
               recursive: bool = False):
        """
        Remove element named 'name' from the collection

        :raises CX: In case a non existent object should be deleted.
        """
        name = name.lower()
        obj = self.find(name=name)

        if obj is None:
            raise CX("cannot delete an object that does not exist: %s" % name)

        if with_delete:
            if with_triggers:
                utils.run_triggers(self.api, obj, "/var/lib/cobbler/triggers/delete/file/pre/*", [])

        self.lock.acquire()
        try:
            del self.listing[name]
        finally:
            self.lock.release()
        self.collection_mgr.serialize_delete(self, obj)

        if with_delete:
            if with_triggers:
                utils.run_triggers(self.api, obj, "/var/lib/cobbler/triggers/delete/file/post/*", [])
                utils.run_triggers(self.api, obj, "/var/lib/cobbler/triggers/change/*", [])

        return
