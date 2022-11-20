"""
Cobbler module that contains the code for a Cobbler menu object.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2021 Yuriy Chelpanov <yuriy.chelpanov@gmail.com>

import uuid
from typing import List, Optional

from cobbler.items import item
from cobbler.cexceptions import CX


class Menu(item.Item):
    """
    A Cobbler menu object.
    """

    COLLECTION_TYPE = "menu"

    def __init__(self, api, *args, **kwargs):
        """
        Constructor
        """
        super().__init__(api, *args, **kwargs)
        self._display_name = ""

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this file object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = self.to_dict()
        cloned = Menu(self.api)
        cloned.from_dict(_dict)
        cloned.uid = uuid.uuid4().hex
        return cloned

    def from_dict(self, dictionary: dict):
        """
        Initializes the object with attributes from the dictionary.

        :param dictionary: The dictionary with values.
        """
        self._remove_depreacted_dict_keys(dictionary)
        super().from_dict(dictionary)

    @property
    def parent(self) -> Optional["Menu"]:
        """
        Parent menu of a menu instance.

        :getter: The menu object or None.
        :setter: Sets the parent.
        """
        if not self._parent:
            return None
        return self.api.menus().find(name=self._parent)

    @parent.setter
    def parent(self, value: str):
        """
        Setter for the parent menu of a menu.

        :param value: The name of the parent to set.
        :raises CX: Raised in case of self parenting or if the menu with value ``value`` is not found.
        """
        if not isinstance(value, str):
            raise TypeError('Property "parent" must be of type str!')
        old_parent = self._parent
        if isinstance(old_parent, Menu):
            old_parent.children.remove(self.name)
        if not value:
            self._parent = ""
            return
        if value == self.name:
            # check must be done in two places as the parent setter could be called before/after setting the name...
            raise CX("self parentage is weird")
        found = self.api.menus().find(name=value)
        if found is None:
            raise CX(f"menu {value} not found")
        self._parent = value
        self.depth = found.depth + 1
        new_parent = self._parent
        if isinstance(new_parent, Menu) and self.name not in new_parent.children:
            new_parent.children.append(self.name)

    @property
    def children(self) -> List[str]:
        """
        Child menu of a menu instance.

        :getter: Returns the children.
        :setter: Sets the children. Raises a TypeError if children have the wrong type.
        """
        return self._children

    @children.setter
    def children(self, value: List[str]):
        """
        Setter for the children.

        :param value: The value to set the children to.
        :raises TypeError: Raised in case the children of menu have the wrong type.
        """
        if not isinstance(value, list):
            raise TypeError("Field children of object menu must be of type list.")
        if isinstance(value, list):
            if not all(isinstance(x, str) for x in value):
                raise TypeError(
                    "Field children of object menu must be of type list and all items need to be menu "
                    "names (str)."
                )
            self._children = []
            for name in value:
                menu = self.api.find_menu(name=name)
                if menu is not None:
                    self._children.append(name)
                else:
                    self.logger.warning(
                        'Menu with the name "%s" did not exist. Skipping setting as a child!',
                        name,
                    )

    #
    # specific methods for item.Menu
    #

    @property
    def display_name(self) -> str:
        """
        Returns the display name.

        :getter: Returns the display name for the boot menu.
        :setter: Sets the display name for the boot menu.
        """
        return self._display_name

    @display_name.setter
    def display_name(self, display_name: str):
        """
        Setter for the display_name of the item.

        :param display_name: The new display_name. If ``None`` the display_name will be set to an emtpy string.
        """
        self._display_name = display_name
