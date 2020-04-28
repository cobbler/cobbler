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

from builtins import range
from builtins import object
from cobbler import utils
import time
import os
from threading import Lock

from cobbler.actions import litesync
from cobbler.items import package, system, item as item_base, image, profile, repo, mgmtclass, distro, file

from cobbler.utils import _
from cobbler.cexceptions import CX, NotImplementedException


class Collection(object):
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

    def factory_produce(self, collection_mgr, seed_data):
        """
        Must override in subclass. Factory_produce returns an Item object from dict.

        :param collection_mgr: The collection manager to resolve all information with.
        :param seed_data:
        """
        raise NotImplementedException()

    def remove(self, name, with_delete=True, with_sync=True, with_triggers=True, recursive=False, logger=None):
        """
        Remove an item from collection. This method must be overriden in any subclass.

        :param name: (item name)
        :type name: str
        :param with_delete: (sync and run triggers)
        :type with_delete: bool
        :param with_sync: (sync to server file system)
        :type with_sync: bool
        :param with_triggers: (run "on delete" triggers)
        :type with_triggers: bool
        :param recursive: (recursively delete children)
        :type recursive: bool
        :param logger: (logger object)
        :returns: NotImplementedException
        """
        raise NotImplementedException()

    def get(self, name):
        """
        Return object with name in the collection

        :param name: The name of the object to retrieve from the collection.
        :return: The object if it exists. Otherwise None.
        """
        return self.listing.get(name.lower(), None)

    def find(self, name=None, return_list=False, no_errors=False, **kargs):
        """
        Return first object in the collection that maches all item='value' pairs passed, else return None if no objects
        can be found. When return_list is set, can also return a list.  Empty list would be returned instead of None in
        that case.

        :param name: The object name which should be found.
        :type name: str
        :param return_list: If a list should be returned or the first match.
        :param no_errors: If errors which are possibly thrown while searching should be ignored or not.
        :param kargs: If name is present, this is optional, otherwise this dict needs to have at least a key with
                      ``name``. You may specify more keys to finetune the search.
        :type kargs: dict
        :return: The first item or a list with all matches.
        """
        matches = []

        # support the old style innovation without kwargs
        if name is not None:
            kargs["name"] = name

        kargs = self.__rekey(kargs)

        # no arguments is an error, so we don't return a false match
        if len(kargs) == 0:
            raise CX(_("calling find with no arguments"))

        # performance: if the only key is name we can skip the whole loop
        if len(kargs) == 1 and "name" in kargs and not return_list:
            try:
                return self.listing.get(kargs["name"].lower(), None)
            except:
                return self.listing.get(kargs["name"], None)

        self.lock.acquire()
        try:
            for (name, obj) in list(self.listing.items()):
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
    }

    def __rekey(self, _dict):
        """
        Find calls from the command line ("cobbler system find") don't always match with the keys from the datastructs
        and this makes them both line up without breaking compatibility with either. Thankfully we don't have a LOT to
        remap.

        :param _dict: The dict which should be remapped.
        :return: The dict which can now be understood by the cli.
        :rtype: dict
        """
        new_dict = {}
        for x in list(_dict.keys()):
            if x in self.SEARCH_REKEY:
                newkey = self.SEARCH_REKEY[x]
                new_dict[newkey] = _dict[x]
            else:
                new_dict[x] = _dict[x]
        return new_dict

    def to_list(self):
        """
        Serialize the collection

        :rtype: list
        :return: All elements of the collection as a list.
        """
        _list = [x.to_dict() for x in list(self.listing.values())]
        return _list

    def from_list(self, _list):
        """
        Create all collection object items from ``_list``.

        :param _list: The list with all item dictionaries.
        :type _list: list
        """
        if _list is None:
            return
        for item_dict in _list:
            item = self.factory_produce(self.collection_mgr, item_dict)
            self.add(item)

    def copy(self, ref, newname, logger=None):
        """
        Copy an object with a new name into the same collection.

        :param ref: The reference to the object which should be copied.
        :param newname: The new name for the copied object.
        :param logger: This parameter is unused in this implementation.
        """
        ref = ref.make_clone()
        ref.uid = self.collection_mgr.generate_uid()
        ref.ctime = 0
        ref.set_name(newname)
        if ref.COLLECTION_TYPE == "system":
            # this should only happen for systems
            for iname in list(ref.interfaces.keys()):
                # clear all these out to avoid DHCP/DNS conflicts
                ref.set_dns_name("", iname)
                ref.set_mac_address("", iname)
                ref.set_ip_address("", iname)

        self.add(
            ref, save=True, with_copy=True, with_triggers=True, with_sync=True,
            check_for_duplicate_names=True, check_for_duplicate_netinfo=False)

    def rename(self, ref, newname, with_sync=True, with_triggers=True, logger=None):
        """
        Allows an object "ref" to be given a newname without affecting the rest of the object tree.

        :param ref: The reference to the object which should be renamed.
        :param newname: The new name for the object.
        :param with_sync: If a sync should be triggered when the object is renamed.
        :param with_triggers: If triggers should be run when the object is renamed.
        :param logger: The logger to audit the action with.
        """
        # Nothing to do when it is the same name
        if newname == ref.name:
            return

        # make a copy of the object, but give it a new name.
        oldname = ref.name
        newref = ref.make_clone()
        newref.set_name(newname)

        self.add(newref, with_triggers=with_triggers, save=True)

        # for mgmt classes, update all objects that use it
        if ref.COLLECTION_TYPE == "mgmtclass":
            for what in ["distro", "profile", "system"]:
                items = self.api.find_items(what, {"mgmt_classes": oldname})
                for item in items:
                    for i in range(0, len(item.mgmt_classes)):
                        if item.mgmt_classes[i] == oldname:
                            item.mgmt_classes[i] = newname
                    self.api.add_item(what, item, save=True)

        # for a repo, rename the mirror directory
        if ref.COLLECTION_TYPE == "repo":
            path = "/var/www/cobbler/repo_mirror/%s" % ref.name
            if os.path.exists(path):
                newpath = "/var/www/cobbler/repo_mirror/%s" % newref.name
                os.renames(path, newpath)

        # for a distro, rename the mirror and references to it
        if ref.COLLECTION_TYPE == 'distro':
            path = utils.find_distro_path(self.api.settings(), ref)

            # create a symlink for the new distro name
            utils.link_distro(self.api.settings(), newref)

            # Test to see if the distro path is based directly on the name of the distro. If it is, things need to
            # updated accordingly.
            if os.path.exists(path) and path == "/var/www/cobbler/distro_mirror/%s" % ref.name:
                newpath = "/var/www/cobbler/distro_mirror/%s" % newref.name
                os.renames(path, newpath)

                # update any reference to this path ...
                distros = self.api.distros()
                for d in distros:
                    if d.kernel.find(path) == 0:
                        d.set_kernel(d.kernel.replace(path, newpath))
                        d.set_initrd(d.initrd.replace(path, newpath))
                        self.collection_mgr.serialize_item(self, d)

        # Now descend to any direct ancestors and point them at the new object allowing the original object to be
        # removed without orphanage. Direct ancestors will either be profiles or systems. Note that we do have to
        # care as set_parent is only really meaningful for subprofiles. We ideally want a more generic set_parent.
        kids = ref.get_children()
        for k in kids:
            if k.COLLECTION_TYPE == "distro":
                raise CX(_("internal error, not expected to have distro child objects"))
            elif k.COLLECTION_TYPE == "profile":
                if k.parent != "":
                    k.set_parent(newname)
                else:
                    k.set_distro(newname)
                self.api.profiles().add(k, save=True, with_sync=with_sync, with_triggers=with_triggers)
            elif k.COLLECTION_TYPE == "system":
                k.set_profile(newname)
                self.api.systems().add(k, save=True, with_sync=with_sync, with_triggers=with_triggers)
            elif k.COLLECTION_TYPE == "repo":
                raise CX(_("internal error, not expected to have repo child objects"))
            else:
                raise CX(_("internal error, unknown child type (%s), cannot finish rename" % k.COLLECTION_TYPE))

        # now delete the old version
        self.remove(oldname, with_delete=True, with_triggers=with_triggers)
        return

    def add(self, ref, save=False, with_copy=False, with_triggers=True, with_sync=True, quick_pxe_update=False,
            check_for_duplicate_names=False, check_for_duplicate_netinfo=False, logger=None):
        """
        Add an object to the collection

        :param ref: The reference to the object.
        :param save: If this is true then the objet is persited on the disk.
        :param with_copy: Is a bit of a misnomer, but lots of internal add operations can run with "with_copy" as False.
                          True means a real final commit, as if entered from the command line (or basically, by a user).
                          With with_copy as False, the particular add call might just be being run during
                          deserialization, in which case extra semantics around the add don't really apply. So, in that
                          case, don't run any triggers and don't deal with any actual files.
        :param with_sync: If a sync should be triggered when the object is renamed.
        :param with_triggers: If triggers should be run when the object is renamed.
        :param quick_pxe_update: This decides if there should be run a quick or full update after the add was done.
        :param check_for_duplicate_names: If the name of an object should be unique or not.
        :type check_for_duplicate_names: bool
        :param check_for_duplicate_netinfo: This checks for duplicate network information. This only has an effect on
                                            systems.
        :type check_for_duplicate_netinfo: bool
        :param logger: The logger to audit the action with.
        """
        item_base.Item.remove_from_cache(ref)
        if ref is None:
            raise CX("Unable to add a None object")
        if ref.name is None:
            raise CX("Unable to add an object without a name")

        ref.check_if_valid()

        if ref.uid == '':
            ref.uid = self.collection_mgr.generate_uid()

        if save is True:
            now = time.time()
            if ref.ctime == 0:
                ref.ctime = now
            ref.mtime = now

        if self.lite_sync is None:
            self.lite_sync = litesync.CobblerLiteSync(self.collection_mgr, logger=logger)

        # migration path for old API parameter that I've renamed.
        if with_copy and not save:
            save = with_copy

        if not save:
            # For people that aren't quite aware of the API if not saving the object, you can't run these features.
            with_triggers = False
            with_sync = False

        # Avoid adding objects to the collection if an object of the same/ip/mac already exists.
        self.__duplication_checks(ref, check_for_duplicate_names, check_for_duplicate_netinfo)

        if ref.COLLECTION_TYPE != self.collection_type():
            raise CX(_("API error: storing wrong data type in collection"))

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
            self.collection_mgr.serialize_item(self, ref)

            if with_sync:
                if isinstance(ref, system.System):
                    # we don't need openvz containers to be network bootable
                    if ref.virt_type == "openvz":
                        ref.netboot_enabled = False
                    self.lite_sync.add_single_system(ref.name)
                elif isinstance(ref, profile.Profile):
                    # we don't need openvz containers to be network bootable
                    if ref.virt_type == "openvz":
                        ref.enable_menu = 0
                    self.lite_sync.add_single_profile(ref.name)
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
                else:
                    print(_("Internal error. Object type not recognized: %s") % type(ref))
            if not with_sync and quick_pxe_update:
                if isinstance(ref, system.System):
                    self.lite_sync.update_system_netboot_status(ref.name)

            # save the tree, so if neccessary, scripts can examine it.
            if with_triggers:
                utils.run_triggers(self.api, ref, "/var/lib/cobbler/triggers/change/*", [], logger)
                utils.run_triggers(self.api, ref, "/var/lib/cobbler/triggers/add/%s/post/*" % self.collection_type(), [], logger)

        # update children cache in parent object
        parent = ref.get_parent()
        if parent is not None:
            parent.children[ref.name] = ref

    def __duplication_checks(self, ref, check_for_duplicate_names, check_for_duplicate_netinfo):
        """
        Prevents adding objects with the same name. Prevents adding or editing to provide the same IP, or MAC.
        Enforcement is based on whether the API caller requests it.

        :param ref: The refernce to the object.
        :param check_for_duplicate_names: If the name of an object should be unique or not.
        :type check_for_duplicate_names: bool
        :param check_for_duplicate_netinfo: This checks for duplicate network information. This only has an effect on
                                            systems.
        :type check_for_duplicate_netinfo: bool
        :raises CX: If a duplicate is found
        """
        # ToDo: Use return bool type to indicate duplicates and only throw CX in real error case.
        # always protect against duplicate names
        if check_for_duplicate_names:
            match = None
            if isinstance(ref, system.System):
                match = self.api.find_system(ref.name)
            elif isinstance(ref, profile.Profile):
                match = self.api.find_profile(ref.name)
            elif isinstance(ref, distro.Distro):
                match = self.api.find_distro(ref.name)
            elif isinstance(ref, repo.Repo):
                match = self.api.find_repo(ref.name)
            elif isinstance(ref, image.Image):
                match = self.api.find_image(ref.name)
            elif isinstance(ref, mgmtclass.Mgmtclass):
                match = self.api.find_mgmtclass(ref.name)
            elif isinstance(ref, package.Package):
                match = self.api.find_package(ref.name)
            elif isinstance(ref, file.File):
                match = self.api.find_file(ref.name)
            else:
                raise CX("internal error, unknown object type")

            if match:
                raise CX(_("An object already exists with that name.  Try 'edit'?"))

        # the duplicate mac/ip checks can be disabled.
        if not check_for_duplicate_netinfo:
            return

        if isinstance(ref, system.System):
            for (name, intf) in list(ref.interfaces.items()):
                match_ip = []
                match_mac = []
                match_hosts = []
                input_mac = intf["mac_address"]
                input_ip = intf["ip_address"]
                input_dns = intf["dns_name"]
                if not self.api.settings().allow_duplicate_macs and input_mac is not None and input_mac != "":
                    match_mac = self.api.find_system(mac_address=input_mac, return_list=True)
                if not self.api.settings().allow_duplicate_ips and input_ip is not None and input_ip != "":
                    match_ip = self.api.find_system(ip_address=input_ip, return_list=True)
                # it's ok to conflict with your own net info.

                if not self.api.settings().allow_duplicate_hostnames and input_dns is not None and input_dns != "":
                    match_hosts = self.api.find_system(dns_name=input_dns, return_list=True)

                for x in match_mac:
                    if x.name != ref.name:
                        raise CX(_("Can't save system %s. The MAC address (%s) is already used by system %s (%s)") % (ref.name, intf["mac_address"], x.name, name))
                for x in match_ip:
                    if x.name != ref.name:
                        raise CX(_("Can't save system %s. The IP address (%s) is already used by system %s (%s)") % (ref.name, intf["ip_address"], x.name, name))
                for x in match_hosts:
                    if x.name != ref.name:
                        raise CX(_("Can't save system %s.  The dns name (%s) is already used by system %s (%s)") % (ref.name, intf["dns_name"], x.name, name))

    def to_string(self):
        """
        Creates a printable representation of the collection suitable for reading by humans or parsing from scripts.
        Actually scripts would be better off reading the JSON in the cobbler_collections files directly.

        :return: The object as a string representation.
        :rtype: str
        """
        values = list(self.listing.values())[:]   # copy the values
        values.sort()                       # sort the copy (2.3 fix)
        results = []
        for i, v in enumerate(values):
            results.append(v.to_string())
        if len(values) > 0:
            return "\n\n".join(results)
        else:
            return _("No objects found")

    @staticmethod
    def collection_type() -> str:
        """
        Returns the string key for the name of the collection (used by serializer etc)
        """
        return NotImplementedException()

    @staticmethod
    def collection_types() -> str:
        """
        Returns the string key for the plural name of the collection (used by serializer)
        """
        return NotImplementedException()

# EOF
