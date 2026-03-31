"""
"ItemGroup" is the abstract base class for groups of items.

Changelog:
    * V3.4.0 (unreleased):
        * Initial creation of the class
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Enno Gotthold <enno.gotthold@suse.com>

from abc import ABC
from typing import TYPE_CHECKING, Any, List, Type

from cobbler import enums
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
        super().__init__(api)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._members: List[str] = []

        if len(kwargs) > 0:
            self.from_dict(kwargs)

    def _resolve(self, property_name: List[str]) -> Any:
        settings_name = property_name[-1]
        if property_name[-1] == "owners":
            settings_name = "default_ownership"
        raw_value = self.__get_raw_value(self, property_name)
        if raw_value == enums.VALUE_INHERITED:
            return getattr(self.api.settings(), settings_name)
        else:
            return raw_value

    def _resolve_enum(
        self, property_name: List[str], enum_type: Type[enums.ConvertableEnum]
    ) -> Any:
        # The DistroGroup doesn't have any enum types that need resolving.
        return None

    def _resolve_list(self, property_name: List[str]) -> List[Any]:
        """
        Resolves and merges a list property from the current object, its parent, and global settings.

        :param property_name: The list of strings that represent the names of the attributes/properties to travel to
            the target attribute.
        :returns: The list with all values blended together.
        """
        property_name_raw = property_name.copy()
        property_name_raw[-1] = "_" + property_name_raw[-1]

        attribute_value = self.__get_raw_value(self, property_name_raw)
        settings = self.api.settings()

        merged_list: List[Any] = []

        parent = self.parent
        if self.parent is None:
            parent = self.get_conceptual_parent()  # type: ignore
        try:
            merged_list.extend(self.__get_raw_value(parent, property_name))
        except AttributeError:
            # Does not have the requested attribute
            pass
        if hasattr(settings, property_name[-1]):
            merged_list.extend(getattr(settings, property_name[-1]))

        if attribute_value != enums.VALUE_INHERITED:
            merged_list.extend(attribute_value)

        return merged_list

    def __get_raw_value(self, obj: Any, property_name: List[str]) -> Any:
        """
        Retrieves the raw value of a nested attribute from an object using a list of property names.

        :returns: The raw value of the property.
        :raises AttributeError: In case the property doesn't have the requested attribute.
        """
        if hasattr(obj, f"_{property_name[0]}"):
            property_key = property_name.pop(0)
            if len(property_name) > 0:
                return self.__get_raw_value(getattr(obj, property_key), property_name)
            return getattr(obj, f"_{property_key}")
        raise AttributeError(
            f'Could not retrieve "{property_name[0]}" with obj "{obj}!'
        )

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
