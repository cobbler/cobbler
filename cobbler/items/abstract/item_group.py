"""
"ItemGroup" is the abstract base class for groups of items.

Changelog:
    * V3.4.0 (unreleased):
        * Initial creation of the class
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Enno Gotthold <enno.gotthold@suse.com>

from abc import ABC
from typing import TYPE_CHECKING, Any, List

from cobbler.items.abstract.inheritable_item import InheritableItem

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI

    LazyProperty = property
else:
    from cobbler.decorator import LazyProperty


class ItemGroup(InheritableItem, ABC):
    """
    Abstract class for item groups in Cobbler.
    """

    TYPE_NAME = "item_group_abstract"
    COLLECTION_TYPE = "item_groups"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any):
        """
        Constructor.

        :param api: The Cobbler API object.
        """
        super().__init__(api, *args, **kwargs)

        self._members: List[str] = []

        if len(kwargs) > 0:
            self.from_dict(kwargs)

    @LazyProperty
    def members(self) -> List[str]:
        """
        :getter: The members of this group.
        :setter: Set the members of this group.
        """
        return self._members

    @members.setter
    def members(self, value: List[str]) -> None:
        """
        Set the members of this item group.

        :param value: A list of string uids representing the members of the group.
        """
        if not isinstance(value, list):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("members must be a list")
        for member in value:
            if not isinstance(
                member, str
            ):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise TypeError("All members must be of type string")
        self._members = value
