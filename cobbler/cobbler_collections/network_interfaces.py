"""
TODO
"""

import os
from typing import TYPE_CHECKING, Any, Dict, Optional, List
from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.items import network_interface
from cobbler.cobbler_collections import collection
from cobbler.utils import filesystem_helpers

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.cobbler_collections.collection import ITEM


class NetworkInterfaces(collection.Collection[network_interface.NetworkInterface]):
    """
    TODO
    """

    @staticmethod
    def collection_type() -> str:
        return "network_interface"

    @staticmethod
    def collection_types() -> str:
        return "network_interfaces"

    def factory_produce(
        self, api: "CobblerAPI", seed_data: Dict[str, Any]
    ) -> network_interface.NetworkInterface:
        """
        Return a Network Interface forged from seed_data

        :param api: Parameter is skipped.
        :param seed_data: The data the object is initalized with.
        :returns: The created repository.
        """
        return network_interface.NetworkInterface(self.api, **seed_data)

    def get(self, name: str) -> Optional["ITEM"]:  # type: ignore
        """
        Return object with name in the collection

        :param name: The name of the object to retrieve from the collection.
        :return: The object if it exists. Otherwise, "None".
        """
        search_result = self.find(name=name)
        if isinstance(search_result, list):
            raise TypeError("Search result may not be list!")
        return search_result  # type: ignore

    def get_names(self) -> List[str]:
        """
        Return list of names in the collection.

        :return: list of names in the collection.
        """
        result: List[str] = []
        for item in self.listing.values():
            result.append(item.name)
        return result

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
        # FIXME: Implement

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

        # FIXME: Implement

    def remove(
        self,
        name: str,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
        rebuild_menu: bool = True,
    ) -> None:
        """
        Remove element named 'name' from the collection

        :raises CX: In case any subitem (profiles or systems) would be orphaned. If the option ``recursive`` is set then
                    the orphaned items would be removed automatically.
        """

        # NOTE: with_delete isn't currently meaningful for repos
        # but is left in for consistancy in the API.  Unused.
        obj = self.find(name=name)

        if obj is None:
            raise CX(f"cannot delete an object that does not exist: {name}")

        if isinstance(obj, list):
            # Will never happen, but we want to make mypy happy.
            raise CX("Ambiguous match detected!")

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api,
                    obj,
                    "/var/lib/cobbler/triggers/delete/network_interfaces/pre/*",
                    [],
                )

        with self.lock:
            self.remove_from_indexes(obj)
            del self.listing[name]
        self.collection_mgr.serialize_delete(self, obj)

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api,
                    obj,
                    "/var/lib/cobbler/triggers/delete/network_interfaces/post/*",
                    [],
                )
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/change/*", []
                )

            path = os.path.join(self.api.settings().webdir, "repo_mirror", obj.name)
            if os.path.exists(path):
                filesystem_helpers.rmtree(path)
