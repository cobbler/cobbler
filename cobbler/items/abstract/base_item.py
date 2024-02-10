"""
Cobbler module that contains the code for an abstract Cobbler item.

Changelog:

V3.4.0 (unreleased):
    * Introduced ``BaseItem``
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Enno Gotthold <egotthold@suse.com>

import copy
import enum
import fnmatch
import logging
import pprint
import re
import uuid
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from cobbler import enums, utils
from cobbler.cexceptions import CX
from cobbler.decorator import InheritableProperty, LazyProperty
from cobbler.items.abstract.item_cache import ItemCache
from cobbler.utils import input_converters

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.cobbler_collections.collection import ITEM


RE_OBJECT_NAME = re.compile(r"[a-zA-Z0-9_\-.:]*$")


class BaseItem:
    """
    A BaseItem is a serializable thing that can appear in a Collection
    """

    # Constants
    TYPE_NAME = "baseitem"
    COLLECTION_TYPE = "baseitem"

    @classmethod
    def _find_compare(
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

    @classmethod
    def _remove_depreacted_dict_keys(cls, dictionary: Dict[Any, Any]) -> None:
        """
        This method does remove keys which should not be deserialized and are only there for API compatibility in
        :meth:`~cobbler.items.item.Item.to_dict`.

        :param dictionary: The dict to update
        """

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any) -> None:
        """
        The keyword arguments are used to seed the object. This is the preferred way over ``from_dict`` starting with
        Cobbler version 3.4.0.

        :param api: The Cobbler API object which is used for resolving information.
        """
        # pylint: disable=unused-argument
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self.api = api
        self.logger = logging.getLogger()

        self._cache: ItemCache = ItemCache(api)

        self._ctime = 0.0
        self._mtime = 0.0
        self._uid = uuid.uuid4().hex
        self._name = ""
        self._comment = ""
        self._owners: Union[List[Any], str] = enums.VALUE_INHERITED
        self._inmemory = True

        if len(kwargs) > 0:
            self.from_dict(kwargs)
        if self._uid == "":
            self._uid = uuid.uuid4().hex

        if not self._has_initialized:
            self._has_initialized = True

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

    @abstractmethod
    def make_clone(self) -> "ITEM":  # type: ignore
        """
        Must be defined in any subclass
        """
        raise NotImplementedError("Must be implemented in a specific Item")

    @staticmethod
    def __is_dict_key(name: str) -> bool:
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

    def __setattr__(self, name: str, value: Any):
        """
        Intercepting an attempt to assign a value to an attribute.

        :name: The attribute name.
        :value: The attribute value.
        """
        if BaseItem.__is_dict_key(name) and self._has_initialized:
            self.clean_cache(name)
        super().__setattr__(name, value)

    def __common_resolve(self, property_name: str):
        settings_name = property_name
        if property_name.startswith("proxy_url_"):
            property_name = "proxy"
        elif property_name == "owners":
            settings_name = "default_ownership"
        attribute = "_" + property_name

        return getattr(self, attribute), settings_name

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
            settings = self.api.settings()
            possible_return = None
            if hasattr(settings, settings_name):
                possible_return = getattr(settings, settings_name)
            elif hasattr(settings, f"default_{settings_name}"):
                possible_return = getattr(settings, f"default_{settings_name}")

            if possible_return is not None:
                return possible_return
            raise AttributeError(
                f'{type(self)} "{self.name}" inherits property "{property_name}", but neither its parent nor'
                f" settings have it"
            )

        return attribute_value

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
        if self._uid != uid and self.COLLECTION_TYPE != BaseItem.COLLECTION_TYPE:
            name = self.name.lower()
            collection = self.api.get_items(self.COLLECTION_TYPE)
            with collection.lock:
                if collection.get(name) is not None:
                    # Changing the hash of an object requires special handling.
                    collection.listing.pop(name)
                    self._uid = uid
                    collection.listing[name] = self  # type: ignore
                    return
        self._uid = uid

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
        Gettinging the ItemCache oject.

        .. note:: This is a read only property.

        :getter: This is the ItemCache oject.
        """
        return self._cache

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
        self._owners = input_converters.input_string_or_list(owners)

    def check_if_valid(self) -> None:
        """
        Raise exceptions if the object state is inconsistent.

        :raises CX: In case the name of the item is not set.
        """
        if not self.name:
            raise CX("Name is required")

    def dump_vars(
        self, formatted_output: bool = True, remove_dicts: bool = False
    ) -> Union[Dict[str, Any], str]:
        """
        Dump all variables.

        :param formatted_output: Whether to format the output or not.
        :param remove_dicts: If True the dictionaries will be put into str form.
        :return: The raw or formatted data.
        """
        raw = utils.blender(self.api, remove_dicts, self)  # type: ignore
        if formatted_output:
            return pprint.pformat(raw)
        return raw

    def clean_cache(self, name: Optional[str] = None):
        """
        Clearing the Item cache.

        :param name: The name of Item attribute or None.
        """
        # Ignore unused argument to allow overriding this method for objects with inheritance.
        # pylint: disable=unused-argument
        if not self.api.settings().cache_enabled:
            return

        if not self._inmemory:
            # Don't attempt to invalidate a Cache that is not warmed up.
            return

        # Invalidating the cache of the object itself.
        self.cache.clean_dict_cache()

    def to_dict(self, resolved: bool = False) -> Dict[str, Any]:
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
            if self.__is_dict_key(key):
                new_key = key[1:].lower()
                if isinstance(key_value, enum.Enum):
                    if resolved:
                        value[new_key] = getattr(self, new_key).value
                    else:
                        value[new_key] = key_value.value
                elif new_key == "interfaces":
                    # This is the special interfaces dict. Lets fix it before it gets to the normal process.
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

    def from_dict(self, dictionary: Dict[str, Any]):
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

    def serialize(self) -> Dict[str, Any]:
        """
        This method is a proxy for :meth:`~cobbler.items.item.Item.to_dict` and contains additional logic for
        serialization to a persistent location.

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
        item_dict = self.api.deserialize_item(self)
        self.from_dict(item_dict)

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
        if key not in data:
            if not no_errors:
                # FIXME: removed for 2.0 code, shouldn't cause any problems to not have an exception here?
                # raise CX("searching for field that does not exist: %s" % key)
                return False

        if value is None:
            return True
        return self._find_compare(value, data[key])
