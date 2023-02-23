"""
Cobbler module that at runtime holds all packages in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2010, Kelsey Hightower <kelsey.hightower@gmail.com>

from cobbler.cobbler_collections import collection
from cobbler.items import package as package
from cobbler import utils
from cobbler.cexceptions import CX


class Packages(collection.Collection):
    """
    A package provides a container for package resources.
    """

    @staticmethod
    def collection_type() -> str:
        return "package"

    @staticmethod
    def collection_types() -> str:
        return "packages"

    def factory_produce(self, api, item_dict):
        """
        Return a Package forged from item_dict
        """
        new_package = package.Package(api)
        new_package.from_dict(item_dict)
        return new_package

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
                    self.api, obj, "/var/lib/cobbler/triggers/delete/package/pre/*", []
                )

        with self.lock:
            del self.listing[name]
        self.collection_mgr.serialize_delete(self, obj)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/package/post/*", []
                )
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/change/*", []
                )
