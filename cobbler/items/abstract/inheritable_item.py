"""
"InheritableItem" the entry point for items that have logical parents and children.

Changelog:
    * V3.4.0 (unreleased):
        * Initial creation of the class
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Enno Gotthold <enno.gotthold@suse.com>

from abc import ABC
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Union

from cobbler import enums
from cobbler.cexceptions import CX
from cobbler.decorator import LazyProperty
from cobbler.items.abstract.base_item import BaseItem

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.distro import Distro
    from cobbler.items.menu import Menu
    from cobbler.items.profile import Profile
    from cobbler.items.system import System
    from cobbler.settings import Settings


class HierarchyItem(NamedTuple):
    """
    NamedTuple to display the dependency that a single item has.
    The `dependant_item_type` object is stored in the `dependant_type_attribute` attribute of the Item.

    For example, an item with HierarchyItem("profile", "repos") contains `Profile` objects in the `repos` attribute.
    """

    dependant_item_type: str
    dependant_type_attribute: str


class LogicalHierarchy(NamedTuple):
    """
    NamedTuple to display the order of hierarchy in the dependency tree.
    """

    up: List[HierarchyItem]
    down: List[HierarchyItem]


class InheritableItem(BaseItem, ABC):
    """
    Abstract class that acts as a starting point in the inheritance for items that have a parent and children.
    """

    # Constants
    TYPE_NAME = "inheritable_abstract"
    COLLECTION_TYPE = "inheritable_abstract"

    # Item types dependencies.
    # Used to determine descendants and cache invalidation.
    # Format: {"Item Type": [("Dependent Item Type", "Dependent Type attribute"), ..], [..]}
    TYPE_DEPENDENCIES: Dict[str, List[HierarchyItem]] = {
        "repo": [
            HierarchyItem("profile", "repos"),
        ],
        "distro": [
            HierarchyItem("profile", "distro"),
        ],
        "menu": [
            HierarchyItem("menu", "parent"),
            HierarchyItem("image", "menu"),
            HierarchyItem("profile", "menu"),
        ],
        "profile": [
            HierarchyItem("profile", "parent"),
            HierarchyItem("system", "profile"),
        ],
        "image": [
            HierarchyItem("system", "image"),
        ],
        "system": [],
    }

    # Defines a logical hierarchy of Item Types.
    # Format: {"Item Type": [("Previous level Type", "Attribute to go to the previous level",), ..],
    #                       [("Next level Item Type", "Attribute to move from the next level"), ..]}
    LOGICAL_INHERITANCE: Dict[str, LogicalHierarchy] = {
        "distro": LogicalHierarchy(
            [],
            [
                HierarchyItem("profile", "distro"),
            ],
        ),
        "profile": LogicalHierarchy(
            [
                HierarchyItem("distro", "distro"),
            ],
            [
                HierarchyItem("system", "profile"),
            ],
        ),
        "image": LogicalHierarchy(
            [],
            [
                HierarchyItem("system", "image"),
            ],
        ),
        "system": LogicalHierarchy(
            [HierarchyItem("image", "image"), HierarchyItem("profile", "profile")],
            [],
        ),
    }

    def __init__(
        self, api: "CobblerAPI", *args: Any, is_subobject: bool = False, **kwargs: Any
    ):
        """
        Constructor.  Requires a back reference to the CobblerAPI object.

        NOTE: is_subobject is used for objects that allow inheritance in their trees. This inheritance refers to
        conceptual inheritance, not Python inheritance. Objects created with is_subobject need to call their
        setter for parent immediately after creation and pass in a value of an object of the same type. Currently this
        is only supported for profiles. Sub objects blend their data with their parent objects and only require a valid
        parent name and a name for themselves, so other required options can be gathered from items further up the
        Cobbler tree.

                           distro
                               profile
                                    profile  <-- created with is_subobject=True
                                         system   <-- created as normal
                           image
                               system
                           menu
                               menu

        For consistency, there is some code supporting this in all object types, though it is only usable
        (and only should be used) for profiles at this time.  Objects that are children of
        objects of the same type (i.e. subprofiles) need to pass this in as True.  Otherwise, just
        use False for is_subobject and the parent object will (therefore) have a different type.

        The keyword arguments are used to seed the object. This is the preferred way over ``from_dict`` starting with
        Cobbler version 3.4.0.

        :param api: The Cobbler API object which is used for resolving information.
        :param is_subobject: See above extensive description.
        """
        super().__init__(api, *args, **kwargs)

        self._depth = 0
        self._parent = ""
        self._is_subobject = is_subobject
        self._children: List[str] = []
        self._inmemory = True

        if len(kwargs) > 0:
            kwargs.update({"is_subobject": is_subobject})
            self.from_dict(kwargs)

        if not self._has_initialized:
            self._has_initialized = True

    @LazyProperty
    def depth(self) -> int:
        """
        This represents the logical depth of an object in the category of the same items. Important for the order of
        loading items from the disk and other related features where the alphabetical order is incorrect for sorting.

        :getter: The logical depth of the object.
        :setter: The new int for the logical object-depth.
        """
        return self._depth

    @depth.setter  # type: ignore[no-redef]
    def depth(self, depth: int) -> None:
        """
        Setter for depth.

        :param depth: The new value for depth.
        """
        if not isinstance(depth, int):  # type: ignore
            raise TypeError("depth needs to be of type int")
        self._depth = depth

    @LazyProperty
    def parent(self) -> Optional[Union["System", "Profile", "Distro", "Menu"]]:
        """
        This property contains the name of the parent of an object. In case there is not parent this return
        None.

        :getter: Returns the parent object or None if it can't be resolved via the Cobbler API.
        :setter: The uid of the new logical parent.
        """
        if self._parent == "":
            return None
        return self.api.get_items(self.COLLECTION_TYPE).listing.get(self._parent)  # type: ignore

    @parent.setter  # type: ignore[no-redef]
    def parent(self, parent: Union["InheritableItem", str]) -> None:
        """
        Set the parent object for this object.

        :param parent: The new parent object. This needs to be a descendant in the logical inheritance chain.
        """
        if not isinstance(parent, str) and not isinstance(parent, InheritableItem):  # type: ignore
            raise TypeError('Property "parent" must be of type InheritableItem or str!')
        found = None
        if isinstance(parent, InheritableItem):
            found = parent
            parent = parent.uid
        old_parent = self._parent
        if self.TYPE_NAME == "profile":  # type: ignore[reportUnnecessaryComparison]
            old_arch: Optional[enums.Archs] = getattr(self, "arch")
            new_arch: Optional[enums.Archs] = None
        items = self.api.get_items(self.COLLECTION_TYPE)
        if not parent:
            self._parent = ""
            items.update_index_value(self, "parent", old_parent, "")
            if self.TYPE_NAME == "profile":  # type: ignore[reportUnnecessaryComparison]
                new_arch = getattr(self, "arch")
                if new_arch != old_arch:  # type: ignore[reportPossiblyUnboundVariable]
                    items.update_index_value(self, "arch", old_arch, new_arch)  # type: ignore[reportArgumentType]
                    for child in self.tree_walk():
                        items.update_index_value(child, "arch", old_arch, new_arch)  # type: ignore[reportArgumentType]
            return
        if parent == self.uid:
            # check must be done in two places as setting parent could be called before/after setting name...
            raise CX("self parentage is forbidden")
        if found is None:
            found = items.listing.get(parent)
        if found is None:
            raise CX(f'parent item "{parent}" not found, inheritance not possible')
        self._parent = parent
        self.depth = found.depth + 1  # type: ignore
        items.update_index_value(self, "parent", old_parent, parent)
        if self.TYPE_NAME == "profile":  # type: ignore[reportUnnecessaryComparison]
            new_arch = getattr(self, "arch")
            if new_arch != old_arch:  # type: ignore[reportPossiblyUnboundVariable]
                items.update_index_value(self, "arch", old_arch, new_arch)  # type: ignore[reportArgumentType]
                for child in self.tree_walk():
                    items.update_index_value(child, "arch", old_arch, new_arch)  # type: ignore[reportArgumentType]

    @LazyProperty
    def get_parent(self) -> str:
        """
        This method returns the name of the parent for the object. In case there is not parent this return
        empty string.
        """
        return self._parent

    def get_conceptual_parent(self) -> Optional["InheritableItem"]:
        """
        The parent may just be a superclass for something like a sub-profile. Get the first parent of a different type.

        :return: The first item which is conceptually not from the same type.
        """
        if self is None:  # type: ignore
            return None

        curr_obj = self
        next_obj = curr_obj.parent
        while next_obj is not None:
            curr_obj = next_obj
            next_obj = next_obj.parent

        if curr_obj.TYPE_NAME in curr_obj.LOGICAL_INHERITANCE:
            for prev_level in curr_obj.LOGICAL_INHERITANCE[curr_obj.TYPE_NAME].up:
                prev_level_type = prev_level.dependant_item_type
                prev_level_uid = getattr(
                    curr_obj, "_" + prev_level.dependant_type_attribute
                )
                if prev_level_uid is not None and prev_level_uid != "":
                    prev_level_item = self.api.find_items(
                        prev_level_type, {"uid": prev_level_uid}, return_list=False
                    )
                    if prev_level_item is not None and not isinstance(
                        prev_level_item, list
                    ):
                        return prev_level_item
        return None

    @property
    def logical_parent(self) -> Any:
        """
        This property contains the name of the logical parent of an object. In case there is not parent this return
        None.

        .. note:: This is a read only property.

        :getter: Returns the parent object or None if it can't be resolved via the Cobbler API.
        """
        parent = self.parent
        if parent is None:
            return self.get_conceptual_parent()
        return parent

    @property
    def children(self) -> List["InheritableItem"]:
        """
        The list of logical children of any depth.

        .. note:: This is a read only property.

        :getter: An empty list in case of items which don't have logical children.
        """
        if self.COLLECTION_TYPE not in ["profile", "menu"]:
            return []

        results: Optional[List["InheritableItem"]] = self.api.find_items(  # type: ignore
            self.COLLECTION_TYPE, {"parent": self._uid}, return_list=True
        )
        if results is None:
            return []
        return results

    def tree_walk(
        self, attribute_name: Optional[str] = None
    ) -> List["InheritableItem"]:
        """
        Get all children related by parent/child relationship.

        :return: The list of children objects.
        """
        results: List["InheritableItem"] = []
        for child in self.children:
            if (
                attribute_name is None
                or getattr(child, attribute_name) == enums.VALUE_INHERITED
            ):
                results.append(child)
                results.extend(child.tree_walk(attribute_name))

        return results

    @property
    def descendants(self) -> List["InheritableItem"]:
        """
        Get objects that depend on this object, i.e. those that would be affected by a cascading delete, etc.

        .. note:: This is a read only property.

        :getter: This is a list of all descendants. May be empty if none exist.
        """
        childs = self.tree_walk()
        results = set(childs)
        childs.append(self)  # type: ignore
        for child in childs:
            for item_type in self.TYPE_DEPENDENCIES[child.COLLECTION_TYPE]:
                dep_type_items = self.api.find_items(
                    item_type.dependant_item_type,
                    {item_type.dependant_type_attribute: child.uid},
                    return_list=True,
                )
                if dep_type_items is None or not isinstance(dep_type_items, list):
                    raise ValueError("Expected list to be returned by find_items")
                results.update(dep_type_items)
                for dep_item in dep_type_items:
                    results.update(dep_item.descendants)
        return list(results)

    @LazyProperty
    def is_subobject(self) -> bool:
        """
        Weather the object is a subobject of another object or not.

        :getter: True in case the object is a subobject, False otherwise.
        :setter: Sets the value. If this is not a bool, this will raise a ``TypeError``.
        """
        return self._is_subobject

    @is_subobject.setter  # type: ignore[no-redef]
    def is_subobject(self, value: bool) -> None:
        """
        Setter for the property ``is_subobject``.

        :param value: The boolean value whether this is a subobject or not.
        :raises TypeError: In case the value was not of type bool.
        """
        if not isinstance(value, bool):  # type: ignore
            raise TypeError(
                "Field is_subobject of object item needs to be of type bool!"
            )
        self._is_subobject = value

    def grab_tree(self) -> List[Union["InheritableItem", "Settings"]]:
        """
        Climb the tree and get every node.

        :return: The list of items with all parents from that object upwards the tree. Contains at least the item
                 itself and the settings of Cobbler.
        """
        results: List[Union["InheritableItem", "Settings"]] = [self]
        parent = self.logical_parent
        while parent is not None:
            results.append(parent)
            parent = parent.logical_parent
            # FIXME: Now get the object and check its existence
        results.append(self.api.settings())
        self.logger.debug(
            "grab_tree found %s children (including settings) of this object",
            len(results),
        )
        return results
