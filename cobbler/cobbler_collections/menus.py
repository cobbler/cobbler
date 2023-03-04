"""
Cobbler module that at runtime holds all menus in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2021 Yuriy Chelpanov <yuriy.chelpanov@gmail.com>

from cobbler.items import menu
from cobbler.cobbler_collections import collection
from cobbler import utils
from cobbler.cexceptions import CX


class Menus(collection.Collection):
    """
    A menu represents an element of the hierarchical boot menu.
    """

    @staticmethod
    def collection_type() -> str:
        return "menu"

    @staticmethod
    def collection_types() -> str:
        return "menus"

    def factory_produce(self, api, item_dict):
        """
        Return a Menu forged from item_dict

        :param api: The cobblerd API.
        :param item_dict: The seed data.
        :return: A new menu instance.
        """
        new_menu = menu.Menu(api)
        new_menu.from_dict(item_dict)
        return new_menu

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
            for item in items:
                item.menu = ""

        if recursive:
            kids = obj.descendants
            kids.sort(key=lambda x: -x.depth)
            for kid in kids:
                if self.api.find_menu(name=kid) is not None:
                    self.api.remove_menu(
                        kid,
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
