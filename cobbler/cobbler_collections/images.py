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
        ref: image.Image,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = True,
        rebuild_menu: bool = True,
    ) -> None:
        """
        Remove the given element from the collection

        :param ref: The object to delete
        :param with_delete: In case the deletion triggers are executed for this image.
        :param with_sync: In case a Cobbler Sync should be executed after the action.
        :param with_triggers: In case the Cobbler Trigger mechanism should be executed.
        :param recursive: In case you want to delete all objects this image references.
        :param rebuild_menu: unused
        :raises CX: Raised in case you want to delete a none existing image.
        """
        # rebuild_menu is not used
        _ = rebuild_menu

        if ref is None:  # type: ignore
            raise CX("cannot delete an object that does not exist")

        # first see if any Groups use this distro
        if not recursive:
            search_result = self.api.find_system(True, image=ref.uid)
            if isinstance(search_result, list) and len(search_result) > 0:
                raise CX(
                    f"removal would orphan the following system(s): {', '.join([ref.uid for ref in search_result])}"
                )

        if recursive:
            kids = self.api.find_system(return_list=True, image=ref.uid)
            if kids is None:
                kids = []
            if not isinstance(kids, list):
                raise ValueError("Expected list or None from find_items!")
            for k in kids:
                self.api.remove_system(k, recursive=True, with_sync=with_sync)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/delete/image/pre/*", []
                )
            if with_sync:
                self.remove_quick_pxe_sync(ref)

        with self.lock:
            self.remove_from_indexes(ref)
            del self.listing[ref.uid]
        self.collection_mgr.serialize_delete(self, ref)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/delete/image/post/*", []
                )
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/change/*", []
                )

    def remove_quick_pxe_sync(
        self, ref: image.Image, rebuild_menu: bool = True
    ) -> None:
        self.api.get_sync().remove_single_image(ref)
