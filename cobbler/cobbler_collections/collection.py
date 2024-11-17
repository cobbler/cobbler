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
from cobbler.items import distro, image, menu, profile, repo, system
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
        return len(list(self.listing.values()))

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

    @abstractmethod
    def remove(
        self,
        name: str,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
    ) -> None:
        """
        Remove an item from collection. This method must be overridden in any subclass.

        :param name: Item Name
        :param with_delete: sync and run triggers
        :param with_sync: sync to server file system
        :param with_triggers: run "on delete" triggers
        :param recursive: recursively delete children
        :returns: NotImplementedError
        """

    def get(self, name: str) -> Optional[ITEM]:
        """
        Return object with name in the collection

        :param name: The name of the object to retrieve from the collection.
        :return: The object if it exists. Otherwise, "None".
        """
        return self.listing.get(name, None)

    def get_names(self) -> List[str]:
        """
        Return list of names in the collection.

        :return: list of names in the collection.
        """
        return list(self.listing)

    def find(
        self,
        name: str = "",
        return_list: bool = False,
        no_errors: bool = False,
        **kargs: FIND_KWARGS,
    ) -> Optional[Union[List[ITEM], ITEM]]:
        """
        Return first object in the collection that matches all item='value' pairs passed, else return None if no objects
        can be found. When return_list is set, can also return a list.  Empty list would be returned instead of None in
        that case.

        :param name: The object name which should be found.
        :param return_list: If a list should be returned or the first match.
        :param no_errors: If errors which are possibly thrown while searching should be ignored or not.
        :param kargs: If name is present, this is optional, otherwise this dict needs to have at least a key with
                      ``name``. You may specify more keys to finetune the search.
        :return: The first item or a list with all matches.
        :raises ValueError: In case no arguments for searching were specified.
        """
        matches: List[ITEM] = []

        if name:
            kargs["name"] = name

        kargs = self.__rekey(kargs)

        # no arguments is an error, so we don't return a false match
        if len(kargs) == 0:
            raise ValueError("calling find with no arguments")

        # performance: if the only key is name we can skip the whole loop
        if len(kargs) == 1 and "name" in kargs and not return_list:
            try:
                return self.listing.get(kargs["name"], None)  # type: ignore
            except Exception:
                return self.listing.get(name, None)

        if self.api.settings().lazy_start:
            # Forced deserialization of the entire collection to prevent deadlock in the search loop
            self._deserialize()

        with self.lock:
            orig_kargs_len = len(kargs)
            result = self.find_by_indexes(kargs)
            new_kargs_len = len(kargs)
            if new_kargs_len > 0:
                obj_list: List[ITEM] = []
                if result is not None:
                    obj_list = result
                else:
                    if new_kargs_len == orig_kargs_len:
                        obj_list = list(self)
                for obj in obj_list:
                    if obj.inmemory and obj.find_match(kargs, no_errors=no_errors):
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
        "ip": "ip_address",
        "mac": "mac_address",
        "virt-auto-boot": "virt_auto_boot",
        "virt-file-size": "virt_file_size",
        "virt-disk-driver": "virt_disk_driver",
        "virt-ram": "virt_ram",
        "virt-path": "virt_path",
        "virt-type": "virt_type",
        "virt-bridge": "virt_bridge",
        "virt-cpus": "virt_cpus",
        "virt-host": "virt_host",
        "virt-group": "virt_group",
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
        copied_item: ITEM = ref.make_clone()
        copied_item.ctime = time.time()
        copied_item.name = newname
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
        with_sync: bool = True,
        with_triggers: bool = True,
    ):
        """
        Allows an object "ref" to be given a new name without affecting the rest of the object tree.

        :param ref: The reference to the object which should be renamed.
        :param newname: The new name for the object.
        :param with_sync: If a sync should be triggered when the object is renamed.
        :param with_triggers: If triggers should be run when the object is renamed.
        """
        # Nothing to do when it is the same name
        if newname == ref.name:
            return

        # Save the old name
        oldname: str = ref.name
        with self.lock:
            # Delete the old item
            self.collection_mgr.serialize_delete_one_item(ref)
            self.remove_from_indexes(ref)
            self.listing.pop(oldname)
            # Change the name of the object
            ref.name = newname
            # Save just this item
            self.collection_mgr.serialize_one_item(ref)
            self.listing[newname] = ref
            self.add_to_indexes(ref)

        for dep_type in InheritableItem.TYPE_DEPENDENCIES[ref.COLLECTION_TYPE]:
            items = self.api.find_items(
                dep_type[0], {dep_type[1]: oldname}, return_list=True
            )
            if items is None:
                continue
            if not isinstance(items, list):
                raise ValueError("Unexepcted return value from find_items!")
            for item in items:
                attr = getattr(item, "_" + dep_type[1])
                if isinstance(attr, (str, BaseItem)):
                    setattr(item, dep_type[1], newname)
                elif isinstance(attr, list):
                    start_search = 0
                    for _ in range(attr.count(oldname)):  # type: ignore
                        offset = attr.index(oldname, start_search)  # type: ignore
                        attr[offset] = newname
                        start_search = offset + 1
                else:
                    raise CX(
                        f'Internal error, unknown attribute type {type(attr)} for "{item.name}"!'
                    )
                self.api.get_items(item.COLLECTION_TYPE).add(
                    item,  # type: ignore
                    save=True,
                    with_sync=with_sync,
                    with_triggers=with_triggers,
                )

        # for a repo, rename the mirror directory
        if isinstance(ref, repo.Repo):
            # if ref.COLLECTION_TYPE == "repo":
            path = os.path.join(self.api.settings().webdir, "repo_mirror")
            old_path = os.path.join(path, oldname)
            if os.path.exists(old_path):
                new_path = os.path.join(path, ref.name)
                os.renames(old_path, new_path)

        # for a distro, rename the mirror and references to it
        if isinstance(ref, distro.Distro):
            # if ref.COLLECTION_TYPE == "distro":
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

    def add(
        self,
        ref: ITEM,
        save: bool = False,
        with_copy: bool = False,
        with_triggers: bool = True,
        with_sync: bool = True,
        quick_pxe_update: bool = False,
        check_for_duplicate_names: bool = False,
    ) -> None:
        """
        Add an object to the collection

        :param ref: The reference to the object.
        :param save: If this is true then the objet is persisted on the disk.
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
            for item_obj in self.listing.values():
                if item_obj.name == ref.name:
                    raise CX(
                        f'An object with that name "{ref.name}" exists already. Try "edit"?'
                    )

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
            self.listing[ref.name] = ref
            self.add_to_indexes(ref)

        # perform filesystem operations
        if save:
            # Save just this item if possible, if not, save the whole collection
            self.collection_mgr.serialize_one_item(ref)

            if with_sync:
                if isinstance(ref, system.System):
                    # we don't need openvz containers to be network bootable
                    if ref.virt_type == enums.VirtType.OPENVZ:
                        ref.netboot_enabled = False
                    self.lite_sync.add_single_system(ref)
                elif isinstance(ref, profile.Profile):
                    # we don't need openvz containers to be network bootable
                    if ref.virt_type == "openvz":  # type: ignore
                        ref.enable_menu = False
                    self.lite_sync.add_single_profile(ref)
                    self.api.sync_systems(
                        systems=[
                            x.name  # type: ignore
                            for x in self.api.find_system(  # type: ignore
                                return_list=True,
                                no_errors=False,
                                **{"profile": ref.name},
                            )
                        ]  # type: ignore
                    )
                elif isinstance(ref, distro.Distro):
                    self.lite_sync.add_single_distro(ref)
                elif isinstance(ref, image.Image):
                    self.lite_sync.add_single_image(ref)
                elif isinstance(ref, repo.Repo):
                    pass
                elif isinstance(ref, menu.Menu):
                    pass
                else:
                    self.logger.error(
                        "Internal error. Object type not recognized: %s", type(ref)
                    )
            if not with_sync and quick_pxe_update:
                if isinstance(ref, system.System):
                    self.lite_sync.update_system_netboot_status(ref.name)

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

    def _deserialize(self) -> None:
        """
        Loading all collection items from disk in case of lazy start.
        """
        if self.inmemory or self.deserialize_running:
            # Preventing infinite recursion if a collection search is required when loading item properties.
            # Also prevents unnecessary looping through the collection if all items are already in memory.
            return

        self.deserialize_running = True
        for obj_name in self.get_names():
            obj = self.get(obj_name)
            if obj is not None and not obj.inmemory:
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
        item_name = ref.name
        if isinstance(key, (str, int)):
            index_operation(key, item_name, indx_dict, indx_uniq)
        elif isinstance(key, (list, set, dict)):
            if len(key) == 0:  # type: ignore
                index_operation("", item_name, indx_dict, indx_uniq)
            else:
                for k in key:  # type: ignore
                    if isinstance(k, (str, int)):
                        index_operation(k, item_name, indx_dict, indx_uniq)
                    else:
                        raise CX(
                            f'Attribute type {key}({type(k)}) for "{item_name}"'  # type: ignore
                            " cannot be used to create an index!"
                        )
        elif isinstance(key, enums.ConvertableEnum):
            index_operation(key.value, item_name, indx_dict, indx_uniq)
        else:
            raise CX(
                f'Attribute type {type(key)} for "{item_name}" cannot be used to create an index!'
            )

    def _get_index_property(self, ref: ITEM, index_name: str) -> str:
        indx_prop = self.api.settings().memory_indexes[self.collection_type()][  # type: ignore
            index_name
        ]
        property_name: str = f"_{index_name}"
        if "property" in indx_prop:
            property_name = indx_prop["property"]  # type: ignore
        elif not hasattr(ref, property_name):
            property_name = index_name
        if hasattr(ref, property_name):
            return getattr(ref, property_name)
        raise CX(
            f'Internal error, unknown attribute "{property_name}" for "{ref.name}"!'
        )

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
            if indx == "uid" or ref.inmemory:
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
        if ref.name in self.listing and attribute_name in self.indexes:
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

    def find_by_indexes(self, kargs: Dict[str, Any]) -> Optional[List[ITEM]]:
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

        for key, value in kargs.items():
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
            kargs.pop(key)
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
