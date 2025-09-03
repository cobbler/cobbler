"""
Cobbler module that at runtime holds all menus in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2021 Yuriy Chelpanov <yuriy.chelpanov@gmail.com>

from typing import TYPE_CHECKING, Any, Dict

from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import collection
from cobbler.items import menu

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Menus(collection.Collection[menu.Menu]):
    """
    A menu represents an element of the hierarchical boot menu.
    """

    @staticmethod
    def collection_type() -> str:
        return "menu"

    @staticmethod
    def collection_types() -> str:
        return "menus"

    def factory_produce(
        self, api: "CobblerAPI", seed_data: Dict[str, Any]
    ) -> menu.Menu:
        """
        Return a Menu forged from seed_data

        :param api: Parameter is skipped.
        :param seed_data: Data to seed the object with.
        :returns: The created object.
        """
        return menu.Menu(self.api, **seed_data)

    def remove(
        self,
        ref: menu.Menu,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
        rebuild_menu: bool = True,
    ) -> None:
        """
        Remove the given element from the collection

        :param ref: The object to delete
        :param with_delete: In case the deletion triggers are executed for this menu.
        :param with_sync: In case a Cobbler Sync should be executed after the action.
        :param with_triggers: In case the Cobbler Trigger mechanism should be executed.
        :param recursive: In case you want to delete all objects this menu references.
        :param rebuild_menu: unused
        :raises CX: Raised in case you want to delete a none existing menu.
        """
        # rebuild_menu is not used
        _ = rebuild_menu

        if ref is None:  # type: ignore
            raise CX("cannot delete an object that does not exist")

        for item_type in ["image", "profile"]:
            items = self.api.find_items(item_type, {"menu": ref.uid}, return_list=True)
            if items is None:
                continue
            if not isinstance(items, list):
                raise ValueError("Expected list or None from find_items!")
            for item in items:
                item.menu = ""

        if recursive:
            kids = ref.descendants
            kids.sort(key=lambda x: -x.depth)
            for k in kids:
                self.api.remove_item(
                    k.COLLECTION_TYPE,
                    k,
                    recursive=False,
                    delete=with_delete,
                    with_triggers=with_triggers,
                    with_sync=with_sync,
                )

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/delete/menu/pre/*", []
                )
        with self.lock:
            self.remove_from_indexes(ref)
            del self.listing[ref.uid]
        self.collection_mgr.serialize_delete(self, ref)
        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/delete/menu/post/*", []
                )
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/change/*", []
                )
            if with_sync:
                self.remove_quick_pxe_sync(ref)

    def remove_quick_pxe_sync(self, ref: menu.Menu, rebuild_menu: bool = True) -> None:
        self.api.get_sync().remove_single_menu()
