"""
Cobbler module that at runtime holds all images in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from typing import TYPE_CHECKING, Any, Dict

from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import collection
from cobbler.items import image

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Images(collection.Collection[image.Image]):
    """
    A image instance represents a ISO or virt image we want to track
    and repeatedly install.  It differs from a answer-file based installation.
    """

    @staticmethod
    def collection_type() -> str:
        return "image"

    @staticmethod
    def collection_types() -> str:
        return "images"

    def factory_produce(self, api: "CobblerAPI", seed_data: Dict[str, Any]):
        """
        Return a Distro forged from seed_data

        :param api: Parameter is skipped.
        :param seed_data: Data to seed the object with.
        :returns: The created object.
        """
        return image.Image(self.api, **seed_data)

    def remove(
        self,
        name: str,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = True,
    ) -> None:
        """
        Remove element named 'name' from the collection

        :raises CX: In case object does not exist or it would orhan a system.
        """
        # NOTE: with_delete isn't currently meaningful for repos but is left in for consistency in the API. Unused.
        obj = self.listing.get(name, None)

        if obj is None:
            raise CX(f"cannot delete an object that does not exist: {name}")

        # first see if any Groups use this distro
        if not recursive:
            for system in self.api.systems():
                if system.image == name:
                    raise CX(f"removal would orphan system: {system.name}")

        if recursive:
            kids = self.api.find_system(return_list=True, **{"image": obj.name})
            if kids is None:
                kids = []
            if not isinstance(kids, list):
                raise ValueError("Expected list or None from find_items!")
            for k in kids:
                self.api.remove_system(k, recursive=True)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/image/pre/*", []
                )
            if with_sync:
                lite_sync = self.api.get_sync()
                lite_sync.remove_single_image(obj)

        with self.lock:
            del self.listing[name]
        self.collection_mgr.serialize_delete(self, obj)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/image/post/*", []
                )
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/change/*", []
                )
