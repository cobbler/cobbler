"""
All code belonging to Cobbler network interfaces.

Changelog (NetworkInterface):

V3.4.0 (unreleased):
    * Changes:
        * Constructor: ``kwargs`` can now be used to seed the item during creation.
        * Moved into dedicated module
V3.3.4 (unreleased):
    * No changes
V3.3.3:
    * Changed:
        * ``to_dict()``: Accepts new parameter ``resolved``
        * ``virt_bridge``: Can now be set to ``<<inherit>>`` to get its value from the settings key
          ``default_virt_bridge``
V3.3.2:
    * No changes
V3.3.1:
    * No changes
V3.3.0:
    * This release switched from pure attributes to properties (getters/setters).
    * Added:
        * ``NetworkInterface`` is now a class.
        * Serialization still happens inside the system collection.
        * Properties have been used.
V3.2.2:
    * No changes
V3.2.1:
    * No changes
V3.2.0:
    * No changes
V3.1.2:
    * No changes
V3.1.1:
    * No changes
V3.1.0:
    * No changes
V3.0.1:
    * No changes
V3.0.0:
    * Field defintions now split of ``System`` class
V2.8.5:
    * Inital tracking of changes for the changelog.
    * Field definitions part of ``System`` class
    * Added:
        * ``mac_address``: str
        * ``connected_mode``: bool
        * ``mtu``: str
        * ``ip_address``: str
        * ``interface_type``: str - One of "na", "bond", "bond_slave", "bridge", bridge_slave", "bonded_bridge_slave",
          "infiniband"
        * ``interface_master``: str
        * ``bonding_opts``: str
        * ``bridge_opts``: str
        * ``management``: bool
        * ``static``: bool
        * ``netmask``: str
        * ``if_gateway``: str
        * ``dhcp_tag``: str
        * ``dns_name``: str
        * ``static_routes``: List[str]
        * ``virt_bridge``: str
        * ``ipv6_address``: str
        * ``ipv6_prefix``: str
        * ``ipv6_secondaries``: List[str]
        * ``ipv6_mtu``: str
        * ``ipv6_static_routes``: List[str]
        * ``ipv6_default_gateway``: str
        * ``cnames``: List[str]
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2008, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>


import enum
import logging
from ipaddress import AddressValueError
from typing import TYPE_CHECKING, Any, Dict, List, Union

from cobbler import enums, utils, validate
from cobbler.decorator import InheritableProperty
from cobbler.utils import input_converters

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class NetworkInterface:
    """
    A subobject of a Cobbler System which represents the network interfaces
    """

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any) -> None:
        """
        Constructor.

        :param api: The Cobbler API object which is used for resolving information.
        """
        self.__logger = logging.getLogger()
        self.__api = api
        self._bonding_opts = ""
        self._bridge_opts = ""
        self._cnames: List[str] = []
        self._connected_mode = False
        self._dhcp_tag = ""
        self._dns_name = ""
        self._if_gateway = ""
        self._interface_master = ""
        self._interface_type = enums.NetworkInterfaceType.NA
        self._ip_address = ""
        self._ipv6_address = ""
        self._ipv6_default_gateway = ""
        self._ipv6_mtu = ""
        self._ipv6_prefix = ""
        self._ipv6_secondaries: List[str] = []
        self._ipv6_static_routes: List[str] = []
        self._mac_address = ""
        self._management = False
        self._mtu = ""
        self._netmask = ""
        self._static = False
        self._static_routes: List[str] = []
        self._virt_bridge = enums.VALUE_INHERITED

        if len(kwargs) > 0:
            self.from_dict(kwargs)

    def from_dict(self, dictionary: Dict[str, Any]):
        """
        Initializes the object with attributes from the dictionary.

        :param dictionary: The dictionary with values.
        """
        dictionary_keys = list(dictionary.keys())
        for key in dictionary:
            if hasattr(self, key):
                setattr(self, key, dictionary[key])
                dictionary_keys.remove(key)
        if len(dictionary_keys) > 0:
            self.__logger.info(
                "The following keys were ignored and could not be set for the NetworkInterface object: "
                "%s",
                str(dictionary_keys),
            )

    def to_dict(self, resolved: bool = False) -> Dict[str, Any]:
        """
        This converts everything in this object to a dictionary.

        :param resolved: If this is True, Cobbler will resolve the values to its final form, rather than give you the
                         objects raw value.
        :return: A dictionary with all values present in this object.
        """
        result: Dict[str, Any] = {}
        for key, key_value in self.__dict__.items():
            if "__" in key:
                continue
            if key.startswith("_"):
                new_key = key[1:].lower()
                if isinstance(key_value, enum.Enum):
                    result[new_key] = key_value.name.lower()
                elif (
                    isinstance(key_value, str)
                    and key_value == enums.VALUE_INHERITED
                    and resolved
                ):
                    result[new_key] = getattr(self, key[1:])
                else:
                    result[new_key] = key_value
        return result

    # These two methods are currently not used, but we do want to use them in the future, so let's define them.
    def serialize(self) -> Dict[str, Any]:
        """
        This method is a proxy for :meth:`~cobbler.items.item.Item.to_dict` and contains additional logic for
        serialization to a persistent location.

        :return: The dictionary with the information for serialization.
        """
        return self.to_dict()

    def deserialize(self, interface_dict: Dict[str, Any]):
        """
        This is currently a proxy for :py:meth:`~cobbler.items.item.Item.from_dict` .

        :param interface_dict: The dictionary with the data to deserialize.
        """
        self.from_dict(interface_dict)

    @property
    def dhcp_tag(self) -> str:
        """
        dhcp_tag property.

        :getter: Returns the value for ``dhcp_tag``.
        :setter: Sets the value for the property ``dhcp_tag``.
        """
        return self._dhcp_tag

    @dhcp_tag.setter
    def dhcp_tag(self, dhcp_tag: str):
        """
        Setter for the dhcp_tag of the NetworkInterface class.

        :param dhcp_tag: The new dhcp tag.
        """
        if not isinstance(dhcp_tag, str):  # type: ignore
            raise TypeError(
                "Field dhcp_tag of object NetworkInterface needs to be of type str!"
            )
        self._dhcp_tag = dhcp_tag

    @property
    def cnames(self) -> List[str]:
        """
        cnames property.

        :getter: Returns the value for ``cnames``.
        :setter: Sets the value for the property ``cnames``.
        """
        return self._cnames

    @cnames.setter
    def cnames(self, cnames: List[str]):
        """
        Setter for the cnames of the NetworkInterface class.

        :param cnames: The new cnames.
        """
        self._cnames = input_converters.input_string_or_list_no_inherit(cnames)

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
        self._static_routes = input_converters.input_string_or_list_no_inherit(routes)

    @property
    def static(self) -> bool:
        """
        static property.

        :getter: Returns the value for ``static``.
        :setter: Sets the value for the property ``static``.
        """
        return self._static

    @static.setter
    def static(self, truthiness: bool):
        """
        Setter for the static of the NetworkInterface class.

        :param truthiness: The new value if the interface is static or not.
        """
        try:
            truthiness = input_converters.input_boolean(truthiness)
        except TypeError as error:
            raise TypeError(
                "Field static of NetworkInterface needs to be of Type bool!"
            ) from error
        self._static = truthiness

    @property
    def management(self) -> bool:
        """
        management property.

        :getter: Returns the value for ``management``.
        :setter: Sets the value for the property ``management``.
        """
        return self._management

    @management.setter
    def management(self, truthiness: bool):
        """
        Setter for the management of the NetworkInterface class.

        :param truthiness: The new value for management.
        """
        try:
            truthiness = input_converters.input_boolean(truthiness)
        except TypeError as error:
            raise TypeError(
                "Field management of object NetworkInterface needs to be of type bool!"
            ) from error
        self._management = truthiness

    @property
    def dns_name(self) -> str:
        """
        dns_name property.

        :getter: Returns the value for ``dns_name`.
        :setter: Sets the value for the property ``dns_name``.
        """
        return self._dns_name

    @dns_name.setter
    def dns_name(self, dns_name: str):
        """
        Set DNS name for interface.

        :param dns_name: DNS Name of the system
        :raises ValueError: In case the DNS name is already existing inside Cobbler
        """
        dns_name = validate.hostname(dns_name)
        if dns_name != "" and not self.__api.settings().allow_duplicate_hostnames:
            matched = self.__api.find_system(dns_name=dns_name)
            if matched is None:
                matched = []
            if not isinstance(matched, list):  # type: ignore
                raise ValueError("Incompatible return type detected!")
            for match in matched:
                if self in match.interfaces.values():
                    continue
                raise ValueError(
                    f'DNS name duplicate found "{dns_name}". Object with the conflict has the name "{match.name}"'
                )
        self._dns_name = dns_name

    @property
    def ip_address(self) -> str:
        """
        ip_address property.

        :getter: Returns the value for ``ip_address``.
        :setter: Sets the value for the property ``ip_address``.
        """
        return self._ip_address

    @ip_address.setter
    def ip_address(self, address: str):
        """
        Set IPv4 address on interface.

        :param address: IP address
        :raises ValueError: In case the IP address is already existing inside Cobbler.
        """
        address = validate.ipv4_address(address)
        if address != "" and not self.__api.settings().allow_duplicate_ips:
            matched = self.__api.find_system(return_list=True, ip_address=address)
            if matched is None:
                matched = []
            if not isinstance(matched, list):
                raise ValueError(
                    "Unexpected search result during ip deduplication search!"
                )
            for match in matched:
                if self in match.interfaces.values():
                    continue
                raise ValueError(
                    f'IP address duplicate found "{address}". Object with the conflict has the name "{match.name}"'
                )
        self._ip_address = address

    @property
    def mac_address(self) -> str:
        """
        mac_address property.

        :getter: Returns the value for ``mac_address``.
        :setter: Sets the value for the property ``mac_address``.
        """
        return self._mac_address

    @mac_address.setter
    def mac_address(self, address: str):
        """
        Set MAC address on interface.

        :param address: MAC address
        :raises CX: In case there a random mac can't be computed
        """
        address = validate.mac_address(address)
        if address == "random":
            # FIXME: Pass virt_type of system
            address = utils.get_random_mac(self.__api)
        if address != "" and not self.__api.settings().allow_duplicate_macs:
            matched = self.__api.find_system(mac_address=address)
            if matched is None:
                matched = []
            if not isinstance(matched, list):
                raise ValueError(
                    "Unexpected search result during ip deduplication search!"
                )
            for match in matched:
                if self in match.interfaces.values():
                    continue
                raise ValueError(
                    f'MAC address duplicate found "{address}". Object with the conflict has the name "{match.name}"'
                )
        self._mac_address = address

    @property
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

    @property
    def if_gateway(self) -> str:
        """
        if_gateway property.

        :getter: Returns the value for ``if_gateway``.
        :setter: Sets the value for the property ``if_gateway``.
        """
        return self._if_gateway

    @if_gateway.setter
    def if_gateway(self, gateway: str):
        """
        Set the per-interface gateway. Exceptions are raised if the value is invalid. For details see
        :meth:`~cobbler.validate.ipv4_address`.

        :param gateway: IPv4 address for the gateway
        """
        self._if_gateway = validate.ipv4_address(gateway)

    @InheritableProperty
    def virt_bridge(self) -> str:
        """
        virt_bridge property. If set to ``<<inherit>>`` this will read the value from the setting "default_virt_bridge".

        :getter: Returns the value for ``virt_bridge``.
        :setter: Sets the value for the property ``virt_bridge``.
        """
        if self._virt_bridge == enums.VALUE_INHERITED:
            return self.__api.settings().default_virt_bridge
        return self._virt_bridge

    @virt_bridge.setter
    def virt_bridge(self, bridge: str):
        """
        Setter for the virt_bridge of the NetworkInterface class.

        :param bridge: The new value for "virt_bridge".
        """
        if not isinstance(bridge, str):  # type: ignore
            raise TypeError(
                "Field virt_bridge of object NetworkInterface should be of type str!"
            )
        if bridge == "":
            self._virt_bridge = enums.VALUE_INHERITED
            return
        self._virt_bridge = bridge

    @property
    def interface_type(self) -> enums.NetworkInterfaceType:
        """
        interface_type property.

        :getter: Returns the value for ``interface_type``.
        :setter: Sets the value for the property ``interface_type``.
        """
        return self._interface_type

    @interface_type.setter
    def interface_type(self, intf_type: Union[enums.NetworkInterfaceType, int, str]):
        """
        Setter for the interface_type of the NetworkInterface class.

        :param intf_type: The interface type to be set. Will be autoconverted to the enum type if possible.
        """
        if not isinstance(intf_type, (enums.NetworkInterfaceType, int, str)):  # type: ignore
            raise TypeError(
                "interface intf_type type must be of int, str or enums.NetworkInterfaceType"
            )
        if isinstance(intf_type, int):
            try:
                intf_type = enums.NetworkInterfaceType(intf_type)
            except ValueError as value_error:
                raise ValueError(
                    f'intf_type with number "{intf_type}" was not a valid interface type!'
                ) from value_error
        elif isinstance(intf_type, str):
            try:
                intf_type = enums.NetworkInterfaceType[intf_type.upper()]
            except KeyError as key_error:
                raise ValueError(
                    f"intf_type choices include: {list(map(str, enums.NetworkInterfaceType))}"
                ) from key_error
        # Now it must be of the enum type
        if intf_type not in enums.NetworkInterfaceType:
            raise ValueError(
                "interface intf_type value must be one of:"
                f"{','.join(list(map(str, enums.NetworkInterfaceType)))} or blank"
            )
        self._interface_type = intf_type

    @property
    def interface_master(self) -> str:
        """
        interface_master property.

        :getter: Returns the value for ``interface_master``.
        :setter: Sets the value for the property ``interface_master``.
        """
        return self._interface_master

    @interface_master.setter
    def interface_master(self, interface_master: str):
        """
        Setter for the interface_master of the NetworkInterface class.

        :param interface_master: The new interface master.
        """
        if not isinstance(interface_master, str):  # type: ignore
            raise TypeError(
                "Field interface_master of object NetworkInterface needs to be of type str!"
            )
        self._interface_master = interface_master

    @property
    def bonding_opts(self) -> str:
        """
        bonding_opts property.

        :getter: Returns the value for ``bonding_opts``.
        :setter: Sets the value for the property ``bonding_opts``.
        """
        return self._bonding_opts

    @bonding_opts.setter
    def bonding_opts(self, bonding_opts: str):
        """
        Setter for the bonding_opts of the NetworkInterface class.

        :param bonding_opts: The new bonding options for the interface.
        """
        if not isinstance(bonding_opts, str):  # type: ignore
            raise TypeError(
                "Field bonding_opts of object NetworkInterface needs to be of type str!"
            )
        self._bonding_opts = bonding_opts

    @property
    def bridge_opts(self) -> str:
        """
        bridge_opts property.

        :getter: Returns the value for ``bridge_opts``.
        :setter: Sets the value for the property ``bridge_opts``.
        """
        return self._bridge_opts

    @bridge_opts.setter
    def bridge_opts(self, bridge_opts: str):
        """
        Setter for the bridge_opts of the NetworkInterface class.

        :param bridge_opts: The new bridge options to set for the interface.
        """
        if not isinstance(bridge_opts, str):  # type: ignore
            raise TypeError(
                "Field bridge_opts of object NetworkInterface needs to be of type str!"
            )
        self._bridge_opts = bridge_opts

    @property
    def ipv6_address(self) -> str:
        """
        ipv6_address property.

        :getter: Returns the value for ``ipv6_address``.
        :setter: Sets the value for the property ``ipv6_address``.
        """
        return self._ipv6_address

    @ipv6_address.setter
    def ipv6_address(self, address: str):
        """
        Set IPv6 address on interface.

        :param address: IP address
        :raises ValueError: IN case the IP is duplicated
        """
        address = validate.ipv6_address(address)
        if address != "" and not self.__api.settings().allow_duplicate_ips:
            matched = self.__api.find_system(ipv6_address=address)
            if matched is None:
                matched = []
            if not isinstance(matched, list):
                raise ValueError(
                    "Unexpected search result during ip deduplication search!"
                )
            for match in matched:
                if self in match.interfaces.values():
                    continue
                raise ValueError(
                    f'IPv6 address duplicate found "{address}". Object with the conflict has the name'
                    f'"{match.name}"'
                )
        self._ipv6_address = address

    @property
    def ipv6_prefix(self) -> str:
        """
        ipv6_prefix property.

        :getter: Returns the value for ``ipv6_prefix``.
        :setter: Sets the value for the property ``ipv6_prefix``.
        """
        return self._ipv6_address

    @ipv6_prefix.setter
    def ipv6_prefix(self, prefix: str):
        """
        Assign a IPv6 prefix

        :param prefix: The new IPv6 prefix for the interface.
        """
        if not isinstance(prefix, str):  # type: ignore
            raise TypeError(
                "Field ipv6_prefix of object NetworkInterface needs to be of type str!"
            )
        self._ipv6_prefix = prefix.strip()

    @property
    def ipv6_secondaries(self) -> List[str]:
        """
        ipv6_secondaries property.

        :getter: Returns the value for ``ipv6_secondaries``.
        :setter: Sets the value for the property ``ipv6_secondaries``.
        """
        return self._ipv6_secondaries

    @ipv6_secondaries.setter
    def ipv6_secondaries(self, addresses: List[str]):
        """
        Setter for the ipv6_secondaries of the NetworkInterface class.

        :param addresses: The new secondaries for the interface.
        """
        data = input_converters.input_string_or_list(addresses)
        secondaries: List[str] = []
        for address in data:
            if address == "" or utils.is_ip(address):
                secondaries.append(address)
            else:
                raise AddressValueError(
                    f"invalid format for IPv6 IP address ({address})"
                )
        self._ipv6_secondaries = secondaries

    @property
    def ipv6_default_gateway(self) -> str:
        """
        ipv6_default_gateway property.

        :getter: Returns the value for ``ipv6_default_gateway``.
        :setter: Sets the value for the property ``ipv6_default_gateway``.
        """
        return self._ipv6_default_gateway

    @ipv6_default_gateway.setter
    def ipv6_default_gateway(self, address: str):
        """
        Setter for the ipv6_default_gateway of the NetworkInterface class.

        :param address: The new default gateway for the interface.
        """
        if not isinstance(address, str):  # type: ignore
            raise TypeError(
                "Field ipv6_default_gateway of object NetworkInterface needs to be of type str!"
            )
        if address == "" or utils.is_ip(address):
            self._ipv6_default_gateway = address.strip()
            return
        raise AddressValueError(f"invalid format of IPv6 IP address ({address})")

    @property
    def ipv6_static_routes(self) -> List[str]:
        """
        ipv6_static_routes property.

        :getter: Returns the value for ``ipv6_static_routes``.
        :setter: Sets the value for the property `ipv6_static_routes``.
        """
        return self._ipv6_static_routes

    @ipv6_static_routes.setter
    def ipv6_static_routes(self, routes: List[str]):
        """
        Setter for the ipv6_static_routes of the NetworkInterface class.

        :param routes: The new static routes for the interface.
        """
        self._ipv6_static_routes = input_converters.input_string_or_list_no_inherit(
            routes
        )

    @property
    def ipv6_mtu(self) -> str:
        """
        ipv6_mtu property.

        :getter: Returns the value for ``ipv6_mtu``.
        :setter: Sets the value for the property ``ipv6_mtu``.
        """
        return self._ipv6_mtu

    @ipv6_mtu.setter
    def ipv6_mtu(self, mtu: str):
        """
        Setter for the ipv6_mtu of the NetworkInterface class.

        :param mtu: The new IPv6 MTU for the interface.
        """
        if not isinstance(mtu, str):  # type: ignore
            raise TypeError(
                "Field ipv6_mtu of object NetworkInterface needs to be of type str!"
            )
        self._ipv6_mtu = mtu

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

    @property
    def connected_mode(self) -> bool:
        """
        connected_mode property.

        :getter: Returns the value for ``connected_mode``.
        :setter: Sets the value for the property ``connected_mode``.
        """
        return self._connected_mode

    @connected_mode.setter
    def connected_mode(self, truthiness: bool):
        """
        Setter for the connected_mode of the NetworkInterface class.

        :param truthiness: The new value for connected mode of the interface.
        """
        try:
            truthiness = input_converters.input_boolean(truthiness)
        except TypeError as error:
            raise TypeError(
                "Field connected_mode of object NetworkInterface needs to be of type bool!"
            ) from error
        self._connected_mode = truthiness

    def modify_interface(self, _dict: Dict[str, Any]):
        """
        Modify the interface

        :param _dict: The dict with the parameter.
        """
        for key, value in list(_dict.items()):
            (field, _) = key.split("-", 1)
            field = field.replace("_", "").replace("-", "")

            if field == "bondingopts":
                self.bonding_opts = value
            if field == "bridgeopts":
                self.bridge_opts = value
            if field == "connectedmode":
                self.connected_mode = value
            if field == "cnames":
                self.cnames = value
            if field == "dhcptag":
                self.dhcp_tag = value
            if field == "dnsname":
                self.dns_name = value
            if field == "ifgateway":
                self.if_gateway = value
            if field == "interfacetype":
                self.interface_type = value
            if field == "interfacemaster":
                self.interface_master = value
            if field == "ipaddress":
                self.ip_address = value
            if field == "ipv6address":
                self.ipv6_address = value
            if field == "ipv6defaultgateway":
                self.ipv6_default_gateway = value
            if field == "ipv6mtu":
                self.ipv6_mtu = value
            if field == "ipv6prefix":
                self.ipv6_prefix = value
            if field == "ipv6secondaries":
                self.ipv6_secondaries = value
            if field == "ipv6staticroutes":
                self.ipv6_static_routes = value
            if field == "macaddress":
                self.mac_address = value
            if field == "management":
                self.management = value
            if field == "mtu":
                self.mtu = value
            if field == "netmask":
                self.netmask = value
            if field == "static":
                self.static = value
            if field == "staticroutes":
                self.static_routes = value
            if field == "virtbridge":
                self.virt_bridge = value
