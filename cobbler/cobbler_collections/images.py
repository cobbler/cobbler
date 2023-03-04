"""
Cobbler module that at runtime holds all images in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from cobbler.cobbler_collections import collection
from cobbler.items import image as image
from cobbler import utils
from cobbler.cexceptions import CX


class Images(collection.Collection):
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

    def factory_produce(self, api, item_dict):
        """
        Return a Distro forged from item_dict
        """
        new_image = image.Image(api)
        new_image.from_dict(item_dict)
        return new_image

    def remove(
        self,
        name,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = True,
    ):
        """
        Remove element named 'name' from the collection

        :raises CX: In case object does not exist or it would orhan a system.
        """
        # NOTE: with_delete isn't currently meaningful for repos but is left in for consistency in the API. Unused.
        obj = self.find(name=name)
        if obj is None:
            raise CX(f"cannot delete an object that does not exist: {name}")

        # first see if any Groups use this distro
        if not recursive:
            for system in self.api.systems():
                if system.image is not None and system.image == name:
                    raise CX(f"removal would orphan system: {system.name}")

        if recursive:
            kids = self.api.find_items("system", {"image": obj.name})
            for k in kids:
                self.api.remove_system(k, recursive=True)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/image/pre/*", []
                )
            if with_sync:
                lite_sync = self.api.get_sync()
                lite_sync.remove_single_image(name)

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
