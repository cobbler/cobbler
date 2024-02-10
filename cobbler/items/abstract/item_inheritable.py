"""
TODO
"""

import uuid
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, TypeVar, Union

from cobbler import enums, utils
from cobbler.cexceptions import CX
from cobbler.decorator import InheritableDictProperty, InheritableProperty, LazyProperty
from cobbler.items.abstract.base_item import BaseItem

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.cobbler_collections.collection import ITEM_UNION
    from cobbler.items.distro import Distro
    from cobbler.items.menu import Menu
    from cobbler.items.profile import Profile
    from cobbler.items.system import System
    from cobbler.settings import Settings


T = TypeVar("T")


class InheritableItem(BaseItem):
    """
    TODO
    """

    # Constants
    TYPE_NAME = "inheritableitem"
    COLLECTION_TYPE = "inheritableitem"

    # Item types dependencies.
    # Used to determine descendants and cache invalidation.
    # Format: {"Item Type": [("Dependent Item Type", "Dependent Type attribute"), ..], [..]}
    TYPE_DEPENDENCIES: Dict[str, List[Tuple[str, str]]] = {
        "repo": [
            ("profile", "repos"),
        ],
        "distro": [
            ("profile", "distro"),
        ],
        "menu": [
            ("menu", "parent"),
            ("image", "menu"),
            ("profile", "menu"),
        ],
        "profile": [
            ("profile", "parent"),
            ("system", "profile"),
        ],
        "image": [
            ("system", "image"),
        ],
        "system": [],
    }

    # Defines a logical hierarchy of Item Types.
    # Format: {"Item Type": [("Previous level Type", "Attribute to go to the previous level",), ..],
    #                       [("Next level Item Type", "Attribute to move from the next level"), ..]}
    LOGICAL_INHERITANCE: Dict[
        str, Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]
    ] = {
        "distro": (
            [],
            [
                ("profile", "distro"),
            ],
        ),
        "profile": (
            [
                ("distro", "distro"),
            ],
            [
                ("system", "profile"),
            ],
        ),
        "image": (
            [],
            [
                ("system", "image"),
            ],
        ),
        "system": ([("image", "image"), ("profile", "profile")], []),
    }

    @classmethod
    def _remove_depreacted_dict_keys(cls, dictionary: Dict[Any, Any]) -> None:
        super()._remove_depreacted_dict_keys(dictionary)
        if "children" in dictionary:
            dictionary.pop("children")

    def __init__(
        self, api: "CobblerAPI", *args: Any, is_subobject: bool = False, **kwargs: Any
    ) -> None:
        """
        NOTE: is_subobject is used for objects that allow inheritance in their trees. This inheritance refers to
        conceptual inheritance, not Python inheritance. Objects created with is_subobject need to call their
        setter for parent immediately after creation and pass in a value of an object of the same type. Currently this
        is only supported for profiles. Subobjects blend their data with their parent objects and only require a valid
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

        :param api: The Cobbler API object which is used for resolving information.
        :param is_subobject: See above extensive description.
        """
        super().__init__(api, *args, **kwargs)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._parent = ""
        self._depth = 0
        self._children: List[str] = []
        self._is_subobject = is_subobject

        if len(kwargs) > 0:
            kwargs.update({"is_subobject": is_subobject})
            InheritableItem.from_dict(self, kwargs)
        if self._uid == "":
            self._uid = uuid.uuid4().hex

        if not self._has_initialized:
            self._has_initialized = True

    @abstractmethod
    def make_clone(self) -> "ITEM":  # type: ignore
        """
        Must be defined in any subclass
        """
        raise NotImplementedError("Must be implemented in a specific Item")

    @LazyProperty
    def depth(self) -> int:
        """
        This represents the logical depth of an object in the category of the same items. Important for the order of
        loading items from the disk and other related features where the alphabetical order is incorrect for sorting.

        :getter: The logical depth of the object.
        :setter: The new int for the logical object-depth.
        """
        return self._depth

    @depth.setter
    def depth(self, depth: int) -> None:
        """
        Setter for depth.

        :param depth: The new value for depth.
        """
        if not isinstance(depth, int):  # type: ignore
            raise TypeError("depth needs to be of type int")
        self._depth = depth

    @LazyProperty
    def is_subobject(self) -> bool:
        """
        Weather the object is a subobject of another object or not.

        :getter: True in case the object is a subobject, False otherwise.
        :setter: Sets the value. If this is not a bool, this will raise a ``TypeError``.
        """
        return self._is_subobject

    @is_subobject.setter
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

    @LazyProperty
    def parent(self) -> Optional[Union["System", "Profile", "Distro", "Menu"]]:
        """
        This property contains the name of the parent of an object. In case there is not parent this return
        None.

        :getter: Returns the parent object or None if it can't be resolved via the Cobbler API.
        :setter: The name of the new logical parent.
        """
        if self._parent == "":
            return None
        return self.api.get_items(self.COLLECTION_TYPE).get(self._parent)  # type: ignore

    @parent.setter
    def parent(self, parent: str) -> None:
        """
        Set the parent object for this object.

        :param parent: The new parent object. This needs to be a descendant in the logical inheritance chain.
        """
        if not isinstance(parent, str):  # type: ignore
            raise TypeError('Property "parent" must be of type str!')
        if not parent:
            self._parent = ""
            return
        if parent == self.name:
            # check must be done in two places as setting parent could be called before/after setting name...
            raise CX("self parentage is weird")
        found = self.api.get_items(self.COLLECTION_TYPE).get(parent)
        if found is None:
            raise CX(f'profile "{parent}" not found, inheritance not possible')
        self._parent = parent
        self.depth = found.depth + 1

    @property
    def children(self) -> List["InheritableItem"]:
        """
        The list of logical children of any depth.

        :getter: An empty list in case of items which don't have logical children.
        """
        results: List["InheritableItem"] = []
        list_items = self.api.get_items(self.COLLECTION_TYPE)
        for obj in list_items:
            if obj.get_parent == self._name:
                results.append(obj)
        return results

    @LazyProperty
    def get_parent(self) -> str:
        """
        This method returns the name of the parent for the object. In case there is not parent this return
        empty string.
        """
        return self._parent

    def get_conceptual_parent(self) -> Optional["ITEM_UNION"]:
        """
        The parent may just be a superclass for something like a subprofile. Get the first parent of a different type.

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
            for prev_level in curr_obj.LOGICAL_INHERITANCE[curr_obj.TYPE_NAME][0]:
                prev_level_type = prev_level[0]
                prev_level_name = getattr(curr_obj, "_" + prev_level[1])
                if prev_level_name is not None and prev_level_name != "":
                    prev_level_item = self.api.find_items(
                        prev_level_type, name=prev_level_name, return_list=False
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

        :getter: Returns the parent object or None if it can't be resolved via the Cobbler API.
        :setter: The name of the new logical parent.
        """
        parent = self.parent
        if parent is None:
            return self.get_conceptual_parent()
        return parent

    def tree_walk(self) -> List["InheritableItem"]:
        """
        Get all children related by parent/child relationship.

        :return: The list of children objects.
        """
        results: List["InheritableItem"] = []
        for child in self.children:
            results.append(child)
            results.extend(child.tree_walk())

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
            for item_type in InheritableItem.TYPE_DEPENDENCIES[child.COLLECTION_TYPE]:
                dep_type_items = self.api.find_items(
                    item_type[0], {item_type[1]: child.name}, return_list=True
                )
                if dep_type_items is None or not isinstance(dep_type_items, list):
                    raise ValueError("Expected list to be returned by find_items")
                results.update(dep_type_items)
                for dep_item in dep_type_items:
                    results.update(dep_item.descendants)
        return list(results)

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

    def clean_cache(self, name: Optional[str] = None):
        """
        Clearing the Item cache.

        :param name: The name of Item attribute or None.
        """
        if not self.api.settings().cache_enabled:
            return

        if self._inmemory:
            self._clean_dict_cache(name)

    def _clean_dict_cache(self, name: Optional[str]):
        """
        Clearing the Item dict cache.

        :param name: The name of Item attribute or None.
        """
        if name is not None and self._inmemory:
            attr = getattr(type(self), name[1:])
            if (
                isinstance(attr, (InheritableProperty, InheritableDictProperty))
                and self.COLLECTION_TYPE != InheritableItem.COLLECTION_TYPE
                and self.api.get_items(self.COLLECTION_TYPE).get(self.name) is not None
            ):
                # Invalidating "resolved" caches
                for dep_item in self.descendants:
                    dep_item.cache.set_dict_cache(None, True)

        # Invalidating the cache of the object itself.
        self.cache.clean_dict_cache()

    def __common_resolve(self, property_name: str):
        settings_name = property_name
        if property_name.startswith("proxy_url_"):
            property_name = "proxy"
        if property_name == "owners":
            settings_name = "default_ownership"
        attribute = "_" + property_name

        return getattr(self, attribute), settings_name

    def __resolve_get_parent_or_settings(self, property_name: str, settings_name: str):
        settings = self.api.settings()
        conceptual_parent = self.get_conceptual_parent()

        if hasattr(self.parent, property_name):
            return getattr(self.parent, property_name)
        elif hasattr(conceptual_parent, property_name):
            return getattr(conceptual_parent, property_name)
        elif hasattr(settings, settings_name):
            return getattr(settings, settings_name)
        elif hasattr(settings, f"default_{settings_name}"):
            return getattr(settings, f"default_{settings_name}")
        return None

    def _resolve(self, property_name: str) -> Any:
        """
        Resolve the ``property_name`` value in the object tree. This function traverses the tree from the object to its
        topmost parent and returns the first value that is not inherited. If the tree does not contain a value the
        settings are consulted.

        :param property_name: The property name to resolve.
        :raises AttributeError: In case one of the objects try to inherit from a parent that does not have
                                ``property_name``.
        :return: The resolved value.
        """
        attribute_value, settings_name = self.__common_resolve(property_name)

        if attribute_value == enums.VALUE_INHERITED:
            possible_return = self.__resolve_get_parent_or_settings(
                property_name, settings_name
            )
            if possible_return is not None:
                return possible_return
            raise AttributeError(
                f'{type(self)} "{self.name}" inherits property "{property_name}", but neither its parent nor'
                f" settings have it"
            )

        return attribute_value

    def _resolve_enum(
        self, property_name: str, enum_type: Type[enums.ConvertableEnum]
    ) -> Any:
        """
        See :meth:`~cobbler.items.item.Item._resolve`
        """
        attribute_value, settings_name = self.__common_resolve(property_name)
        unwrapped_value = getattr(attribute_value, "value", "")
        if unwrapped_value == enums.VALUE_INHERITED:
            possible_return = self.__resolve_get_parent_or_settings(
                unwrapped_value, settings_name
            )
            if possible_return is not None:
                return enum_type(possible_return)
            raise AttributeError(
                f'{type(self)} "{self.name}" inherits property "{property_name}", but neither its parent nor'
                f" settings have it"
            )

        return attribute_value

    def _resolve_dict(self, property_name: str) -> Dict[str, Any]:
        """
        Merge the ``property_name`` dictionary of the object with the ``property_name`` of all its parents. The value
        of the child takes precedence over the value of the parent.

        :param property_name: The property name to resolve.
        :return: The merged dictionary.
        :raises AttributeError: In case the the the object had no attribute with the name :py:property_name: .
        """
        attribute = "_" + property_name

        attribute_value = getattr(self, attribute)
        settings = self.api.settings()

        merged_dict: Dict[str, Any] = {}

        conceptual_parent = self.get_conceptual_parent()
        if hasattr(conceptual_parent, property_name):
            merged_dict.update(getattr(conceptual_parent, property_name))
        elif hasattr(settings, property_name):
            merged_dict.update(getattr(settings, property_name))

        if attribute_value != enums.VALUE_INHERITED:
            merged_dict.update(attribute_value)

        utils.dict_annihilate(merged_dict)
        return merged_dict

    def _deduplicate_dict(
        self, property_name: str, value: Dict[str, T]
    ) -> Dict[str, T]:
        """
        Filter out the key:value pair may come from parent and global settings.
        Note: we do not know exactly which resolver does key:value belongs to, what we did is just deduplicate them.

        :param property_name: The property name to deduplicated.
        :param value: The value that should be deduplicated.
        :returns: The deduplicated dictionary
        """
        _, settings_name = self.__common_resolve(property_name)
        settings = self.api.settings()
        conceptual_parent = self.get_conceptual_parent()

        if hasattr(self.parent, property_name):
            parent_value = getattr(self.parent, property_name)
        elif hasattr(conceptual_parent, property_name):
            parent_value = getattr(conceptual_parent, property_name)
        elif hasattr(settings, settings_name):
            parent_value = getattr(settings, settings_name)
        elif hasattr(settings, f"default_{settings_name}"):
            parent_value = getattr(settings, f"default_{settings_name}")
        else:
            parent_value = {}

        # Because we use getattr pyright cannot correctly check this.
        for key in parent_value:  # type: ignore
            if key in value and parent_value[key] == value[key]:  # type: ignore
                value.pop(key)  # type: ignore

        return value

    def deserialize(self) -> None:
        def deserialize_ancestor(ancestor_item_type: str, ancestor_name: str):
            if ancestor_name not in {"", enums.VALUE_INHERITED}:
                ancestor = self.api.get_items(ancestor_item_type).get(ancestor_name)
                if ancestor is not None and not ancestor.inmemory:
                    ancestor.deserialize()

        item_dict = self.api.deserialize_item(self)
        if item_dict["inmemory"]:
            for (
                ancestor_item_type,
                ancestor_deps,
            ) in InheritableItem.TYPE_DEPENDENCIES.items():
                for ancestor_dep in ancestor_deps:
                    if self.TYPE_NAME == ancestor_dep[0]:
                        attr_name = ancestor_dep[1]
                        if attr_name not in item_dict:
                            continue
                        attr_val = item_dict[attr_name]
                        if isinstance(attr_val, str):
                            deserialize_ancestor(ancestor_item_type, attr_val)
                        elif isinstance(attr_val, list):  # type: ignore
                            attr_val: List[str]
                            for ancestor_name in attr_val:
                                deserialize_ancestor(ancestor_item_type, ancestor_name)
        self.from_dict(item_dict)
