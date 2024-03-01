"""
Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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
import logging
import time
import os
import uuid
from threading import Lock
from typing import List, Union

from cobbler import utils
from cobbler.items import package, system, item as item_base, image, profile, repo, mgmtclass, distro, file, menu

from cobbler.cexceptions import CX


class Collection:
    """
    Base class for any serializable list of things.
    """

    def __init__(self, collection_mgr):
        """
        Constructor.

        :param collection_mgr: The collection manager to resolve all information with.
        """
        self.collection_mgr = collection_mgr
        self.listing = {}
        self.api = self.collection_mgr.api
        self.lite_sync = None
        self.lock = Lock()
        self.logger = logging.getLogger()

    def __iter__(self):
        """
        Iterator for the collection. Allows list comprehensions, etc.
        """
        for a in list(self.listing.values()):
            yield a

    def __len__(self):
        """
        Returns size of the collection.
        """
        return len(list(self.listing.values()))

    def factory_produce(self, api, seed_data):
        """
        Must override in subclass. Factory_produce returns an Item object from dict.

        :param api: The API to resolve all information with.
        :param seed_data: Unused Parameter in the base collection.
        """
        raise NotImplementedError()

    def remove(self, name: str, with_delete: bool = True, with_sync: bool = True, with_triggers: bool = True,
               recursive: bool = False):
        """
        Remove an item from collection. This method must be overridden in any subclass.

        :param name: Item Name
        :param with_delete: sync and run triggers
        :param with_sync: sync to server file system
        :param with_triggers: run "on delete" triggers
        :param recursive: recursively delete children
        :returns: NotImplementedError
        """
        raise NotImplementedError("Please implement this in a child class of this class.")

    def get(self, name: str):
        """
        Return object with name in the collection

        :param name: The name of the object to retrieve from the collection.
        :return: The object if it exists. Otherwise None.
        """
        return self.listing.get(name.lower(), None)

    def get_names(self) -> List[str]:
        """
        Return list of names in the collection.
        :return: list of names in the collection.
        """
        return list(self.listing)
    
    def find(self, name: str = "", return_list: bool = False, no_errors=False,
             **kargs: dict) -> Union[List[item_base.Item], item_base.Item, None]:
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
        matches = []

        if name:
            kargs["name"] = name

        kargs = self.__rekey(kargs)

        # no arguments is an error, so we don't return a false match
        if len(kargs) == 0:
            raise ValueError("calling find with no arguments")

        # performance: if the only key is name we can skip the whole loop
        if len(kargs) == 1 and "name" in kargs and not return_list:
            try:
                return self.listing.get(kargs["name"].lower(), None)
            except:
                return self.listing.get(kargs["name"], None)

        if self.api.settings().lazy_start:
            # Forced deserialization of the entire collection to prevent deadlock in the search loop
            for obj_name in self.get_names():
                obj = self.get(obj_name)
                if obj is not None and not obj.inmemory:
                    obj.deserialize()

        self.lock.acquire()
        try:
            for obj in self:
                if obj.find_match(kargs, no_errors=no_errors):
                    matches.append(obj)
        finally:
            self.lock.release()

        if not return_list:
            if len(matches) == 0:
                return None
            return matches[0]
        else:
            return matches

    SEARCH_REKEY = {
        'kopts': 'kernel_options',
        'kopts_post': 'kernel_options_post',
        'inherit': 'parent',
        'ip': 'ip_address',
        'mac': 'mac_address',
        'virt-auto-boot': 'virt_auto_boot',
        'virt-file-size': 'virt_file_size',
        'virt-disk-driver': 'virt_disk_driver',
        'virt-ram': 'virt_ram',
        'virt-path': 'virt_path',
        'virt-type': 'virt_type',
        'virt-bridge': 'virt_bridge',
        'virt-cpus': 'virt_cpus',
        'virt-host': 'virt_host',
        'virt-group': 'virt_group',
        'dhcp-tag': 'dhcp_tag',
        'netboot-enabled': 'netboot_enabled',
        'enable_gpxe': 'enable_ipxe',
        'boot_loader': 'boot_loaders',
    }

    def __rekey(self, _dict: dict) -> dict:
        """
        Find calls from the command line ("cobbler system find") don't always match with the keys from the datastructs
        and this makes them both line up without breaking compatibility with either. Thankfully we don't have a LOT to
        remap.

        :param _dict: The dict which should be remapped.
        :return: The dict which can now be understood by the cli.
        """
        new_dict = {}
        for x in list(_dict.keys()):
            if x in self.SEARCH_REKEY:
                newkey = self.SEARCH_REKEY[x]
                new_dict[newkey] = _dict[x]
            else:
                new_dict[x] = _dict[x]
        return new_dict

    def to_list(self) -> list:
        """
        Serialize the collection

        :return: All elements of the collection as a list.
        """
        return [x.to_dict() for x in list(self.listing.values())]

    def from_list(self, _list: list):
        """
        Create all collection object items from ``_list``.

        :param _list: The list with all item dictionaries.
        """
        if _list is None:
            return
        for item_dict in _list:
            item = self.factory_produce(self.api, item_dict)
            self.add(item)

    def copy(self, ref, newname):
        """
        Copy an object with a new name into the same collection.

        :param ref: The reference to the object which should be copied.
        :param newname: The new name for the copied object.
        """
        copied_item = ref.make_clone()
        copied_item.uid = uuid.uuid4().hex
        copied_item.ctime = time.time()
        copied_item.name = newname
        if copied_item.COLLECTION_TYPE == "system":
            # this should only happen for systems
            for interface in copied_item.interfaces:
                # clear all these out to avoid DHCP/DNS conflicts
                copied_item.interfaces[interface].dns_name = ""
                copied_item.interfaces[interface].mac_address = ""
                copied_item.interfaces[interface].ip_address = ""

        self.add(
            copied_item,
            save=True,
            with_copy=True,
            with_triggers=True,
            with_sync=True,
            check_for_duplicate_names=True
        )

    def rename(self, ref: item_base.Item, newname, with_sync: bool = True, with_triggers: bool = True):
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
        oldname = ref.name
        # Reserve the new name
        self.listing[newname] = None
        # Delete the old item
        self.collection_mgr.serialize_delete_one_item(ref)
        self.listing.pop(oldname)
        # Change the name of the object
        ref.name = newname
        # Save just this item
        self.collection_mgr.serialize_one_item(ref)
        self.listing[newname] = ref

        # for mgmt classes, update all objects that use it
        if ref.COLLECTION_TYPE == "mgmtclass":
            for what in ["distro", "profile", "system"]:
                items = self.api.find_items(what, {"mgmt_classes": oldname})
                for item in items:
                    for i in range(0, len(item.mgmt_classes)):
                        if item.mgmt_classes[i] == oldname:
                            item.mgmt_classes[i] = newname
                    self.api.add_item(what, item, save=True)

        # for menus, update all objects that use it
        if ref.COLLECTION_TYPE == "menu":
            for what in ["profile", "image"]:
                items = self.api.find_items(what, {"menu": oldname})
                for item in items:
                    item.menu = newname
                    self.api.add_item(what, item, save=True)

        # for a repo, rename the mirror directory
        if ref.COLLECTION_TYPE == "repo":
            path = os.path.join(self.api.settings().webdir, "repo_mirror")
            old_path = os.path.join(path, oldname)
            if os.path.exists(old_path):
                new_path = os.path.join(path, ref.name)
                os.renames(old_path, new_path)

        # for a distro, rename the mirror and references to it
        if ref.COLLECTION_TYPE == 'distro':
            path = utils.find_distro_path(self.api.settings(), ref)

            # create a symlink for the new distro name
            utils.link_distro(self.api.settings(), ref)

            # Test to see if the distro path is based directly on the name of the distro. If it is, things need to
            # updated accordingly.
            if os.path.exists(path) \
                    and path == str(os.path.join(self.api.settings().webdir, "distro_mirror", ref.name)):
                newpath = os.path.join(self.api.settings().webdir, "distro_mirror", ref.name)
                os.renames(path, newpath)

                # update any reference to this path ...
                distros = self.api.distros()
                for d in distros:
                    if d.kernel.find(path) == 0:
                        d.kernel = d.kernel.replace(path, newpath)
                        d.initrd = d.initrd.replace(path, newpath)
                        self.collection_mgr.serialize_one_item(d)

        if ref.COLLECTION_TYPE in ('profile', 'system'):
            if ref.parent is not None:
                ref.parent.children.remove(oldname)

        # Now descend to any direct ancestors and point them at the new object allowing the original object to be
        # removed without orphanage. Direct ancestors will either be profiles or systems. Note that we do have to
        # care as setting the parent is only really meaningful for subprofiles. We ideally want a more generic parent
        # setter.
        kids = ref.get_children()
        for k in kids:
            if self.api.find_profile(name=k) is not None:
                k = self.api.find_profile(name=k)
                if ref.COLLECTION_TYPE == "distro":
                    k.distro = newname
                else:
                    k.parent = newname
                self.api.profiles().add(k, save=True, with_sync=with_sync, with_triggers=with_triggers)
            elif self.api.find_menu(name=k) is not None:
                k = self.api.find_menu(name=k)
                k.parent = newname
                self.api.menus().add(k, save=True, with_sync=with_sync, with_triggers=with_triggers)
            elif self.api.find_system(name=k) is not None:
                k = self.api.find_system(name=k)
                k.profile = newname
                self.api.systems().add(k, save=True, with_sync=with_sync, with_triggers=with_triggers)
            else:
                raise CX("Internal error, unknown child type for child \"%s\"!" % k)

    def add(self, ref, save: bool = False, with_copy: bool = False, with_triggers: bool = True, with_sync: bool = True,
            quick_pxe_update: bool = False, check_for_duplicate_names: bool = False):
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
        if ref is None:
            raise TypeError("Unable to add a None object")

        ref.check_if_valid()

        if ref.uid == '':
            ref.uid = uuid.uuid4().hex

        if save:
            now = float(time.time())
            if ref.ctime == 0.0:
                ref.ctime = now
            ref.mtime = now

        if self.lite_sync is None:
            self.lite_sync = self.api.get_sync()

        # migration path for old API parameter that I've renamed.
        if with_copy and not save:
            save = with_copy

        if not save:
            # For people that aren't quite aware of the API if not saving the object, you can't run these features.
            with_triggers = False
            with_sync = False

        # Avoid adding objects to the collection with the same name
        if check_for_duplicate_names:
            for item in self.listing.values():
                if item.name == ref.name:
                    raise CX("An object already exists with that name. Try 'edit'?")

        if ref.COLLECTION_TYPE != self.collection_type():
            raise TypeError("API error: storing wrong data type in collection")

        # failure of a pre trigger will prevent the object from being added
        if save and with_triggers:
            utils.run_triggers(self.api, ref, "/var/lib/cobbler/triggers/add/%s/pre/*" % self.collection_type())

        self.lock.acquire()
        try:
            self.listing[ref.name.lower()] = ref
        finally:
            self.lock.release()

        # perform filesystem operations
        if save:
            # Save just this item if possible, if not, save the whole collection
            self.collection_mgr.serialize_one_item(ref)
            if ref.parent:
                self.collection_mgr.serialize_one_item(ref.parent)

            if with_sync:
                if isinstance(ref, system.System):
                    # we don't need openvz containers to be network bootable
                    if ref.virt_type == "openvz":
                        ref.netboot_enabled = False
                    self.lite_sync.add_single_system(ref.name)
                    self.api.sync_systems(systems=[ref.name])
                elif isinstance(ref, profile.Profile):
                    # we don't need openvz containers to be network bootable
                    if ref.virt_type == "openvz":
                        ref.enable_menu = False
                    self.lite_sync.add_single_profile(ref.name)
                    self.api.sync_systems(systems=ref.get_children())
                elif isinstance(ref, distro.Distro):
                    self.lite_sync.add_single_distro(ref.name)
                elif isinstance(ref, image.Image):
                    self.lite_sync.add_single_image(ref.name)
                elif isinstance(ref, repo.Repo):
                    pass
                elif isinstance(ref, mgmtclass.Mgmtclass):
                    pass
                elif isinstance(ref, package.Package):
                    pass
                elif isinstance(ref, file.File):
                    pass
                elif isinstance(ref, menu.Menu):
                    pass
                else:
                    print("Internal error. Object type not recognized: %s" % type(ref))
            if not with_sync and quick_pxe_update:
                if isinstance(ref, system.System):
                    self.lite_sync.update_system_netboot_status(ref.name)

            # save the tree, so if neccessary, scripts can examine it.
            if with_triggers:
                utils.run_triggers(self.api, ref, "/var/lib/cobbler/triggers/change/*", [])
                utils.run_triggers(self.api, ref, "/var/lib/cobbler/triggers/add/%s/post/*" % self.collection_type(),
                                   [])

    def to_string(self) -> str:
        """
        Creates a printable representation of the collection suitable for reading by humans or parsing from scripts.
        Actually scripts would be better off reading the JSON in the cobbler_collections files directly.

        :return: The object as a string representation.
        """
        # FIXME: No to_string() method in any of the items present!
        values = list(self.listing.values())[:]   # copy the values
        values.sort()                       # sort the copy (2.3 fix)
        results = []
        for i, v in enumerate(values):
            results.append(v.to_string())
        if len(values) > 0:
            return "\n\n".join(results)
        else:
            return "No objects found"

    @staticmethod
    def collection_type() -> str:
        """
        Returns the string key for the name of the collection (used by serializer etc)
        """
        raise NotImplementedError("Please implement the method \"collection_type\" in your Collection!")

    @staticmethod
    def collection_types() -> str:
        """
        Returns the string key for the plural name of the collection (used by serializer)
        """
        raise NotImplementedError("Please implement the method \"collection_types\" in your Collection!")
