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

    TYPE_NAME = "menu"
    COLLECTION_TYPE = "menu"

    def __init__(self, api, *args, **kwargs):
        """
        Constructor
        """
        super().__init__(api, *args, **kwargs)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._display_name = ""
        if not self._has_initialized:
            self._has_initialized = True

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
