"""
Cobbler module that contains the code for a Cobbler menu object.

Changelog:

V3.4.0 (unreleased):
    * Changes:
        * Constructor: ``kwargs`` can now be used to seed the item during creation.
        * ``children``: The property was moved to the base class.
        * ``parent``: The property was moved to the base class.
        * ``from_dict()``: The method was moved to the base class.
V3.3.4 (unreleased):
    * No changes
V3.3.3:
    * Changed:
        * ``check_if_valid()``: Now present in base class.
V3.3.2:
    * No changes
V3.3.1:
    * No changes
V3.3.0:
    * Inital version of the item type.
    * Added:
        * display_name: str
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2021 Yuriy Chelpanov <yuriy.chelpanov@gmail.com>

import copy
from typing import TYPE_CHECKING, Any

from cobbler.decorator import LazyProperty
from cobbler.items.abstract import item_inheritable

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Menu(item_inheritable.InheritableItem):
    """
    A Cobbler menu object.
    """

    TYPE_NAME = "menu"
    COLLECTION_TYPE = "menu"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any) -> None:
        """
        Constructor

        :param api: The Cobbler API object which is used for resolving information.
        """
        super().__init__(api)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._display_name = ""

        if len(kwargs) > 0:
            self.from_dict(kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self) -> "Menu":
        """
        Clone this file object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = copy.deepcopy(self.to_dict())
        _dict.pop("uid", None)
        return Menu(self.api, **_dict)

    #
    # specific methods for item.Menu
    #

    @LazyProperty
    def display_name(self) -> str:
        """
        Returns the display name.

        :getter: Returns the display name for the boot menu.
        :setter: Sets the display name for the boot menu.
        """
        return self._display_name

    @display_name.setter
    def display_name(self, display_name: str) -> None:
        """
        Setter for the display_name of the item.

        :param display_name: The new display_name. If ``None`` the display_name will be set to an emtpy string.
        """
        self._display_name = display_name
