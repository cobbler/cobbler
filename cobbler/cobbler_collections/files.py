"""
Cobbler module that at runtime holds all files in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2010, Kelsey Hightower <kelsey.hightower@gmail.com>

from typing import TYPE_CHECKING, Any, Dict

from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import collection
from cobbler.items import file

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Files(collection.Collection[file.File]):
    """
    Files provide a container for file resources.
    """

    @staticmethod
    def collection_type() -> str:
        return "file"

    @staticmethod
    def collection_types() -> str:
        return "files"

    def factory_produce(self, api: "CobblerAPI", seed_data: Dict[str, Any]):
        """
        Return a File forged from seed_data

        :param api: Parameter is skipped.
        :param seed_data: Data to seed the object with.
        :returns: The created object.
        """
        return file.File(api, **seed_data)

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

        :raises CX: In case a non existent object should be deleted.
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
                    self.api, obj, "/var/lib/cobbler/triggers/delete/file/pre/*", []
                )

        with self.lock:
            del self.listing[name]
        self.collection_mgr.serialize_delete(self, obj)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/file/post/*", []
                )
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/change/*", []
                )

        return
