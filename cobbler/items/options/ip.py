"""
This module provides option classes for managing IP-related settings for network interfaces in Cobbler.
"""

from ipaddress import AddressValueError
from typing import TYPE_CHECKING, Any, List

from cobbler import utils, validate
from cobbler.items.options.base import ItemOption

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.network_interface import NetworkInterface

    LazyProperty = property
else:
    from cobbler.decorator import LazyProperty


class IPOption(ItemOption["NetworkInterface"]):
    """
    Option class for managing IP-related settings for a NetworkInterface.

    Provides properties and methods to set static routes and MTU values.
    """

    def __init__(
        self, api: "CobblerAPI", item: "NetworkInterface", **kwargs: Any
    ) -> None:
        super().__init__(api=api, item=item)
        self._address = ""
        self._static_routes: List[str] = []
        self._mtu = ""

        if len(kwargs) > 0:
            self.from_dict(kwargs)

    @property
    def static_routes(self) -> List[str]:
        """
        static_routes property.

        :getter: Returns the value for ``static_routes``.
        :setter: Sets the value for the property ``static_routes``.
        """
        return self._static_routes

    @static_routes.setter
    def static_routes(self, routes: List[str]):
        """
        Setter for the static_routes of the NetworkInterface class.

        :param routes: The new routes.
        """
        self._static_routes = self._api.input_string_or_list_no_inherit(routes)

    @property
    def mtu(self) -> str:
        """
        mtu property.

        :getter: Returns the value for ``mtu``.
        :setter: Sets the value for the property ``mtu``.
        """
        return self._mtu

    @mtu.setter
    def mtu(self, mtu: str):
        """
        Setter for the mtu of the NetworkInterface class.

        :param mtu: The new value for the mtu of the interface
        """
        if not isinstance(mtu, str):  # type: ignore
            raise TypeError(
                "Field mtu of object NetworkInterface needs to be type str!"
            )
        self._mtu = mtu


class IPv4Option(IPOption):
    """
    Option class for managing IPv4-specific settings for a NetworkInterface.

    Includes properties for address, netmask, and related configuration.
    """

    def __init__(
        self, api: "CobblerAPI", item: "NetworkInterface", **kwargs: Any
    ) -> None:
        super().__init__(api=api, item=item, **kwargs)
        self._netmask = ""

        if len(kwargs) > 0:
            self.from_dict(kwargs)

    @property
    def parent_name(self) -> str:
        return "ipv4"

    @LazyProperty
    def address(self) -> str:
        """
        address property.

        :getter: Returns the value for ``address``.
        :setter: Sets the value for the property ``address``.
        """
        return self._address

    @address.setter
    def address(self, address: str):
        """
        Set IPv4 address on interface.

        :param address: IP address
        :raises ValueError: In case the IP address is already existing inside Cobbler.
        """
        if self._address == address:
            return
        address = validate.ipv4_address(address)
        if address != "" and not self._api.settings().allow_duplicate_ips:
            matched = self._api.find_network_interface(
                return_list=True, ipv4=f"address={address}"
            )
            if matched is None:
                matched = []
            if not isinstance(matched, list):
                raise ValueError(
                    "Unexpected search result during ip deduplication search!"
                )
            for match in matched:
                raise ValueError(
                    f'IP address duplicate found "{address}". Object with the conflict has the name "{match.uid}"'
                )
        old_ip_address = self._address
        self._address = address
        self._api.network_interfaces().update_index_value(
            self._item, "ipv4.address", old_ip_address, address
        )

    @LazyProperty
    def netmask(self) -> str:
        """
        netmask property.

        :getter: Returns the value for ``netmask``.
        :setter: Sets the value for the property ``netmask``.
        """
        return self._netmask

    @netmask.setter
    def netmask(self, netmask: str):
        """
        Set the netmask for given interface.

        :param netmask: netmask
        """
        self._netmask = validate.ipv4_netmask(netmask)


class IPv6Option(IPOption):
    """
    Option class for managing IPv6-specific settings for a NetworkInterface.

    Includes properties for address, prefix, secondaries, and default gateway.
    """

    def __init__(
        self, api: "CobblerAPI", item: "NetworkInterface", **kwargs: Any
    ) -> None:
        super().__init__(api=api, item=item, **kwargs)
        self._default_gateway = ""
        self._prefix = ""
        self._secondaries: List[str] = []

        if len(kwargs) > 0:
            self.from_dict(kwargs)

    @property
    def parent_name(self) -> str:
        return "ipv6"

    @LazyProperty
    def address(self) -> str:
        """
        address property.

        :getter: Returns the value for ``address``.
        :setter: Sets the value for the property ``address``.
        """
        return self._address

    @address.setter
    def address(self, address: str):
        """
        Set IPv6 address on interface.

        :param address: IP address
        :raises ValueError: IN case the IP is duplicated
        """
        if self._address == address:
            return
        address = validate.ipv6_address(address)
        if address != "" and not self._api.settings().allow_duplicate_ips:
            matched = self._api.find_network_interface(
                return_list=True, ipv6=f"address={address}"
            )
            if matched is None:
                matched = []
            if not isinstance(matched, list):
                raise ValueError(
                    "Unexpected search result during ip deduplication search!"
                )
            for match in matched:
                raise ValueError(
                    f'IPv6 address duplicate found "{address}". Object with the conflict has the name'
                    f'"{match.uid}"'
                )
        old_ipv6_address = self._address
        self._address = address
        self._api.network_interfaces().update_index_value(
            self._item, "ipv6.address", old_ipv6_address, address
        )

    @property
    def prefix(self) -> str:
        """
        prefix property.

        :getter: Returns the value for ``prefix``.
        :setter: Sets the value for the property ``prefix``.
        """
        return self._prefix

    @prefix.setter
    def prefix(self, prefix: str):
        """
        Assign a IPv6 prefix

        :param prefix: The new IPv6 prefix for the interface.
        """
        if not isinstance(prefix, str):  # type: ignore
            raise TypeError(
                "Field ipv6_prefix of object NetworkInterface needs to be of type str!"
            )
        self._prefix = prefix.strip()

    @property
    def secondaries(self) -> List[str]:
        """
        secondaries property.

        :getter: Returns the value for ``secondaries``.
        :setter: Sets the value for the property ``secondaries``.
        """
        return self._secondaries

    @secondaries.setter
    def secondaries(self, addresses: List[str]):
        """
        Setter for the secondaries of the NetworkInterface class.

        :param addresses: The new secondaries for the interface.
        """
        data = self._api.input_string_or_list(addresses)
        secondaries: List[str] = []
        for address in data:
            if address == "" or utils.is_ip(address):
                secondaries.append(address)
            else:
                raise AddressValueError(
                    f"invalid format for IPv6 IP address ({address})"
                )
        self._secondaries = secondaries
