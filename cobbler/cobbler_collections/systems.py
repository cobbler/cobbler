"""
Cobbler module that at runtime holds all systems in Cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2008-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from typing import TYPE_CHECKING, Any, Dict, Set

from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import collection
from cobbler.items import system

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.cobbler_collections.manager import CollectionManager


class Systems(collection.Collection[system.System]):
    """
    Systems are hostnames/MACs/IP names and the associated profile
    they belong to.
    """

    def __init__(self, collection_mgr: "CollectionManager"):
        """
        Constructor.

        :param collection_mgr: The collection manager to resolve all information with.
        """
        super().__init__(collection_mgr)
        self.indexes: Dict[str, Dict[str, str]] = {
            "uid": {},
            "mac_address": {},
            "ip_address": {},
            "ipv6_address": {},
            "dns_name": {},
        }
        settings = self.api.settings()
        self.disabled_indexes: Dict[str, bool] = {
            "mac_address": settings.allow_duplicate_macs,
            "ip_address": settings.allow_duplicate_ips,
            "ipv6_address": settings.allow_duplicate_ips,
            "dns_name": settings.allow_duplicate_hostnames,
        }

    @staticmethod
    def collection_type() -> str:
        return "system"

    @staticmethod
    def collection_types() -> str:
        return "systems"

    def factory_produce(
        self, api: "CobblerAPI", seed_data: Dict[str, Any]
    ) -> system.System:
        """
        Return a System forged from seed_data

        :param api: Parameter is skipped.
        :param seed_data: Data to seed the object with.
        :returns: The created object.
        """
        return system.System(self.api, **seed_data)

    def remove(
        self,
        name: str,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
    ) -> None:
        """
        Remove element named 'name' from the collection

        :raises CX: In case the name of the object was not given.
        """
        obj = self.listing.get(name, None)

        if obj is None:
            raise CX(f"cannot delete an object that does not exist: {name}")

        if isinstance(obj, list):
            # Will never happen, but we want to make mypy happy.
            raise CX("Ambiguous match detected!")

        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/system/pre/*", []
                )
            if with_sync:
                lite_sync = self.api.get_sync()
                lite_sync.remove_single_system(obj)

        with self.lock:
            self.remove_from_indexes(obj)
            del self.listing[name]
        self.collection_mgr.serialize_delete(self, obj)
        if with_delete:
            if with_triggers:
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/delete/system/post/*", []
                )
                utils.run_triggers(
                    self.api, obj, "/var/lib/cobbler/triggers/change/*", []
                )

    def add_to_indexes(self, ref: system.System) -> None:
        """
        Add indexes for the system.

        :param ref: The reference to the system whose indexes are updated.
        """
        super().add_to_indexes(ref)
        if not ref.inmemory:
            return

        for indx_key, indx_val in self.indexes.items():
            if indx_key == "uid" or self.disabled_indexes[indx_key]:
                continue

            for interface in ref.interfaces.values():
                if hasattr(interface, indx_key):
                    secondary_key = getattr(interface, indx_key)
                    if secondary_key is not None and secondary_key != "":
                        indx_val[secondary_key] = ref.name

    def update_interface_index_value(
        self,
        interface: system.NetworkInterface,
        attribute_name: str,
        old_value: str,
        new_value: str,
    ) -> None:
        if (
            interface.system_name in self.listing
            and not self.disabled_indexes[attribute_name]
            and interface in self.listing[interface.system_name].interfaces.values()
        ):
            indx_dict = self.indexes[attribute_name]
            with self.lock:
                if (
                    old_value != ""
                    and old_value in indx_dict
                    and indx_dict[old_value] == interface.system_name
                ):
                    del indx_dict[old_value]
                if new_value != "":
                    indx_dict[new_value] = interface.system_name

    def update_interfaces_indexes(
        self, ref: system.System, new_ifaces: Dict[str, system.NetworkInterface]
    ) -> None:
        """
        Update interfaces indexes for the system.

        :param ref: The reference to the system whose interfaces indexes are updated.
        :param new_ifaces: The new interfaces.
        """
        if ref.name not in self.listing:
            return

        for indx_key, indx_val in self.indexes.items():
            if indx_key == "uid" or self.disabled_indexes[indx_key]:
                continue

            old_ifaces = ref.interfaces
            old_values: Set[str] = {
                getattr(x, indx_key)
                for x in old_ifaces.values()
                if hasattr(x, indx_key) and getattr(x, indx_key) != ""
            }
            new_values: Set[str] = {
                getattr(x, indx_key)
                for x in new_ifaces.values()
                if hasattr(x, indx_key) and getattr(x, indx_key) != ""
            }

            with self.lock:
                for value in old_values - new_values:
                    del indx_val[value]
                for value in new_values - old_values:
                    indx_val[value] = ref.name

    def update_interface_indexes(
        self, ref: system.System, iface_name: str, new_iface: system.NetworkInterface
    ) -> None:
        """
        Update interface indexes for the system.

        :param ref: The reference to the system whose interfaces indexes are updated.
        :param iface_name: The new interface name.
        :param new_iface: The new interface.
        """
        self.update_interfaces_indexes(
            ref, {**ref.interfaces, **{iface_name: new_iface}}
        )

    def remove_from_indexes(self, ref: system.System) -> None:
        """
        Remove index keys for the system.

        :param ref: The reference to the system whose index keys are removed.
        """
        if not ref.inmemory:
            return

        super().remove_from_indexes(ref)
        for indx_key, indx_val in self.indexes.items():
            if indx_key == "uid" or self.disabled_indexes[indx_key]:
                continue

            for interface in ref.interfaces.values():
                if hasattr(interface, indx_key):
                    indx_val.pop(getattr(interface, indx_key), None)

    def remove_interface_from_indexes(self, ref: system.System, name: str) -> None:
        """
        Remove index keys for the system interface.

        :param ref: The reference to the system whose index keys are removed.
        :param name: The reference to the system whose index keys are removed.
        """
        if not ref.inmemory or name not in ref.interfaces:
            return

        interface = ref.interfaces[name]
        with self.lock:
            for indx_key, indx_val in self.indexes.items():
                if indx_key == "uid" or self.disabled_indexes[indx_key]:
                    continue
                if hasattr(interface, indx_key):
                    indx_val.pop(getattr(interface, indx_key), None)
