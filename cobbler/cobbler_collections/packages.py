"""
Cobbler module that at runtime holds all packages in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2010, Kelsey Hightower <kelsey.hightower@gmail.com>

from typing import TYPE_CHECKING, Any, Dict

from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import collection
from cobbler.items import package

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Packages(collection.Collection[package.Package]):
    """
    A package provides a container for package resources.
    """

    @staticmethod
    def collection_type() -> str:
        return "package"

    @staticmethod
    def collection_types() -> str:
        return "packages"

    def factory_produce(
        self, api: "CobblerAPI", seed_data: Dict[str, Any]
    ) -> package.Package:
        """
        Return a Package forged from seed_data.

        :param api: Parameter is skipped.
        :param seed_data: Data to seed the object with.
        :returns: The created object.
        """
        return package.Package(self.api, **seed_data)

    def remove(
        self,
        name: str,
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

        if isinstance(obj, list):
            # Will never happen, but we want to make mypy happy.
            raise CX("Ambiguous match detected!")

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
