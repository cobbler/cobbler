"""
Cobbler module that at runtime holds all menus in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2021 Yuriy Chelpanov <yuriy.chelpanov@gmail.com>

from typing import TYPE_CHECKING, Any, Dict

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

    def remove_quick_pxe_sync(self, ref: menu.Menu, rebuild_menu: bool = True) -> None:
        """
        Rebuild the PXE boot menu after a menu has been removed.

        .. note:: ``rebuild_menu`` is currently not forwarded to the underlying sync call, so the PXE menu is
                   always rebuilt regardless of this flag's value.

        :param ref: Unused; the removed menu object itself is not needed to rebuild the PXE menu.
        :param rebuild_menu: Intended to control whether the PXE menu is rebuilt (see note above).
        """
        self.api.get_sync().remove_single_menu()
