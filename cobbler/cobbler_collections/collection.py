"""
This module contains the code for the abstract base collection that powers all the other collections.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import logging
import os
import time
from abc import abstractmethod
from threading import Lock
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Set,
    TypeVar,
    Union,
)

from cobbler import enums, utils
from cobbler.cexceptions import CX
from cobbler.items import distro, image, menu, network_interface, profile, repo, system
from cobbler.items.abstract.base_item import BaseItem
from cobbler.items.abstract.inheritable_item import InheritableItem

if TYPE_CHECKING:
    from cobbler.actions.sync import CobblerSync
    from cobbler.api import CobblerAPI
    from cobbler.cobbler_collections.manager import CollectionManager


ITEM = TypeVar("ITEM", bound=BaseItem)
FIND_KWARGS = Union[  # pylint: disable=invalid-name
    str, int, bool, Dict[Any, Any], List[Any]
]


class Collection(Generic[ITEM]):
    """
    Base class for any serializable list of things.
    """

    def __init__(self, collection_mgr: "CollectionManager"):
        """
        Constructor.

        :param collection_mgr: The collection manager to resolve all information with.
        """
        self.collection_mgr = collection_mgr
        self.listing: Dict[str, ITEM] = {}
        self.api = self.collection_mgr.api
        self.__lite_sync: Optional["CobblerSync"] = None
        self.lock: Lock = Lock()
        self._inmemory: bool = not self.api.settings().lazy_start
        self._deserialize_running: bool = False
        # Secondary indexes for the collection.
        self.indexes: Dict[str, Dict[Union[str, int], Union[str, Set[str]]]] = {}
        self.init_indexes()
        self.logger = logging.getLogger()

    def __iter__(self) -> Iterator[ITEM]:
        """
        Iterator for the collection. Allows list comprehensions, etc.
        """
        for obj in list(self.listing.values()):
            yield obj

    def __len__(self) -> int:
        """
        Returns size of the collection.
        """
        return len(self.listing)

    @property
    def lite_sync(self) -> "CobblerSync":
        """
        Provide a ready to use CobblerSync object.

        :getter: Return the object that can update the filesystem state to a new one.
        """
        if self.__lite_sync is None:
            self.__lite_sync = self.api.get_sync()
        return self.__lite_sync

    @property
    def inmemory(self) -> bool:
        r"""
        If set to ``true``, then all items of the collection are loaded into memory.

        :getter: The inmemory for the collection.
        :setter: The new inmemory value for the collection.
        """
        return self._inmemory

    @inmemory.setter
    def inmemory(self, inmemory: bool):
        """
        Setter for the inmemory of the collection.

        :param inmemory: The new inmemory value.
        """
        self._inmemory = inmemory

    @property
    def deserialize_running(self) -> bool:
        r"""
        If set to ``true``, then the collection items are currently being loaded from disk.

        :getter: The deserialize_running for the collection.
        :setter: The new deserialize_running value for the collection.
        """
        return self._deserialize_running

    @deserialize_running.setter
    def deserialize_running(self, deserialize_running: bool):
        """
        Setter for the deserialize_running of the collection.

        :param deserialize_running: The new deserialize_running value.
        """
        self._deserialize_running = deserialize_running

    @abstractmethod
    def factory_produce(self, api: "CobblerAPI", seed_data: Dict[str, Any]) -> ITEM:
        """
        Must override in subclass. Factory_produce returns an Item object from dict.

        :param api: The API to resolve all information with.
        :param seed_data: Unused Parameter in the base collection.
        """

    def remove(
        self,
        ref: ITEM,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
        rebuild_menu: bool = True,
    ) -> None:
        """
        Remove an item from collection. This method must be overridden in any subclass.

        :param ref: The item to remove
        :param with_delete: sync and run triggers
        :param with_sync: sync to server file system
        :param with_triggers: run "on delete" triggers
        :param recursive: recursively delete children
        :param rebuild_menu: rebuild menu after removing the item
        :raises CX: In case any subitem (images, profiles or systems) would be orphaned. If the option ``recursive``
                    is set then the orphaned items would be removed automatically.
        """
        if ref is None:  # type: ignore
            raise CX("cannot delete an object that does not exist")

        for item_type in InheritableItem.TYPE_DEPENDENCIES[ref.COLLECTION_TYPE]:
            dep_type_items = self.api.find_items(
                item_type.dependant_item_type,
                {item_type.dependant_type_attribute: ref.uid},
                return_list=True,
            )
            if dep_type_items is None or not isinstance(dep_type_items, list):
                raise ValueError("Expected list to be returned by find_items")
            if len(dep_type_items) > 0:
                if recursive:
                    for dep_item in dep_type_items:
                        self.api.remove_item(
                            dep_item.COLLECTION_TYPE,
                            dep_item,
                            recursive=recursive,
                            delete=with_delete,
                            with_triggers=with_triggers,
                            with_sync=with_sync,
                        )
                else:
                    dep_str = ",".join([dep_item.uid for dep_item in dep_type_items])
                    raise CX(
                        f"removal would orphan {item_type.dependant_item_type}(s): {dep_str}"
                    )

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api,
                    ref,
                    f"/var/lib/cobbler/triggers/delete/{self.collection_type()}/pre/*",
                    [],
                )

        with self.lock:
            self.remove_from_indexes(ref)
            del self.listing[ref.uid]
        self.collection_mgr.serialize_delete(self, ref)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api,
                    ref,
                    f"/var/lib/cobbler/triggers/delete/{self.collection_type()}/post/*",
                    [],
                )
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/change/*", []
                )
            if with_sync:
                self.remove_quick_pxe_sync(ref, rebuild_menu=rebuild_menu)

    def remove_quick_pxe_sync(self, ref: ITEM, rebuild_menu: bool = True) -> None:
        """
        Execute the quick sync that is required after an item has been removed.

        .. note:: This method is for internal Cobbler use only.

        :param ref: The item to remove from the PXE tree
        :param rebuild_menu: If the menu hierarchy has to be rebuilt.
        """

    def get(self, name: str) -> Optional[ITEM]:
        """
        Return object with name in the collection

        :param name: The name of the object to retrieve from the collection.
        :return: The object if it exists. Otherwise, "None".
        """
        result = self.find(return_list=False, name=name)
        if isinstance(result, list):
            raise ValueError("Search result cannot be of type list.")
        return result

    def find(
        self,
        return_list: bool = False,
        no_errors: bool = False,
        **kwargs: FIND_KWARGS,
    ) -> Optional[Union[List[ITEM], ITEM]]:
        """
        Return first object in the collection that matches all item='value' pairs passed, else return None if no objects
        can be found. When return_list is set, can also return a list.  Empty list would be returned instead of None in
        that case.

        :param return_list: If a list should be returned or the first match.
        :param no_errors: If errors which are possibly thrown while searching should be ignored or not.
        :param kwargs: This dict needs to have one or more keys with search criteria. You may specify more keys to
                       narrow down the search.
        :return: The first item or a list with all matches.
        :raises ValueError: In case no arguments for searching were specified.
        """
        matches: List[ITEM] = []

        kwargs = self.__rekey(kwargs)

        # no arguments is an error, so we don't return a false match
        if len(kwargs) == 0:
            raise ValueError("calling find with no arguments")

        # performance: if the only key is name we can skip the whole loop
        if len(kwargs) == 1 and "uid" in kwargs and not return_list:
            return self.listing.get(kwargs["uid"], None)  # type: ignore

        if self.api.settings().lazy_start:
            # Forced deserialization of the entire collection to prevent deadlock in the search loop
            self._deserialize()

        with self.lock:
            orig_kargs_len = len(kwargs)
            result = self.find_by_indexes(kwargs)
            new_kwargs_len = len(kwargs)
            if new_kwargs_len > 0:
                obj_list: List[ITEM] = []
                if result is not None:
                    obj_list = result
                else:
                    if new_kwargs_len == orig_kargs_len:
                        obj_list = list(self)
                for obj in obj_list:
                    if obj.inmemory and obj.find_match(kwargs, no_errors=no_errors):
                        matches.append(obj)
            else:
                if result is not None:
                    matches = result

        if not return_list:
            if len(matches) == 0:
                return None
            return matches[0]
        return matches

    SEARCH_REKEY = {
        "kopts": "kernel_options",
        "kopts_post": "kernel_options_post",
        "inherit": "parent",
        "ip": "ipv4.address",
        "mac": "mac_address",
        "virt-auto-boot": "virt.auto_boot",
        "virt-file-size": "virt.file_size",
        "virt-disk-driver": "virt.disk_driver",
        "virt-ram": "virt.ram",
        "virt-path": "virt.path",
        "virt-type": "virt.type",
        "virt-bridge": "virt_bridge",
        "virt-cpus": "virt.cpus",
        "virt-host": "virt.host",
        "virt-group": "virt.group",
        "dhcp-tag": "dhcp_tag",
        "netboot-enabled": "netboot_enabled",
        "enable_gpxe": "enable_ipxe",
        "boot_loader": "boot_loaders",
    }

    def __rekey(self, _dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find calls from the command line ("cobbler system find") don't always match with the keys from the datastructs
        and this makes them both line up without breaking compatibility with either. Thankfully we don't have a LOT to
        remap.

        :param _dict: The dict which should be remapped.
        :return: The dict which can now be understood by the cli.
        """
        new_dict: Dict[str, Any] = {}
        for key in _dict.keys():
            if key in self.SEARCH_REKEY:
                newkey = self.SEARCH_REKEY[key]
                new_dict[newkey] = _dict[key]
            else:
                new_dict[key] = _dict[key]
        return new_dict

    def to_list(self) -> List[Dict[str, Any]]:
        """
        Serialize the collection

        :return: All elements of the collection as a list.
        """
        return [item_obj.to_dict() for item_obj in list(self.listing.values())]

    def from_list(self, _list: List[Dict[str, Any]]) -> None:
        """
        Create all collection object items from ``_list``.

        :param _list: The list with all item dictionaries.
        """
        if _list is None:  # type: ignore
            return
        for item_dict in _list:
            try:
                item = self.factory_produce(self.api, item_dict)
                self.add(item)
            except Exception as exc:
                self.logger.error(
                    "Error while loading a collection: %s. Skipping collection %s!",
                    exc,
                    self.collection_type(),
                )

    def copy(
        self,
        ref: ITEM,
        newname: str,
        with_sync: bool = True,
        with_triggers: bool = True,
    ):
        """
        Copy an object with a new name into the same collection.

        :param ref: The reference to the object which should be copied.
        :param newname: The new name for the copied object.
        :param with_sync: If a sync should be triggered when the object is copying.
        :param with_triggers: If triggers should be run when the object is copying.
        """
        copied_item: ITEM = ref.make_clone()  # type: ignore[assignment]
        copied_item.ctime = time.time()
        copied_item.name = newname
        # TODO: Check if uid is changing
        self.add(
            copied_item,
            save=True,
            with_copy=True,
            with_triggers=with_triggers,
            with_sync=with_sync,
            check_for_duplicate_names=True,
        )

    def rename(
        self,
        ref: "ITEM",
        newname: str,
    ):
        """
        Allows an object "ref" to be given a new name without affecting the rest of the object tree.

        :param ref: The reference to the object which should be renamed.
        :param newname: The new name for the object.
        """
        # Nothing to do when it is the same name
        if newname == ref.name:
            return

        # Save the old name
        oldname: str = ref.name
        # Change the name of the object
        ref.name = newname
        # Save just this item
        self.collection_mgr.serialize_one_item(ref)

        # for a repo, rename the mirror directory
        if isinstance(ref, repo.Repo):
            path = os.path.join(self.api.settings().webdir, "repo_mirror")
            old_path = os.path.join(path, oldname)
            if os.path.exists(old_path):
                new_path = os.path.join(path, ref.name)
                os.renames(old_path, new_path)

        # for a distro, rename the mirror and references to it
        if isinstance(ref, distro.Distro):
            path = ref.find_distro_path()  # type: ignore

            # create a symlink for the new distro name
            ref.link_distro()  # type: ignore

            # Test to see if the distro path is based directly on the name of the distro. If it is, things need to
            # updated accordingly.
            if os.path.exists(path) and path == str(
                os.path.join(self.api.settings().webdir, "distro_mirror", ref.name)
            ):
                newpath = os.path.join(
                    self.api.settings().webdir, "distro_mirror", ref.name
                )
                os.renames(path, newpath)

                # update any reference to this path ...
                distros = self.api.distros()
                for distro_obj in distros:
                    if distro_obj.kernel.find(path) == 0:
                        distro_obj.kernel = distro_obj.kernel.replace(path, newpath)
                        distro_obj.initrd = distro_obj.initrd.replace(path, newpath)
                        self.collection_mgr.serialize_one_item(distro_obj)

    def check_for_duplicate_names(self, ref: ITEM) -> None:
        """
        This method verified if the name of an object is a duplicate or not.

        :raises TypeError: In case the search result had an incorrect type.
        :raises CX: In case an item with that name already exists.
        """
        search_result = self.find(True, name=ref.name)
        if not isinstance(search_result, list):
            raise TypeError("Search result must be of type list!")
        if len(search_result) > 0:
            raise CX(
                f'An object with that name "{ref.name}" exists already. Try "edit"?'
            )

    def add(
        self,
        ref: ITEM,
        save: bool = False,
        with_copy: bool = False,
        with_triggers: bool = True,
        with_sync: bool = True,
        quick_pxe_update: bool = False,
        check_for_duplicate_names: bool = False,
        rebuild_menu: bool = True,
    ) -> None:
        """
        Add an object to the collection

        :param ref: The reference to the object.
        :param save: If this is true then the object is persisted on the disk.
        :param with_copy: Is a bit of a misnomer, but lots of internal add operations can run with "with_copy" as False.
                          True means a real final commit, as if entered from the command line (or basically, by a user).
                          With with_copy as False, the particular add call might just be being run during
                          deserialization, in which case extra semantics around the add don't really apply. So, in that
                          case, don't run any triggers and don't deal with any actual files.
        :param with_sync: If a sync should be triggered when the object is renamed.
        :param with_triggers: If triggers should be run when the object is added.
        :param quick_pxe_update: This decides if there should be run a quick or full update after the add was done.
        :param check_for_duplicate_names: If the name of an object should be unique or not.
        :raises TypError: Raised in case ``ref`` is None.
        :raises ValueError: Raised in case the name of ``ref`` is empty.
        """
        if ref is None:  # type: ignore
            raise TypeError("Unable to add a None object")

        ref.check_if_valid()

        if save:
            now = float(time.time())
            if ref.ctime == 0.0:
                ref.ctime = now
            ref.mtime = now

        # migration path for old API parameter that I've renamed.
        if with_copy and not save:
            save = with_copy

        if not save:
            # For people that aren't quite aware of the API if not saving the object, you can't run these features.
            with_triggers = False
            with_sync = False

        # Avoid adding objects to the collection with the same name
        if check_for_duplicate_names:
            self.check_for_duplicate_names(ref)

        if ref.COLLECTION_TYPE != self.collection_type():
            raise TypeError("API error: storing wrong data type in collection")

        # failure of a pre trigger will prevent the object from being added
        if save and with_triggers:
            utils.run_triggers(
                self.api,
                ref,
                f"/var/lib/cobbler/triggers/add/{self.collection_type()}/pre/*",
            )

        with self.lock:
            self.listing[ref.uid] = ref
            self.add_to_indexes(ref)

        # perform filesystem operations
        if save:
            # Save just this item if possible, if not, save the whole collection
            self.collection_mgr.serialize_one_item(ref)

            if with_sync:
                self.add_quick_pxe_sync(ref, rebuild_menu=rebuild_menu)
            if not with_sync and quick_pxe_update:
                if isinstance(ref, system.System):
                    self.lite_sync.update_system_netboot_status(ref)

            # save the tree, so if neccessary, scripts can examine it.
            if with_triggers:
                utils.run_triggers(
                    self.api, ref, "/var/lib/cobbler/triggers/change/*", []
                )
                utils.run_triggers(
                    self.api,
                    ref,
                    f"/var/lib/cobbler/triggers/add/{self.collection_type()}/post/*",
                    [],
                )

    def add_quick_pxe_sync(self, ref: ITEM, rebuild_menu: bool = True):
        """
        Execute the quick sync that is required after an item has been added.

        .. note:: This method is for internal Cobbler use only.

        :param ref: The item to add to the PXE tree
        :param rebuild_menu: If the menu hierarchy has to be rebuilt.
        """
        if isinstance(ref, system.System):
            # we don't need openvz containers to be network bootable
            if ref.virt.type == enums.VirtType.OPENVZ:
                ref.netboot_enabled = False
            self.lite_sync.add_single_system(ref)
        elif isinstance(ref, profile.Profile):
            # we don't need openvz containers to be network bootable
            if ref.virt.type == "openvz":  # type: ignore
                ref.enable_menu = False
            self.lite_sync.add_single_profile(ref, rebuild_menu=rebuild_menu)
            self.api.sync_systems(
                systems=[
                    x.uid  # type: ignore
                    for x in self.api.find_system(  # type: ignore
                        return_list=True,
                        no_errors=False,
                        **{"profile": ref.uid},
                    )
                ]  # type: ignore
            )
        elif isinstance(ref, distro.Distro):
            self.lite_sync.add_single_distro(ref, rebuild_menu=rebuild_menu)
        elif isinstance(ref, image.Image):
            self.lite_sync.add_single_image(ref, rebuild_menu=rebuild_menu)
        elif isinstance(ref, repo.Repo):
            pass
        elif isinstance(ref, menu.Menu):
            pass
        elif isinstance(ref, network_interface.NetworkInterface):
            pass
        else:
            self.logger.error(
                "Internal error. Object type not recognized: %s", type(ref)
            )

    def _deserialize(self) -> None:
        """
        Loading all collection items from disk in case of lazy start.
        """
        if self.inmemory or self.deserialize_running:
            # Preventing infinite recursion if a collection search is required when loading item properties.
            # Also prevents unnecessary looping through the collection if all items are already in memory.
            return

        self.deserialize_running = True
        for obj in self.listing.values():
            if not obj.inmemory:
                obj.deserialize()
        self.inmemory = True
        self.deserialize_running = False

    def init_indexes(self) -> None:
        """
        Initializing Indexes.
        """
        if self.collection_type() not in self.api.settings().memory_indexes:
            return
        for indx, indx_prop in (
            self.api.settings().memory_indexes[self.collection_type()].items()  # type: ignore
        ):
            if not indx_prop["disabled"]:
                self.indexes[indx] = {}

    def index_helper(
        self,
        ref: ITEM,
        index_name: str,
        index_key: Any,
        index_operation: Callable[
            [Union[str, int], str, Dict[Union[str, int], Union[str, Set[str]]], bool],
            None,
        ],
    ) -> None:
        """
        Add/Remove index entry.

        :param ref: The reference to the object.
        :param index_name: Index name.
        :param index_key: The Item attribute value.
        :param index_operation: Method for adding/removing an index entry.
        """
        key = index_key
        if key is None:
            key = ""
        indx_uniq: bool = self.api.settings().memory_indexes[self.collection_type()][  # type: ignore
            index_name
        ][
            "nonunique"
        ]
        indx_dict = self.indexes[index_name]
        item_uid = ref.uid
        if isinstance(key, (str, int)):
            index_operation(key, item_uid, indx_dict, indx_uniq)
        elif isinstance(key, (list, set, dict)):
            if len(key) == 0:  # type: ignore
                index_operation("", item_uid, indx_dict, indx_uniq)
            else:
                for k in key:  # type: ignore
                    if isinstance(k, (str, int)):
                        index_operation(k, item_uid, indx_dict, indx_uniq)
                    else:
                        raise CX(
                            f'Attribute type {key}({type(k)}) for "{item_uid}"'  # type: ignore
                            " cannot be used to create an index!"
                        )
        elif isinstance(key, enums.ConvertableEnum):
            index_operation(key.value, item_uid, indx_dict, indx_uniq)
        else:
            raise CX(
                f'Attribute type {type(key)} for "{item_uid}" cannot be used to create an index!'
            )

    def _get_index_property(self, ref: ITEM, index_name: str) -> str:
        """
        Retrieves the value of the index property for a given reference object based on the specified index name.

        The method determines the appropriate property name to access on the reference object, considering
        memory index settings, dot-separated index names, and fallback logic. If the property exists, its value
        is returned; otherwise, an exception is raised.

        :param ref: The reference object from which to retrieve the index property.
        :param index_name: The name of the index property, possibly dot-separated for nested properties.
        :returns: The value of the index property for the given reference object.
        :raises CX: If the property does not exist on the reference object.
        """
        indx_prop = self.api.settings().memory_indexes[self.collection_type()][  # type: ignore
            index_name
        ]
        split_property_name = index_name.split(".")
        if len(split_property_name) > 1:
            property_name: str = f"_{split_property_name[-1]}"
        else:
            property_name = f"_{index_name}"
        if "property" in indx_prop:
            property_name = indx_prop["property"]  # type: ignore
        elif not hasattr(ref, property_name) and len(split_property_name) == 1:
            property_name = index_name
        if len(split_property_name) > 1:
            return self.__get_index_property(ref, split_property_name)
        if hasattr(ref, property_name):
            return getattr(ref, property_name)
        raise CX(
            f'Internal error, unknown attribute "{property_name}" for "{ref.uid}"!'
        )

    def __get_index_property(self, ref: Any, property_name: List[str]) -> Any:
        """
        Recursively retrieves a nested property from an object using a list of property names.

        :param ref: The object from which to retrieve the property.
        :param property_name: A list of property names representing the path to the desired property.
        :return: The value of the nested property.
        """
        if len(property_name) > 1:
            local_property_name = property_name.pop(0)
            return self.__get_index_property(
                getattr(ref, local_property_name), property_name
            )
        return getattr(ref, property_name[0])

    def add_single_index_value(
        self,
        key: Union[str, int],
        value: str,
        indx_dict: Dict[Union[str, int], Union[str, Set[str]]],
        is_indx_nonunique: bool,
    ) -> None:
        """
        Add the single index value.
        """
        if is_indx_nonunique:
            if key in indx_dict:
                indx_dict[key].add(value)  # type: ignore
            else:
                indx_dict[key] = set([value])
        else:
            if key:
                indx_dict[key] = value

    def add_to_indexes(self, ref: ITEM) -> None:
        """
        Add indexes for the object.

        :param ref: The reference to the object whose indexes are updated.
        """
        for indx in self.indexes:
            if indx == "name" or ref.inmemory:
                self.index_helper(
                    ref,
                    indx,
                    self._get_index_property(ref, indx),
                    self.add_single_index_value,
                )

    def remove_single_index_value(
        self,
        key: Union[str, int],
        value: str,
        indx_dict: Dict[Union[str, int], Union[str, Set[str]]],
        is_indx_nonunique: bool,
    ) -> None:
        """
        Revove the single index value.
        """
        if is_indx_nonunique:
            if key in indx_dict and value in indx_dict[key]:
                indx_dict[key].remove(value)  # type: ignore
                if len(indx_dict[key]) == 0:
                    del indx_dict[key]
        else:
            indx_dict.pop(key, None)

    def remove_from_indexes(self, ref: ITEM) -> None:
        """
        Remove index keys for the object.

        :param ref: The reference to the object whose index keys are removed.
        """
        for indx in self.indexes:
            if indx == "uid" or ref.inmemory:
                self.index_helper(
                    ref,
                    indx,
                    self._get_index_property(ref, indx),
                    self.remove_single_index_value,
                )

    def update_index_value(
        self,
        ref: ITEM,
        attribute_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """
        Update index keys for the object.

        :param ref: The reference to the object whose index keys are updated.
        """
        if ref.in_transaction:
            # Don't update the index for items inside a transaction, this is done during the transaction commit.
            return
        if ref.uid in self.listing and attribute_name in self.indexes:
            with self.lock:
                self.index_helper(
                    ref,
                    attribute_name,
                    old_value,
                    self.remove_single_index_value,
                )
                self.index_helper(
                    ref,
                    attribute_name,
                    new_value,
                    self.add_single_index_value,
                )

    def find_by_indexes(self, kwargs: Dict[str, Any]) -> Optional[List[ITEM]]:
        """
        Searching for items in the collection by indexes.

        :param kwargs: The dict to match for the items.
        """

        def add_result(key: str, value: str, results: List[ITEM]) -> None:
            if value in self.listing:
                results.append(self.listing[value])
            else:
                self.logger.error(
                    'Internal error. The "%s" index for "%s" is corrupted.', key, value
                )

        result: Optional[List[ITEM]] = None
        found_keys: List[str] = []
        found: bool = True

        for key, value in kwargs.items():
            # fnmatch and "~" are not supported
            if (
                key not in self.indexes
                or value[:1] == "~"
                or "?" in value
                or "*" in value
                or "[" in value
            ):
                continue

            indx_dict = self.indexes[key]
            if value in indx_dict and found:
                if result is None:
                    result = []
                indx_val = indx_dict[value]
                result_len = len(result)
                if isinstance(indx_val, str):
                    if result_len > 0:
                        if self.listing[indx_val] not in result:
                            found = False
                    elif found:
                        add_result(key, indx_val, result)
                else:
                    if result_len > 0:
                        indx_set: Set[ITEM] = {self.listing[x] for x in indx_val}
                        result_set = set(result) & indx_set
                        if len(result_set) == 0:
                            found = False
                        else:
                            result = list(result_set)
                    elif found:
                        for obj_name in indx_val:
                            add_result(key, obj_name, result)
            else:
                found = False
            found_keys.append(key)

        for key in found_keys:
            kwargs.pop(key)
        if result is None or len(result) == 0 or not found:
            return None
        return result

    @staticmethod
    @abstractmethod
    def collection_type() -> str:
        """
        Returns the string key for the name of the collection (used by serializer etc)
        """

    @staticmethod
    @abstractmethod
    def collection_types() -> str:
        """
        Returns the string key for the plural name of the collection (used by serializer)
        """
