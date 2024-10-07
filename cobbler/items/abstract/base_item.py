"""
"BaseItem" is the highest point in the object hierarchy of Cobbler. All concrete objects that can be generated should
inherit from it or one of its derived classes.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import copy
import enum
import fnmatch
import logging
import re
import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from cobbler import enums
from cobbler.cexceptions import CX
from cobbler.decorator import InheritableProperty, LazyProperty
from cobbler.items.abstract.item_cache import ItemCache
from cobbler.utils import input_converters

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


RE_OBJECT_NAME = re.compile(r"[a-zA-Z0-9_\-.:]*$")


class BaseItem(ABC):
    """
    Abstract base class to represent the common attributes that a concrete item needs to have at minimum.
    """

    # Constants
    TYPE_NAME = "base"
    COLLECTION_TYPE = "base"

    @staticmethod
    def _is_dict_key(name: str) -> bool:
        """
        Whether the attribute is part of the item's to_dict or not

        :name: The attribute name.
        """
        return (
            name[:1] == "_"
            and "__" not in name
            and name
            not in {
                "_cache",
                "_supported_boot_loaders",
                "_has_initialized",
                "_inmemory",
            }
        )

    @classmethod
    def __find_compare(
        cls,
        from_search: Union[str, List[Any], Dict[Any, Any], bool],
        from_obj: Union[str, List[Any], Dict[Any, Any], bool],
    ) -> bool:
        """
        Only one of the two parameters shall be given in this method. If you give both ``from_obj`` will be preferred.

        :param from_search: Tries to parse this str in the format as a search result string.
        :param from_obj: Tries to parse this str in the format of an obj str.
        :return: True if the comparison succeeded, False otherwise.
        :raises TypeError: In case the type of one of the two variables is wrong or could not be converted
                           intelligently.
        """
        del cls

        if isinstance(from_obj, str):
            # FIXME: fnmatch is only used for string to string comparisons which should cover most major usage, if
            #        not, this deserves fixing
            from_obj_lower = from_obj.lower()
            from_search_lower = from_search.lower()  # type: ignore
            # It's much faster to not use fnmatch if it's not needed
            if (
                "?" not in from_search_lower
                and "*" not in from_search_lower
                and "[" not in from_search_lower
            ):
                match = from_obj_lower == from_search_lower  # type: ignore
            else:
                match = fnmatch.fnmatch(from_obj_lower, from_search_lower)  # type: ignore
            return match  # type: ignore

        if isinstance(from_search, str):
            if isinstance(from_obj, list):
                from_search = input_converters.input_string_or_list(from_search)
                for list_element in from_search:
                    if list_element not in from_obj:
                        return False
                return True
            if isinstance(from_obj, dict):
                from_search = input_converters.input_string_or_dict(
                    from_search, allow_multiples=True
                )
                for dict_key in list(from_search.keys()):  # type: ignore
                    dict_value = from_search[dict_key]
                    if dict_key not in from_obj:
                        return False
                    if not dict_value == from_obj[dict_key]:
                        return False
                return True
            if isinstance(from_obj, bool):  # type: ignore
                inp = from_search.lower() in ["true", "1", "y", "yes"]
                if inp == from_obj:
                    return True
                return False

        raise TypeError(f"find cannot compare type: {type(from_obj)}")

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any):
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        # Attributes
        self._ctime = 0.0
        self._mtime = 0.0
        self._uid = uuid.uuid4().hex
        self._name = ""
        self._comment = ""
        self._owners: Union[List[str], str] = enums.VALUE_INHERITED
        self._inmemory = (
            False  # Set this to true after the last attribute has been initialized.
        )

        # Item Cache
        self._cache: ItemCache = ItemCache(api)

        # Global/Internal API
        self.api = api
        # Logger
        self.logger = logging.getLogger()

        # Bootstrap rest of the properties
        if len(kwargs) > 0:
            self.from_dict(kwargs)
        if self._uid == "":
            self._uid = uuid.uuid4().hex

    def __eq__(self, other: Any) -> bool:
        """
        Comparison based on the uid for our items.

        :param other: The other Item to compare.
        :return: True if uid is equal, otherwise false.
        """
        if isinstance(other, BaseItem):
            return self._uid == other.uid
        return False

    def __hash__(self):
        """
        Hash table for Items.
        Requires special handling if the uid value changes and the Item
        is present in set, frozenset, and dict types.

        :return: hash(uid).
        """
        return hash(self._uid)

    @property
    def uid(self) -> str:
        """
        The uid is the internal unique representation of a Cobbler object. It should never be used twice, even after an
        object was deleted.

        :getter: The uid for the item. Should be unique across a running Cobbler instance.
        :setter: The new uid for the object. Should only be used by the Cobbler Item Factory.
        """
        return self._uid

    @uid.setter
    def uid(self, uid: str) -> None:
        """
        Setter for the uid of the item.

        :param uid: The new uid.
        """
        old_uid = self._uid
        self._uid = uid
        self.api.get_items(self.COLLECTION_TYPE).update_index_value(
            self, "uid", old_uid, uid
        )

    @property
    def ctime(self) -> float:
        """
        Property which represents the creation time of the object.

        :getter: The float which can be passed to Python time stdlib.
        :setter: Should only be used by the Cobbler Item Factory.
        """
        return self._ctime

    @ctime.setter
    def ctime(self, ctime: float) -> None:
        """
        Setter for the ctime property.

        :param ctime: The time the object was created.
        :raises TypeError: In case ``ctime`` was not of type float.
        """
        if not isinstance(ctime, float):  # type: ignore
            raise TypeError("ctime needs to be of type float")
        self._ctime = ctime

    @property
    def mtime(self) -> float:
        """
        Represents the last modification time of the object via the API. This is not updated automagically.

        :getter: The float which can be fed into a Python time object.
        :setter: The new time something was edited via the API.
        """
        return self._mtime

    @mtime.setter
    def mtime(self, mtime: float) -> None:
        """
        Setter for the modification time of the object.

        :param mtime: The new modification time.
        """
        if not isinstance(mtime, float):  # type: ignore
            raise TypeError("mtime needs to be of type float")
        self._mtime = mtime

    @property
    def name(self) -> str:
        """
        Property which represents the objects name.

        :getter: The name of the object.
        :setter: Updating this has broad implications. Please try to use the ``rename()`` functionality from the
                 corresponding collection.
        """
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        """
        The objects name.

        :param name: object name string
        :raises TypeError: In case ``name`` was not of type str.
        :raises ValueError: In case there were disallowed characters in the name.
        """
        if not isinstance(name, str):  # type: ignore
            raise TypeError("name must of be type str")
        if not RE_OBJECT_NAME.match(name):
            raise ValueError(f"Invalid characters in name: '{name}'")
        self._name = name

    @LazyProperty
    def comment(self) -> str:
        """
        For every object you are able to set a unique comment which will be persisted on the object.

        :getter: The comment or an emtpy string.
        :setter: The new comment for the item.
        """
        return self._comment

    @comment.setter
    def comment(self, comment: str) -> None:
        """
        Setter for the comment of the item.

        :param comment: The new comment. If ``None`` the comment will be set to an emtpy string.
        """
        self._comment = comment

    @InheritableProperty
    def owners(self) -> List[Any]:
        """
        This is a feature which is related to the ownership module of Cobbler which gives only specific people access
        to specific records. Otherwise this is just a cosmetic feature to allow assigning records to specific users.

        .. warning:: This is never validated against a list of existing users. Thus you can lock yourself out of a
                     record.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Return the list of users which are currently assigned to the record.
        :setter: The list of people which should be new owners. May lock you out if you are using the ownership
                 authorization module.
        """
        return self._resolve("owners")

    @owners.setter  # type: ignore[no-redef]
    def owners(self, owners: Union[str, List[Any]]):
        """
        Setter for the ``owners`` property.

        :param owners: The new list of owners. Will not be validated for existence.
        """
        if not isinstance(owners, (str, list)):  # type: ignore
            raise TypeError("owners must be str or list!")
        self._owners = self.api.input_string_or_list(owners)

    @property
    def inmemory(self) -> bool:
        r"""
        If set to ``false``, only the Item name is in memory. The rest of the Item's properties can be retrieved
        either on demand or as a result of the ``load_items`` background task.

        :getter: The inmemory for the item.
        :setter: The new inmemory value for the object. Should only be used by the Cobbler serializers.
        """
        return self._inmemory

    @inmemory.setter
    def inmemory(self, inmemory: bool):
        """
        Setter for the inmemory of the item.

        :param inmemory: The new inmemory value.
        """
        self._inmemory = inmemory

    @property
    def cache(self) -> ItemCache:
        """
        Getting the ItemCache object.

        .. note:: This is a read only property.

        :getter: This is the ItemCache object.
        """
        return self._cache

    def check_if_valid(self) -> None:
        """
        Raise exceptions if the object state is inconsistent.

        :raises CX: In case the name of the item is not set.
        """
        if not self.name:
            raise CX("Name is required")

    @abstractmethod
    def make_clone(self) -> "BaseItem":
        """
        Must be defined in any subclass
        """

    @abstractmethod
    def _resolve(self, property_name: str) -> Any:
        """
        Resolve the ``property_name`` value in the object tree. This function traverses the tree from the object to its
        topmost parent and returns the first value that is not inherited. If the tree does not contain a value the
        settings are consulted.

        Items that don't have the concept of Inheritance via parent objects may still inherit from the settings. It is
        the responsibility of the concrete class to implement the correct behavior.

        :param property_name: The property name to resolve.
        :raises AttributeError: In case one of the objects try to inherit from a parent that does not have
                                ``property_name``.
        :return: The resolved value.
        """
        raise NotImplementedError("Must be implemented in a specific Item")

    @classmethod
    def _remove_depreacted_dict_keys(cls, dictionary: Dict[Any, Any]) -> None:
        """
        This method does remove keys which should not be deserialized and are only there for API compatibility in
        :meth:`~cobbler.items.abstract.base_item.BaseItem.to_dict`.

        :param dictionary: The dict to update
        """
        if "ks_meta" in dictionary:
            dictionary.pop("ks_meta")
        if "kickstart" in dictionary:
            dictionary.pop("kickstart")
        if "children" in dictionary:
            dictionary.pop("children")

    def sort_key(self, sort_fields: List[Any]):
        """
        Convert the item to a dict and sort the data after specific given fields.

        :param sort_fields: The fields to sort the data after.
        :return: The sorted data.
        """
        data = self.to_dict()
        return [data.get(x, "") for x in sort_fields]

    def find_match(self, kwargs: Dict[str, Any], no_errors: bool = False) -> bool:
        """
        Find from a given dict if the item matches the kv-pairs.

        :param kwargs: The dict to match for in this item.
        :param no_errors: How strict this matching is.
        :return: True if matches or False if the item does not match.
        """
        # used by find() method in collection.py
        data = self.to_dict()
        for (key, value) in list(kwargs.items()):
            # Allow ~ to negate the compare
            if value is not None and value.startswith("~"):
                res = not self.find_match_single_key(data, key, value[1:], no_errors)
            else:
                res = self.find_match_single_key(data, key, value, no_errors)
            if not res:
                return False

        return True

    def find_match_single_key(
        self, data: Dict[str, Any], key: str, value: Any, no_errors: bool = False
    ) -> bool:
        """
        Look if the data matches or not. This is an alternative for ``find_match()``.

        :param data: The data to search through.
        :param key: The key to look for int the item.
        :param value: The value for the key.
        :param no_errors: How strict this matching is.
        :return: Whether the data matches or not.
        """
        # special case for systems
        key_found_already = False
        if "interfaces" in data:
            if key in [
                "cnames",
                "connected_mode",
                "if_gateway",
                "ipv6_default_gateway",
                "ipv6_mtu",
                "ipv6_prefix",
                "ipv6_secondaries",
                "ipv6_static_routes",
                "management",
                "mtu",
                "static",
                "mac_address",
                "ip_address",
                "ipv6_address",
                "netmask",
                "virt_bridge",
                "dhcp_tag",
                "dns_name",
                "static_routes",
                "interface_type",
                "interface_master",
                "bonding_opts",
                "bridge_opts",
                "interface",
            ]:
                key_found_already = True
                for (name, interface) in list(data["interfaces"].items()):
                    if value == name:
                        return True
                    if value is not None and key in interface:
                        if self.__find_compare(interface[key], value):
                            return True

        if key not in data:
            if not key_found_already:
                if not no_errors:
                    # FIXME: removed for 2.0 code, shouldn't cause any problems to not have an exception here?
                    # raise CX("searching for field that does not exist: %s" % key)
                    return False
            else:
                if value is not None:  # FIXME: new?
                    return False

        if value is None:
            return True
        return self.__find_compare(value, data[key])

    def serialize(self) -> Dict[str, Any]:
        """
        This method is a proxy for :meth:`~cobbler.items.abstract.base_item.BaseItem.to_dict` and contains additional
        logic for serialization to a persistent location.

        :return: The dictionary with the information for serialization.
        """
        keys_to_drop = [
            "kickstart",
            "ks_meta",
            "remote_grub_kernel",
            "remote_grub_initrd",
        ]
        result = self.to_dict()
        for key in keys_to_drop:
            result.pop(key, "")
        return result

    def deserialize(self) -> None:
        """
        Deserializes the object itself and, if necessary, recursively all the objects it depends on.
        """
        if not self._has_initialized:
            return

        item_dict = self.api.deserialize_item(self)
        self.from_dict(item_dict)

    def from_dict(self, dictionary: Dict[Any, Any]) -> None:
        """
        Modify this object to take on values in ``dictionary``.

        :param dictionary: This should contain all values which should be updated.
        :raises AttributeError: In case during the process of setting a value for an attribute an error occurred.
        :raises KeyError: In case there were keys which could not be set in the item dictionary.
        """
        self._remove_depreacted_dict_keys(dictionary)
        if len(dictionary) == 0:
            return
        old_has_initialized = self._has_initialized
        self._has_initialized = False
        result = copy.deepcopy(dictionary)
        for key in dictionary:
            lowered_key = key.lower()
            # The following also works for child classes because self is a child class at this point and not only an
            # Item.
            if hasattr(self, "_" + lowered_key):
                try:
                    setattr(self, lowered_key, dictionary[key])
                except AttributeError as error:
                    raise AttributeError(
                        f'Attribute "{lowered_key}" could not be set!'
                    ) from error
                result.pop(key)
        self._has_initialized = old_has_initialized
        self.clean_cache()
        if len(result) > 0:
            raise KeyError(
                f"The following keys supplied could not be set: {result.keys()}"
            )

    def to_dict(self, resolved: bool = False) -> Dict[Any, Any]:
        """
        This converts everything in this object to a dictionary.

        :param resolved: If this is True, Cobbler will resolve the values to its final form, rather than give you the
                     objects raw value.
        :return: A dictionary with all values present in this object.
        """
        if not self.inmemory:
            self.deserialize()
        cached_result = self.cache.get_dict_cache(resolved)
        if cached_result is not None:
            return cached_result

        value: Dict[str, Any] = {}
        for key, key_value in self.__dict__.items():
            if BaseItem._is_dict_key(key):
                new_key = key[1:].lower()
                if isinstance(key_value, enum.Enum):
                    if resolved:
                        value[new_key] = getattr(self, new_key).value
                    else:
                        value[new_key] = key_value.value
                elif new_key == "interfaces":
                    # This is the special interfaces dict. Let's fix it before it gets to the normal process.
                    serialized_interfaces = {}
                    interfaces = key_value
                    for interface_key in interfaces:
                        serialized_interfaces[interface_key] = interfaces[
                            interface_key
                        ].to_dict(resolved)
                    value[new_key] = serialized_interfaces
                elif isinstance(key_value, list):
                    value[new_key] = copy.deepcopy(key_value)  # type: ignore
                elif isinstance(key_value, dict):
                    if resolved:
                        value[new_key] = getattr(self, new_key)
                    else:
                        value[new_key] = copy.deepcopy(key_value)  # type: ignore
                elif (
                    isinstance(key_value, str)
                    and key_value == enums.VALUE_INHERITED
                    and resolved
                ):
                    value[new_key] = getattr(self, key[1:])
                else:
                    value[new_key] = key_value
        if "autoinstall" in value:
            value.update({"kickstart": value["autoinstall"]})  # type: ignore
        if "autoinstall_meta" in value:
            value.update({"ks_meta": value["autoinstall_meta"]})
        self.cache.set_dict_cache(value, resolved)
        return value

    def _clean_dict_cache(self, name: Optional[str]):
        """
        Clearing the Item dict cache.

        :param name: The name of Item attribute or None.
        """
        if not self.api.settings().cache_enabled:
            return

        # Invalidating the cache of the object itself.
        self.cache.clean_dict_cache()

    def clean_cache(self, name: Optional[str] = None):
        """
        Clearing the Item cache.

        :param name: The name of Item attribute or None.
        """
        if self._inmemory:
            self._clean_dict_cache(name)
