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
from cobbler.items import network_interface, system

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Systems(collection.Collection[system.System]):
    """
    Systems are hostnames/MACs/IP names and the associated profile
    they belong to.
    """

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

    def update_interface_index_value(
        self,
        interface: network_interface.NetworkInterface,
        attribute_name: str,
        old_value: str,
        new_value: str,
    ) -> None:
        if (
            interface.system_name in self.listing
            and interface in self.listing[interface.system_name].interfaces.values()
            and self.listing[interface.system_name].inmemory
        ):
            self.update_index_value(
                self.listing[interface.system_name],
                attribute_name,
                old_value,
                new_value,
            )

    def update_interfaces_indexes(
        self,
        ref: system.System,
        new_ifaces: Dict[str, network_interface.NetworkInterface],
    ) -> None:
        """
        Update interfaces indexes for the system.

        :param ref: The reference to the system whose interfaces indexes are updated.
        :param new_ifaces: The new interfaces.
        """
        if ref.name not in self.listing:
            return

        for indx in self.indexes:
            if indx == "uid":
                continue

            old_ifaces = ref.interfaces
            old_values: Set[str] = {
                getattr(x, indx)
                for x in old_ifaces.values()
                if hasattr(x, indx) and getattr(x, indx) != ""
            }
            new_values: Set[str] = {
                getattr(x, indx)
                for x in new_ifaces.values()
                if hasattr(x, indx) and getattr(x, indx) != ""
            }

            with self.lock:
                for value in old_values - new_values:
                    self.index_helper(
                        ref,
                        indx,
                        value,
                        self.remove_single_index_value,
                    )
                for value in new_values - old_values:
                    self.index_helper(
                        ref,
                        indx,
                        value,
                        self.add_single_index_value,
                    )

    def update_interface_indexes(
        self,
        ref: system.System,
        iface_name: str,
        new_iface: network_interface.NetworkInterface,
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

    def remove_interface_from_indexes(self, ref: system.System, name: str) -> None:
        """
        Remove index keys for the system interface.

        :param ref: The reference to the system whose index keys are removed.
        :param name: The reference to the system whose index keys are removed.
        """
        if not ref.inmemory or name not in ref.interfaces:
            return

        new_ifaces = ref.interfaces.copy()
        del new_ifaces[name]
        self.update_interfaces_indexes(ref, new_ifaces)
