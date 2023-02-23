"""
Cobbler module that at runtime holds all mgmtclasses in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2010, Kelsey Hightower <kelsey.hightower@gmail.com>

from cobbler.cobbler_collections import collection
from cobbler.items import mgmtclass as mgmtclass
from cobbler import utils
from cobbler.cexceptions import CX


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

    def factory_produce(self, api, item_dict):
        """
        Return a mgmtclass forged from item_dict

        :param api: TODO
        :param item_dict: TODO
        :returns: TODO
        """
        new_mgmtclass = mgmtclass.Mgmtclass(api)
        new_mgmtclass.from_dict(item_dict)
        return new_mgmtclass

    def remove(
        self,
        name,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
    ):
        """
        Remove element named 'name' from the collection

        :raises CX: In case the object does not exist.
        """
        obj = self.find(name=name)
        if obj is None:
            raise CX(f"cannot delete an object that does not exist: {name}")

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api,
                    obj,
                    "/var/lib/cobbler/triggers/delete/mgmtclass/pre/*",
                    [],
                )

        with self.lock:
            del self.listing[name]
        self.collection_mgr.serialize_delete(self, obj)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api,
                    obj,
                    "/var/lib/cobbler/triggers/delete/mgmtclass/post/*",
                    [],
                )
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/change/*", []
                )
