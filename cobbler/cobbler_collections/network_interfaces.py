"""
Cobbler module that at runtime holds all network interfaces in Cobbler.
"""

from typing import TYPE_CHECKING, Any, Dict

from cobbler.cexceptions import CX
from cobbler.cobbler_collections import collection
from cobbler.items import network_interface

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class NetworkInterfaces(collection.Collection[network_interface.NetworkInterface]):
    """
    A network interface represents a virtual or physical network interface for a given System.
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
        system_uid = seed_data.pop("system_uid")
        return network_interface.NetworkInterface(
            api=self.api,
            system_uid=system_uid,
            **seed_data,
        )

    def check_for_duplicate_names(
        self, ref: network_interface.NetworkInterface
    ) -> None:
        search_result = self.find(True, system_uid=ref.system_uid, name=ref.name)
        if not isinstance(search_result, list):
            raise TypeError("Search result must be of type list!")
        if len(search_result) > 0:
            raise CX(
                f'An object with that name "{ref.name}" exists already on system {ref.system_uid}. Try "edit"?'
            )
