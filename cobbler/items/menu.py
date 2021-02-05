"""
Copyright 2021 Yuriy Chelpanov
Yuriy Chelpanov <yuriy.chelpanov@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

from cobbler.items import item
from cobbler.cexceptions import CX


# this data structure is described in item.py
FIELDS = [
    # non-editable in UI (internal)
    ["ctime", 0, 0, "", False, "", 0, "int"],
    ["depth", 1, 1, "", False, "", 0, "int"],
    ["mtime", 0, 0, "", False, "", 0, "int"],
    ["uid", "", "", "", False, "", 0, "str"],

    # editable in UI
    ["comment", "", "", "Comment", True, "Free form text description", 0, "str"],
    ["name", "", None, "Name", True, "Ex: Systems", 0, "str"],
    ["display_name", "", "", "Name", True, "Ex: Systems menu", [], "str"],
    ["parent", '', '', "Parent Menu", True, "", [], "str"],
]


class Menu(item.Item):
    """
    A Cobbler menu object.
    """

    COLLECTION_TYPE = "menu"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.display_name = ""

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this file object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = self.to_dict()
        cloned = Menu(self.collection_mgr)
        cloned.from_dict(_dict)
        return cloned

    def get_fields(self):
        """
        Return all fields which this class has with its current values.

        :return: This is a list with lists.
        """
        return FIELDS

    def get_parent(self):
        """
        Return object next highest up the tree.
        """
        if not self.parent or self.parent == '':
            return None

        return self.collection_mgr.menus().find(name=self.parent)

    def check_if_valid(self):
        """
        Check if the profile is valid. This checks for an existing name and a distro as a conceptual parent.
        """
        # name validation
        if not self.name:
            raise CX("Name is required")

    #
    # specific methods for item.Menu
    #

    def set_display_name(self, display_name):
        """
        Setter for the display_name of the item.

        :param display_name: The new display_name. If ``None`` the comment will be set to an emtpy string.
        """
        if display_name is None:
            display_name = ""
        self.display_name = display_name

    def set_parent(self, parent_name):
        """
        Set parent menu for the submenu.

        :param parent_name: The name of the parent menu.
        """
        old_parent = self.get_parent()
        if isinstance(old_parent, item.Item):
            old_parent.children.pop(self.name, 'pass')
        if not parent_name:
            self.parent = ''
            return
        if parent_name == self.name:
            # check must be done in two places as set_parent could be called before/after
            # set_name...
            raise CX("self parentage is weird")
        found = self.collection_mgr.menus().find(name=parent_name)
        if found is None:
            raise CX("menu %s not found" % parent_name)
        self.parent = parent_name
        self.depth = found.depth + 1
        parent = self.get_parent()
        if isinstance(parent, item.Item):
            parent.children[self.name] = self
# EOF
