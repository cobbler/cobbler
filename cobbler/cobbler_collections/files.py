"""
Cobbler module that at runtime holds all files in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2010, Kelsey Hightower <kelsey.hightower@gmail.com>

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
        new_file = file.File(api)
        new_file.from_dict(item_dict)
        return new_file

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

        :raises CX: In case a non existent object should be deleted.
        """
        obj = self.find(name=name)

        if obj is None:
            raise CX(f"cannot delete an object that does not exist: {name}")

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
