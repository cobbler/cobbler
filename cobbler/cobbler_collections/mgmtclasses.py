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
from cobbler.items import mgmtclass as mgmtclass
from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.utils import _


class Mgmtclasses(collection.Collection):
    """
    A mgmtclass provides a container for management resources.
    """

    @staticmethod
    def collection_type() -> str:
        return "mgmtclass"

    @staticmethod
    def collection_types() -> str:
        return "mgmtclasses"

    def factory_produce(self, config, item_dict):
        """
        Return a mgmtclass forged from item_dict
        """
        new_mgmtclass = mgmtclass.Mgmtclass(config)
        new_mgmtclass.from_dict(item_dict)
        return new_mgmtclass

    def remove(self, name, with_delete=True, with_sync=True, with_triggers=True, recursive=False, logger=None):
        """
        Remove element named 'name' from the collection
        """

        name = name.lower()
        obj = self.find(name=name)
        if obj is not None:
            if with_delete:
                if with_triggers:
                    utils.run_triggers(self.collection_mgr.api, obj, "/var/lib/cobbler/triggers/delete/mgmtclass/pre/*", [], logger)

            self.lock.acquire()
            try:
                del self.listing[name]
            finally:
                self.lock.release()
            self.collection_mgr.serialize_delete(self, obj)

            if with_delete:
                if with_triggers:
                    utils.run_triggers(self.collection_mgr.api, obj, "/var/lib/cobbler/triggers/delete/mgmtclass/post/*", [], logger)
                    utils.run_triggers(self.collection_mgr.api, obj, "/var/lib/cobbler/triggers/change/*", [], logger)

            return

        raise CX(_("cannot delete an object that does not exist: %s") % name)

# EOF
