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
        name: str,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
    ) -> None:
        """
        Remove element named 'name' from the collection

        :param name: The name of the menu
        :param with_delete: In case the deletion triggers are executed for this menu.
        :param with_sync: In case a Cobbler Sync should be executed after the action.
        :param with_triggers: In case the Cobbler Trigger mechanism should be executed.
        :param recursive: In case you want to delete all objects this menu references.
        :raises CX: Raised in case you want to delete a none existing menu.
        """
        obj = self.find(name=name)
        if obj is None or not isinstance(obj, menu.Menu):
            raise CX(f"cannot delete an object that does not exist: {name}")

        for item_type in ["image", "profile"]:
            items = self.api.find_items(item_type, {"menu": obj.name}, return_list=True)
            if items is None:
                continue
            if not isinstance(items, list):
                raise ValueError("Expected list or None from find_items!")
            for item in items:
                item.menu = ""

        if recursive:
            kids = obj.descendants
            kids.sort(key=lambda x: -x.depth)
            for k in kids:
                self.api.remove_item(
                    k.COLLECTION_TYPE,
                    k,
                    recursive=False,
                    delete=with_delete,
                    with_triggers=with_triggers,
                )

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/menu/pre/*", []
                )
        with self.lock:
            del self.listing[name]
        self.collection_mgr.serialize_delete(self, obj)
        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/menu/post/*", []
                )
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/change/*", []
                )
            if with_sync:
                lite_sync = self.api.get_sync()
                lite_sync.remove_single_menu()
