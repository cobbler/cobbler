"""
All code belonging to Cobbler systems. This includes network interfaces.
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2008, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import enum
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from ipaddress import AddressValueError

from cobbler import autoinstall_manager, enums, power_manager, utils, validate
from cobbler.cexceptions import CX
from cobbler.items.item import Item
from cobbler.decorator import InheritableProperty, LazyProperty


class NetworkInterface:
    """
    A subobject of a Cobbler System which represents the network interfaces
    """

    def __init__(self, api):
        """
        Constructor.

        :param api: The Cobbler API object which is used for resolving information.
        """
        self.__logger = logging.getLogger()
        self.__api = api
        self._bonding_opts = ""
        self._bridge_opts = ""
        self._cnames = []
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
        self._ipv6_secondaries = []
        self._ipv6_static_routes = []
        self._mac_address = ""
        self._management = False
        self._mtu = ""
        self._netmask = ""
        self._static = False
        self._static_routes = []
        self._virt_bridge = ""

    def from_dict(self, dictionary: dict):
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
            self.__logger.info("The following keys were ignored and could not be set for the NetworkInterface object: "
                               "%s", str(dictionary_keys))

    def to_dict(self, resolved: bool = False) -> dict:
        """
        This converts everything in this object to a dictionary.

        :param resolved: If this is True, Cobbler will resolve the values to its final form, rather than give you the
                         objects raw value.
        :return: A dictionary with all values present in this object.
        """
        result = {}
        for key in self.__dict__:
            if "__" in key:
                continue
            if key.startswith("_"):
                new_key = key[1:].lower()
                key_value = self.__dict__[key]
                if isinstance(key_value, enum.Enum):
                    result[new_key] = self.__dict__[key].name.lower()
                elif (
                    isinstance(key_value, str)
                    and key_value == enums.VALUE_INHERITED
                    and resolved
                ):
                    result[new_key] = getattr(self, key[1:])
                else:
                    result[new_key] = self.__dict__[key]
        return result

    # These two methods are currently not used, but we do want to use them in the future, so let's define them.
    def serialize(self):
        """
        This method is a proxy for :meth:`~cobbler.items.item.Item.to_dict` and contains additional logic for
        serialization to a persistent location.

        :return: The dictionary with the information for serialization.
        """
        self.to_dict()

    def deserialize(self, interface_dict: dict):
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
        if not isinstance(dhcp_tag, str):
            raise TypeError("Field dhcp_tag of object NetworkInterface needs to be of type str!")
        self._dhcp_tag = dhcp_tag

    @property
    def cnames(self) -> list:
        """
        cnames property.

        :getter: Returns the value for ``cnames``.
        :setter: Sets the value for the property ``cnames``.
        """
        return self._cnames

    @cnames.setter
    def cnames(self, cnames: list):
        """
        Setter for the cnames of the NetworkInterface class.

        :param cnames: The new cnames.
        """
        self._cnames = utils.input_string_or_list_no_inherit(cnames)

    @property
    def static_routes(self) -> list:
        """
        static_routes property.

        :getter: Returns the value for ``static_routes``.
        :setter: Sets the value for the property ``static_routes``.
        """
        return self._static_routes

    @static_routes.setter
    def static_routes(self, routes: list):
        """
        Setter for the static_routes of the NetworkInterface class.

        :param routes: The new routes.
        """
        self._static_routes = utils.input_string_or_list_no_inherit(routes)

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
            truthiness = utils.input_boolean(truthiness)
        except TypeError as e:
            raise TypeError("Field static of NetworkInterface needs to be of Type bool!") from e
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
            truthiness = utils.input_boolean(truthiness)
        except TypeError as e:
            raise TypeError(
                "Field management of object NetworkInterface needs to be of type bool!"
            ) from e
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
            matched = self.__api.find_items("system", {"dns_name": dns_name})
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
            matched = self.__api.find_items("system", {"ip_address": address})
            for match in matched:
                if self in match.interfaces.values():
                    continue
                else:
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
            matched = self.__api.find_items("system", {"mac_address": address})
            for match in matched:
                if self in match.interfaces.values():
                    continue
                else:
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
        if not isinstance(bridge, str):
            raise TypeError("Field virt_bridge of object NetworkInterface should be of type str!")
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
        if not isinstance(intf_type, (enums.NetworkInterfaceType, int, str)):
            raise TypeError("interface intf_type type must be of int, str or enums.NetworkInterfaceType")
        if isinstance(intf_type, int):
            try:
                intf_type = enums.NetworkInterfaceType(intf_type)
            except ValueError as value_error:
                raise ValueError("intf_type with number \"%s\" was not a valid interface type!" % intf_type) \
                    from value_error
        elif isinstance(intf_type, str):
            try:
                intf_type = enums.NetworkInterfaceType[intf_type.upper()]
            except KeyError as key_error:
                raise ValueError("intf_type choices include: %s" % list(map(str, enums.NetworkInterfaceType))) \
                    from key_error
        # Now it must be of the enum type
        if intf_type not in enums.NetworkInterfaceType:
            raise ValueError("interface intf_type value must be one of: %s or blank" %
                             ",".join(list(map(str, enums.NetworkInterfaceType))))
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
        if not isinstance(interface_master, str):
            raise TypeError("Field interface_master of object NetworkInterface needs to be of type str!")
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
        if not isinstance(bonding_opts, str):
            raise TypeError("Field bonding_opts of object NetworkInterface needs to be of type str!")
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
        if not isinstance(bridge_opts, str):
            raise TypeError("Field bridge_opts of object NetworkInterface needs to be of type str!")
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
            matched = self.__api.find_items("system", {"ipv6_address": address})
            for match in matched:
                if self in match.interfaces.values():
                    continue
                else:
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
        if not isinstance(prefix, str):
            raise TypeError("Field ipv6_prefix of object NetworkInterface needs to be of type str!")
        self._ipv6_prefix = prefix.strip()

    @property
    def ipv6_secondaries(self) -> list:
        """
        ipv6_secondaries property.

        :getter: Returns the value for ``ipv6_secondaries``.
        :setter: Sets the value for the property ``ipv6_secondaries``.
        """
        return self._ipv6_secondaries

    @ipv6_secondaries.setter
    def ipv6_secondaries(self, addresses: list):
        """
        Setter for the ipv6_secondaries of the NetworkInterface class.

        :param addresses: The new secondaries for the interface.
        """
        data = utils.input_string_or_list(addresses)
        secondaries = []
        for address in data:
            if address == "" or utils.is_ip(address):
                secondaries.append(address)
            else:
                raise AddressValueError("invalid format for IPv6 IP address (%s)" % address)
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
        if not isinstance(address, str):
            raise TypeError("Field ipv6_default_gateway of object NetworkInterface needs to be of type str!")
        if address == "" or utils.is_ip(address):
            self._ipv6_default_gateway = address.strip()
            return
        raise AddressValueError("invalid format of IPv6 IP address (%s)" % address)

    @property
    def ipv6_static_routes(self) -> list:
        """
        ipv6_static_routes property.

        :getter: Returns the value for ``ipv6_static_routes``.
        :setter: Sets the value for the property `ipv6_static_routes``.
        """
        return self._ipv6_static_routes

    @ipv6_static_routes.setter
    def ipv6_static_routes(self, routes: list):
        """
        Setter for the ipv6_static_routes of the NetworkInterface class.

        :param routes: The new static routes for the interface.
        """
        self._ipv6_static_routes = utils.input_string_or_list(routes)

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
        if not isinstance(mtu, str):
            raise TypeError("Field ipv6_mtu of object NetworkInterface needs to be of type str!")
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
        if not isinstance(mtu, str):
            raise TypeError("Field mtu of object NetworkInterface needs to be type str!")
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
            truthiness = utils.input_boolean(truthiness)
        except TypeError as e:
            raise TypeError(
                "Field connected_mode of object NetworkInterface needs to be of type bool!"
            ) from e
        self._connected_mode = truthiness

    def modify_interface(self, _dict: dict):
        """
        Modify the interface

        :param _dict: The dict with the parameter.
        """
        for (key, value) in list(_dict.items()):
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


class System(Item):
    """
    A Cobbler system object.
    """

    # Constants
    TYPE_NAME = "system"
    COLLECTION_TYPE = "system"

    def __init__(self, api, *args, **kwargs):
        """
        Constructor

        :param api: The Cobbler API
        """
        super().__init__(api, *args, **kwargs)
        self._has_initialized = False

        self._interfaces: Dict[str, NetworkInterface] = {}
        self._ipv6_autoconfiguration = False
        self._repos_enabled = False
        self._autoinstall = enums.VALUE_INHERITED
        self._boot_loaders: Union[list, str] = enums.VALUE_INHERITED
        self._enable_ipxe: Union[bool, str] = enums.VALUE_INHERITED
        self._gateway = ""
        self._hostname = ""
        self._image = ""
        self._ipv6_default_device = ""
        self._name_servers = []
        self._name_servers_search = []
        self._netboot_enabled = False
        self._next_server_v4 = enums.VALUE_INHERITED
        self._next_server_v6 = enums.VALUE_INHERITED
        self._filename = enums.VALUE_INHERITED
        self._power_address = ""
        self._power_id = ""
        self._power_pass = ""
        self._power_type = ""
        self._power_user = ""
        self._power_options = ""
        self._power_identity_file = ""
        self._profile = ""
        self._proxy = enums.VALUE_INHERITED
        self._redhat_management_key = enums.VALUE_INHERITED
        self._server = enums.VALUE_INHERITED
        self._status = ""
        self._virt_auto_boot: Union[bool, str] = enums.VALUE_INHERITED
        self._virt_cpus: Union[int, str] = enums.VALUE_INHERITED
        self._virt_disk_driver = enums.VirtDiskDrivers.INHERITED
        self._virt_file_size: Union[float, str] = enums.VALUE_INHERITED
        self._virt_path = enums.VALUE_INHERITED
        self._virt_pxe_boot = False
        self._virt_ram: Union[int, str] = enums.VALUE_INHERITED
        self._virt_type = enums.VirtType.INHERITED
        self._serial_device = -1
        self._serial_baud_rate = enums.BaudRates.DISABLED

        # Overwrite defaults from item.py
        self._owners = enums.VALUE_INHERITED
        self._boot_files = enums.VALUE_INHERITED
        self._fetchable_files = enums.VALUE_INHERITED
        self._autoinstall_meta = enums.VALUE_INHERITED
        self._kernel_options = enums.VALUE_INHERITED
        self._kernel_options_post = enums.VALUE_INHERITED
        self._mgmt_parameters = enums.VALUE_INHERITED
        self._mgmt_classes = enums.VALUE_INHERITED

        if not self._has_initialized:
            self._has_initialized = True

    def __getattr__(self, name):
        if name == "kickstart":
            return self.autoinstall
        elif name == "ks_meta":
            return self.autoinstall_meta
        raise AttributeError("Attribute \"%s\" did not exist on object type System." % name)

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        _dict = self.to_dict()
        cloned = System(self.api)
        cloned.from_dict(_dict)
        cloned.uid = uuid.uuid4().hex
        return cloned

    def from_dict(self, dictionary: dict):
        """
        Initializes the object with attributes from the dictionary.

        :param dictionary: The dictionary with values.
        """
        old_has_initialized = self._has_initialized
        self._has_initialized = False
        if "name" in dictionary:
            self.name = dictionary["name"]
        if "parent" in dictionary:
            self.parent = dictionary["parent"]
        if "profile" in dictionary:
            self.profile = dictionary["profile"]
        if "image" in dictionary:
            self.image = dictionary["image"]
        self._remove_depreacted_dict_keys(dictionary)
        self._has_initialized = old_has_initialized
        super().from_dict(dictionary)

    @LazyProperty
    def parent(self) -> Optional[Item]:
        """
        Return object next highest up the tree. This may be a profile or an image.

        :getter: Returns the value for ``parent``.
        :setter: Sets the value for the property ``parent``.
        :returns: None when there is no parent or the corresponding Item.
        """
        if not self._parent and self.profile:
            return self.api.profiles().find(name=self.profile)
        elif not self._parent and self.image:
            return self.api.images().find(name=self.image)
        elif self._parent:
            # We don't know what type this is, so we need to let find_items() do the magic of guessing that.
            return self.api.find_items(what="", name=self._parent, return_list=False)
        else:
            return None

    @parent.setter
    def parent(self, value: str):
        r"""
        Setter for the ``parent`` property.

        :param value: The name of a profile, an image or another System.
        :raises TypeError: In case value was not of type ``str``.
        :raises ValueError: In case the specified name does not map to an existing profile, image or system.
        """
        if not isinstance(value, str):
            raise TypeError("The name of the parent must be of type str.")
        if not value:
            self._parent = ""
            return
        # FIXME: Add an exists method so we don't need to play try-catch here.
        try:
            self.api.systems().find(name=value)
        except ValueError:
            pass
        try:
            self.api.profiles().find(name=value)
        except ValueError:
            pass
        try:
            self.api.images().find(name=value)
        except ValueError as value_error:
            raise ValueError("Neither a system, profile or image could be found with the name \"%s\"."
                             % value) from value_error
        self._parent = value

    def check_if_valid(self):
        """
        Checks if the current item passes logical validation.

        :raises CX: In case name is missing. Additionally either image or profile is required.
        """
        super().check_if_valid()
        if not self.inmemory:
            return

        # System specific validation
        if self.profile is None or self.profile == "":
            if self.image is None or self.image == "":
                raise CX("Error with system %s - profile or image is required" % self.name)

    #
    # specific methods for item.System
    #

    @LazyProperty
    def interfaces(self) -> Dict[str, NetworkInterface]:
        r"""
        Represents all interfaces owned by the system.

        :getter: The interfaces present. Has at least the ``default`` one.
        :setter: Accepts not only the correct type but also a dict with dicts which will then be converted by the
                 setter.
        """
        return self._interfaces

    @interfaces.setter
    def interfaces(self, value: Dict[str, Any]):
        """
        This methods needs to be able to take a dictionary from ``make_clone()``

        :param value: The new interfaces.
        """
        if not isinstance(value, dict):
            raise TypeError("interfaces must be of type dict")
        dict_values = list(value.values())
        if all(isinstance(x, NetworkInterface) for x in dict_values):
            self._interfaces = value
            return
        if all(isinstance(x, dict) for x in dict_values):
            for key in value:
                network_iface = NetworkInterface(self.api)
                network_iface.from_dict(value[key])
                self._interfaces[key] = network_iface
            return
        raise ValueError("The values of the interfaces must be fully of type dict (one level with values) or "
                         "NetworkInterface objects")

    def modify_interface(self, interface_values: dict):
        """
        Modifies a magic interface dictionary in the form of: {"macaddress-eth0" : "aa:bb:cc:dd:ee:ff"}
        """
        for key in interface_values.keys():
            (_, interface) = key.split("-", 1)
            if interface not in self.interfaces:
                self.__create_interface(interface)
            self.interfaces[interface].modify_interface({key: interface_values[key]})

    def delete_interface(self, name: Union[str, dict]):
        """
        Used to remove an interface.

        :raises TypeError: If the name of the interface is not of type str or dict.
        """
        if isinstance(name, str):
            if not name:
                return
            if name in self.interfaces:
                self.interfaces.pop(name)
                return
        if isinstance(name, dict):
            interface_name = name.get("interface", "")
            self.interfaces.pop(interface_name)
            return
        raise TypeError("The name of the interface must be of type str or dict")

    def rename_interface(self, old_name: str, new_name: str):
        r"""
        Used to rename an interface.

        :raises TypeError: In case on of the params was not a ``str``.
        :raises ValueError: In case the name for the old interface does not exist or the new name does.
        """
        if not isinstance(old_name, str):
            raise TypeError("The old_name of the interface must be of type str")
        if not isinstance(new_name, str):
            raise TypeError("The new_name of the interface must be of type str")
        if old_name not in self.interfaces:
            raise ValueError("Interface \"%s\" does not exist" % old_name)
        if new_name in self.interfaces:
            raise ValueError("Interface \"%s\" already exists" % new_name)
        self.interfaces[new_name] = self.interfaces[old_name]
        del self.interfaces[old_name]

    @LazyProperty
    def hostname(self) -> str:
        """
        hostname property.

        :getter: Returns the value for ``hostname``.
        :setter: Sets the value for the property ``hostname``.
        :return:
        """
        return self._hostname

    @hostname.setter
    def hostname(self, value: str):
        """
        Setter for the hostname of the System class.


        :param value:
        """
        if not isinstance(value, str):
            raise TypeError("Field hostname of object system needs to be of type str!")
        self._hostname = value

    @LazyProperty
    def status(self) -> str:
        """
        status property.

        :getter: Returns the value for ``status``.
        :setter: Sets the value for the property ``status``.
        :return:
        """
        return self._status

    @status.setter
    def status(self, status: str):
        """
        Setter for the status of the System class.


        :param status:
        """
        if not isinstance(status, str):
            raise TypeError("Field status of object system needs to be of type str!")
        self._status = status

    @InheritableProperty
    def boot_loaders(self) -> list:
        """
        boot_loaders property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``boot_loaders``.
        :setter: Sets the value for the property ``boot_loaders``.
        :return:
        """
        return self._resolve("boot_loaders")

    @boot_loaders.setter
    def boot_loaders(self, boot_loaders: Union[str, list]):
        """
        Setter of the boot loaders.

        :param boot_loaders: The boot loaders for the system.
        :raises CX: This is risen in case the bootloaders set are not valid ones.
        """
        if not isinstance(boot_loaders, (str, list)):
            raise TypeError("The bootloaders need to be either a str or list")

        if boot_loaders == enums.VALUE_INHERITED:
            self._boot_loaders = enums.VALUE_INHERITED
            return

        if boot_loaders == "" or boot_loaders == []:
            self._boot_loaders = []
            return

        if isinstance(boot_loaders, str):
            boot_loaders_split = utils.input_string_or_list(boot_loaders)
        else:
            boot_loaders_split = boot_loaders

        parent = self.parent
        if parent is not None:
            parent_boot_loaders = parent.boot_loaders
        else:
            self.logger.warning(
                'Parent of System "%s" could not be found for resolving the parent bootloaders.',
                self.name,
            )
            parent_boot_loaders = []
        if not set(boot_loaders_split).issubset(parent_boot_loaders):
            raise CX(
                'Error with system "%s" - not all boot_loaders are supported (given: "%s"; supported:'
                '"%s")' % (self.name, str(boot_loaders_split), str(parent_boot_loaders))
            )
        self._boot_loaders = boot_loaders_split

    @InheritableProperty
    def server(self) -> str:
        """
        server property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``server``.
        :setter: Sets the value for the property ``server``.
        """
        return self._resolve("server")

    @server.setter
    def server(self, server: str):
        """
        If a system can't reach the boot server at the value configured in settings
        because it doesn't have the same name on it's subnet this is there for an override.

        :param server:
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):
            raise TypeError("Field server of object system needs to be of type str!")
        if server == "":
            server = enums.VALUE_INHERITED
        self._server = server

    @InheritableProperty
    def next_server_v4(self) -> str:
        """
        next_server_v4 property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``next_server_v4``.
        :setter: Sets the value for the property ``next_server_v4``.
        """
        return self._resolve("next_server_v4")

    @next_server_v4.setter
    def next_server_v4(self, server: str = ""):
        """
        Setter for the IPv4 next server. See profile.py for more details.

        :param server: The address of the IPv4 next server. Must be a string or ``enums.VALUE_INHERITED``.
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):
            raise TypeError("next_server_v4 must be a string.")
        if server == enums.VALUE_INHERITED:
            self._next_server_v4 = enums.VALUE_INHERITED
        else:
            self._next_server_v4 = validate.ipv4_address(server)

    @InheritableProperty
    def next_server_v6(self) -> str:
        """
        next_server_v6 property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``next_server_v6``.
        :setter: Sets the value for the property ``next_server_v6``.
        """
        return self._resolve("next_server_v6")

    @next_server_v6.setter
    def next_server_v6(self, server: str = ""):
        """
        Setter for the IPv6 next server. See profile.py for more details.

        :param server: The address of the IPv6 next server. Must be a string or ``enums.VALUE_INHERITED``.
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):
            raise TypeError("next_server_v6 must be a string.")
        if server == enums.VALUE_INHERITED:
            self._next_server_v6 = enums.VALUE_INHERITED
        else:
            self._next_server_v6 = validate.ipv6_address(server)

    @InheritableProperty
    def filename(self) -> str:
        """
        filename property.

        :getter: Returns the value for ``filename``.
        :setter: Sets the value for the property ``filename``.
        """
        return self._resolve("filename")

    @filename.setter
    def filename(self, filename: str):
        """
        Setter for the filename of the System class.

        :param filename:
        :raises TypeError: In case filename is no string.
        """
        if not isinstance(filename, str):
            raise TypeError("Field filename of object system needs to be of type str!")
        if not filename:
            self._filename = enums.VALUE_INHERITED
        else:
            self._filename = filename.strip()

    @InheritableProperty
    def proxy(self) -> str:
        """
        proxy property. This corresponds per default to the setting``proxy_url_int``.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``proxy``.
        :setter: Sets the value for the property ``proxy``.
        """
        return self._resolve("proxy_url_int")

    @proxy.setter
    def proxy(self, proxy: str):
        """
        Setter for the proxy of the System class.

        :param proxy: The new value for the proxy.
        :raises TypeError: In case proxy is no string.
        """
        if not isinstance(proxy, str):
            raise TypeError("Field proxy of object system needs to be of type str!")
        self._proxy = proxy

    @InheritableProperty
    def redhat_management_key(self) -> str:
        """
        redhat_management_key property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``redhat_management_key``.
        :setter: Sets the value for the property ``redhat_management_key``.
        """
        return self._resolve("redhat_management_key")

    @redhat_management_key.setter
    def redhat_management_key(self, management_key: str):
        """
        Setter for the redhat_management_key of the System class.

        :param management_key: The new value for the redhat management key
        :raises TypeError: In case management_key is no string.
        """
        if not isinstance(management_key, str):
            raise TypeError("Field redhat_management_key of object system needs to be of type str!")
        if management_key is None or management_key == "":
            self._redhat_management_key = enums.VALUE_INHERITED
        self._redhat_management_key = management_key

    def get_mac_address(self, interface: str):
        """
        Get the mac address, which may be implicit in the object name or explicit with --mac-address.
        Use the explicit location first.

        :param interface: The name of the interface to get the MAC of.
        """

        intf = self.__get_interface(interface)

        if intf.mac_address != "":
            return intf.mac_address.strip()
        else:
            return None

    def get_ip_address(self, interface: str):
        """
        Get the IP address for the given interface.

        :param interface: The name of the interface to get the IP address of.
        """
        intf = self.__get_interface(interface)
        if intf.ip_address:
            return intf.ip_address.strip()
        else:
            return ""

    def is_management_supported(self, cidr_ok: bool = True) -> bool:
        """
        Can only add system PXE records if a MAC or IP address is available, else it's a koan only record.

        :param cidr_ok: Deprecated parameter which is not used anymore.
        """
        if self.name == "default":
            return True
        for interface in self.interfaces.values():
            mac = interface.mac_address
            ip_v4 = interface.ip_address
            ip_v6 = interface.ipv6_address
            if mac or ip_v4 or ip_v6:
                return True
        return False

    def __create_interface(self, interface: str):
        """
        Create or overwrites a network interface.

        :param interface: The name of the interface
        """
        self.interfaces[interface] = NetworkInterface(self.api)

    def __get_interface(self, interface_name: str = "default") -> NetworkInterface:
        """
        Tries to retrieve an interface and creates it in case the interface doesn't exist. If no name is given the
        default interface is retrieved.

        :param interface_name: The name of the interface. If ``None`` is given then ``default`` is used.
        :raises TypeError: In case interface_name is no string.
        :return: The requested interface.
        """
        if interface_name is None:
            interface_name = "default"
        if not isinstance(interface_name, str):
            raise TypeError("The name of an interface must always be of type str!")
        if not interface_name:
            interface_name = "default"
        if interface_name not in self._interfaces:
            self.__create_interface(interface_name)
        return self._interfaces[interface_name]

    @LazyProperty
    def gateway(self):
        """
        gateway property.

        :getter: Returns the value for ``gateway``.
        :setter: Sets the value for the property ``gateway``.
        :return:
        """
        return self._gateway

    @gateway.setter
    def gateway(self, gateway: str):
        """
        Set a gateway IPv4 address.

        :param gateway: IP address
        :returns: True or CX
        """
        self._gateway = validate.ipv4_address(gateway)

    @LazyProperty
    def name_servers(self) -> list:
        """
        name_servers property.
        FIXME: Differentiate between IPv4/6

        :getter: Returns the value for ``name_servers``.
        :setter: Sets the value for the property ``name_servers``.
        :return:
        """
        return self._name_servers

    @name_servers.setter
    def name_servers(self, data: Union[str, list]):
        """
        Set the DNS servers.
        FIXME: Differentiate between IPv4/6

        :param data: string or list of nameservers
        :returns: True or CX
        """
        self._name_servers = validate.name_servers(data)

    @LazyProperty
    def name_servers_search(self) -> list:
        """
        name_servers_search property.

        :getter: Returns the value for ``name_servers_search``.
        :setter: Sets the value for the property ``name_servers_search``.
        :return:
        """
        return self._name_servers_search

    @name_servers_search.setter
    def name_servers_search(self, data: Union[str, list]):
        """
        Set the DNS search paths.

        :param data: string or list of search domains
        :returns: True or CX
        """
        self._name_servers_search = validate.name_servers_search(data)

    @LazyProperty
    def ipv6_autoconfiguration(self) -> bool:
        """
        ipv6_autoconfiguration property.

        :getter: Returns the value for ``ipv6_autoconfiguration``.
        :setter: Sets the value for the property ``ipv6_autoconfiguration``.
        :return:
        """
        return self._ipv6_autoconfiguration

    @ipv6_autoconfiguration.setter
    def ipv6_autoconfiguration(self, value: bool):
        """
        Setter for the ipv6_autoconfiguration of the System class.


        :param value:
        """
        value = utils.input_boolean(value)
        if not isinstance(value, bool):
            raise TypeError("ipv6_autoconfiguration needs to be of type bool")
        self._ipv6_autoconfiguration = value

    @LazyProperty
    def ipv6_default_device(self) -> str:
        """
        ipv6_default_device property.

        :getter: Returns the value for ``ipv6_default_device``.
        :setter: Sets the value for the property ``ipv6_default_device``.
        :return:
        """
        return self._ipv6_default_device

    @ipv6_default_device.setter
    def ipv6_default_device(self, interface_name: str):
        """
        Setter for the ipv6_default_device of the System class.


        :param interface_name:
        """
        if not isinstance(interface_name, str):
            raise TypeError("Field ipv6_default_device of object system needs to be of type str!")
        if interface_name is None:
            interface_name = ""
        self._ipv6_default_device = interface_name

    @InheritableProperty
    def enable_ipxe(self) -> bool:
        """
        enable_ipxe property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``enable_ipxe``.
        :setter: Sets the value for the property ``enable_ipxe``.
        :return:
        """
        return self._resolve("enable_ipxe")

    @enable_ipxe.setter
    def enable_ipxe(self, enable_ipxe: bool):
        """
        Sets whether the system will use iPXE for booting.

        :param enable_ipxe: If ipxe should be enabled or not.
        :raises TypeError: In case enable_ipxe is not a boolean.
        """
        enable_ipxe = utils.input_boolean(enable_ipxe)
        if not isinstance(enable_ipxe, bool):
            raise TypeError("enable_ipxe needs to be of type bool")
        self._enable_ipxe = enable_ipxe

    @LazyProperty
    def profile(self) -> str:
        """
        profile property.

        :getter: Returns the value for ``profile``.
        :setter: Sets the value for the property ``profile``.
        :return:
        """
        return self._profile

    @profile.setter
    def profile(self, profile_name: str):
        """
        Set the system to use a certain named profile. The profile must have already been loaded into the profiles
        collection.

        :param profile_name: The name of the profile which the system is underneath.
        :raises TypeError: In case profile_name is no string.
        :raises ValueError: In case profile_name does not exist.
        """
        if not isinstance(profile_name, str):
            raise TypeError("The name of a profile needs to be of type str.")

        if profile_name in ["delete", "None", "~", ""]:
            self._profile = ""
            return

        profile = self.api.profiles().find(name=profile_name)
        if profile is None:
            raise ValueError(
                'Profile with the name "%s" is not existing' % profile_name
            )

        old_parent = self.parent
        if isinstance(old_parent, Item):
            if self.name in old_parent.children:
                old_parent.children.remove(self.name)
            else:
                self.logger.debug(
                    'Name of System "%s" was not found in the children of Item "%s"',
                    self.name,
                    self.parent.name,
                )
        else:
            self.logger.debug(
                'Parent of System "%s" not found. Thus skipping removal from children list.',
                self.name,
            )

        self.image = ""  # mutual exclusion rule

        self._profile = profile_name
        self.depth = profile.depth + 1  # subprofiles have varying depths.
        new_parent = self.parent
        if isinstance(new_parent, Item) and self.name not in new_parent.children:
            new_parent.children.append(self.name)

    @LazyProperty
    def image(self) -> str:
        """
        image property.

        :getter: Returns the value for ``image``.
        :setter: Sets the value for the property ``image``.
        :return:
        """
        return self._image

    @image.setter
    def image(self, image_name: str):
        """
        Set the system to use a certain named image. Works like ``set_profile()`` but cannot be used at the same time.
        It's one or the other.

        :param image_name: The name of the image which will act as a parent.
        :raises ValueError: In case the image name was invalid.
        :raises TypeError: In case image_name is no string.
        """
        if not isinstance(image_name, str):
            raise TypeError("The name of an image must be of type str.")

        if image_name in ["delete", "None", "~", ""]:
            self._image = ""
            return

        img = self.api.images().find(name=image_name)
        if img is None:
            raise ValueError('Image with the name "%s" is not existing' % image_name)

        old_parent = self.parent
        if isinstance(old_parent, Item):
            if self.name in old_parent.children:
                old_parent.children.remove(self.name)
            else:
                self.logger.debug(
                    'Name of System "%s" was not found in the children of Item "%s"',
                    self.name,
                    self.parent.name,
                )
        else:
            self.logger.debug(
                'Parent of System "%s" not found. Thus skipping removal from children list.',
                self.name,
            )

        self.profile = ""  # mutual exclusion rule

        self._image = image_name
        self.depth = img.depth + 1
        new_parent = self.parent
        if isinstance(new_parent, Item) and self.name not in new_parent.children:
            new_parent.children.append(self.name)

    @InheritableProperty
    def virt_cpus(self) -> int:
        """
        virt_cpus property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``virt_cpus``.
        :setter: Sets the value for the property ``virt_cpus``.
        """
        return self._resolve("virt_cpus")

    @virt_cpus.setter
    def virt_cpus(self, num: int):
        """
        Setter for the virt_cpus of the System class.

        :param num: The new value for the number of CPU cores.
        """
        self._virt_cpus = validate.validate_virt_cpus(num)

    @InheritableProperty
    def virt_file_size(self) -> float:
        """
        virt_file_size property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``virt_file_size``.
        :setter: Sets the value for the property ``virt_file_size``.
        """
        return self._resolve("virt_file_size")

    @virt_file_size.setter
    def virt_file_size(self, num: float):
        """
        Setter for the virt_file_size of the System class.


        :param num:
        """
        self._virt_file_size = validate.validate_virt_file_size(num)

    @InheritableProperty
    def virt_disk_driver(self) -> enums.VirtDiskDrivers:
        """
        virt_disk_driver property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``virt_disk_driver``.
        :setter: Sets the value for the property ``virt_disk_driver``.
        """
        return self._resolve_enum("virt_disk_driver", enums.VirtDiskDrivers)

    @virt_disk_driver.setter
    def virt_disk_driver(self, driver: Union[str, enums.VirtDiskDrivers]):
        """
        Setter for the virt_disk_driver of the System class.

        :param driver: The new disk driver for the virtual disk.
        """
        self._virt_disk_driver = enums.VirtDiskDrivers.to_enum(driver)

    @InheritableProperty
    def virt_auto_boot(self) -> bool:
        """
        virt_auto_boot property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``virt_auto_boot``.
        :setter: Sets the value for the property ``virt_auto_boot``.
        """
        return self._resolve("virt_auto_boot")

    @virt_auto_boot.setter
    def virt_auto_boot(self, value: bool):
        """
        Setter for the virt_auto_boot of the System class.

        :param value: Weather the VM should automatically boot or not.
        """
        if value == enums.VALUE_INHERITED:
            self._virt_auto_boot = enums.VALUE_INHERITED
            return
        self._virt_auto_boot = validate.validate_virt_auto_boot(value)

    @LazyProperty
    def virt_pxe_boot(self) -> bool:
        """
        virt_pxe_boot property.

        :getter: Returns the value for ``virt_pxe_boot``.
        :setter: Sets the value for the property ``virt_pxe_boot``.
        """
        return self._virt_pxe_boot

    @virt_pxe_boot.setter
    def virt_pxe_boot(self, num: bool):
        """
        Setter for the virt_pxe_boot of the System class.

        :param num:
        """
        self._virt_pxe_boot = validate.validate_virt_pxe_boot(num)

    @InheritableProperty
    def virt_ram(self) -> int:
        """
        virt_ram property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``virt_ram``.
        :setter: Sets the value for the property ``virt_ram``.
        """
        return self._resolve("virt_ram")

    @virt_ram.setter
    def virt_ram(self, num: Union[int, str]):
        """
        Setter for the virt_ram of the System class.


        :param num:
        """
        self._virt_ram = validate.validate_virt_ram(num)

    @InheritableProperty
    def virt_type(self) -> enums.VirtType:
        """
        virt_type property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``virt_type``.
        :setter: Sets the value for the property ``virt_type``.
        """
        return self._resolve_enum("virt_type", enums.VirtType)

    @virt_type.setter
    def virt_type(self, vtype: Union[enums.VirtType, str]):
        """
        Setter for the virt_type of the System class.

        :param vtype: The new virtual type.
        """
        self._virt_type = enums.VirtType.to_enum(vtype)

    @InheritableProperty
    def virt_path(self) -> str:
        """
        virt_path property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``virt_path``.
        :setter: Sets the value for the property ``virt_path``.
        """
        return self._resolve("virt_path")

    @virt_path.setter
    def virt_path(self, path: str):
        """
        Setter for the virt_path of the System class.

        :param path: The new path.
        """
        self._virt_path = validate.validate_virt_path(path, for_system=True)

    @LazyProperty
    def netboot_enabled(self) -> bool:
        """
        netboot_enabled property.

        :getter: Returns the value for ``netboot_enabled``.
        :setter: Sets the value for the property ``netboot_enabled``.
        """
        return self._netboot_enabled

    @netboot_enabled.setter
    def netboot_enabled(self, netboot_enabled: bool):
        """
        If true, allows per-system PXE files to be generated on sync (or add). If false, these files are not generated,
        thus eliminating the potential for an infinite install loop when systems are set to PXE boot first in the boot
        order. In general, users who are PXE booting first in the boot order won't create system definitions, so this
        feature primarily comes into play for programmatic users of the API, who want to initially create a system with
        netboot enabled and then disable it after the system installs, as triggered by some action in automatic
        installation file's %post section. For this reason, this option is not urfaced in the CLI, output, or
        documentation (yet).

        Use of this option does not affect the ability to use PXE menus. If an admin has machines set up to PXE only
        after local boot fails, this option isn't even relevant.

        :param: netboot_enabled:
        :raises TypeError: In case netboot_enabled is not a boolean.
        """
        netboot_enabled = utils.input_boolean(netboot_enabled)
        if not isinstance(netboot_enabled, bool):
            raise TypeError("netboot_enabled needs to be a bool")
        self._netboot_enabled = netboot_enabled

    @InheritableProperty
    def autoinstall(self) -> str:
        """
        autoinstall property.

        :getter: Returns the value for ``autoinstall``.
        :setter: Sets the value for the property ``autoinstall``.
        :return:
        """
        return self._resolve("autoinstall")

    @autoinstall.setter
    def autoinstall(self, autoinstall: str):
        """
        Set the automatic installation template filepath, this must be a local file.

        :param autoinstall: local automatic installation template file path
        """
        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(self.api)
        self._autoinstall = autoinstall_mgr.validate_autoinstall_template_file_path(autoinstall)

    @LazyProperty
    def power_type(self) -> str:
        """
        power_type property.

        :getter: Returns the value for ``power_type``.
        :setter: Sets the value for the property ``power_type``.
        :return:
        """
        return self._power_type

    @power_type.setter
    def power_type(self, power_type: str):
        """
        Setter for the power_type of the System class.


        :param power_type:
        :raises TypeError: In case power_type is no string.
        """
        if not isinstance(power_type, str):
            raise TypeError("power_type must be of type str")
        if not power_type:
            self._power_type = ""
            return
        power_manager.validate_power_type(power_type)
        self._power_type = power_type

    @LazyProperty
    def power_identity_file(self) -> str:
        """
        power_identity_file property.

        :getter: Returns the value for ``power_identity_file``.
        :setter: Sets the value for the property ``power_identity_file``.
        :return:
        """
        return self._power_identity_file

    @power_identity_file.setter
    def power_identity_file(self, power_identity_file: str):
        """
        Setter for the power_identity_file of the System class.


        :param power_identity_file:
        :raises TypeError: In case power_identity_file is no string.
        """
        if not isinstance(power_identity_file, str):
            raise TypeError("Field power_identity_file of object system needs to be of type str!")
        utils.safe_filter(power_identity_file)
        self._power_identity_file = power_identity_file

    @LazyProperty
    def power_options(self) -> str:
        """
        power_options property.

        :getter: Returns the value for ``power_options``.
        :setter: Sets the value for the property ``power_options``.
        :return:
        """
        return self._power_options

    @power_options.setter
    def power_options(self, power_options: str):
        """
        Setter for the power_options of the System class.


        :param power_options:
        :raises TypeError: In case power_options is no string.
        """
        if not isinstance(power_options, str):
            raise TypeError("Field power_options of object system needs to be of type str!")
        utils.safe_filter(power_options)
        self._power_options = power_options

    @LazyProperty
    def power_user(self) -> str:
        """
        power_user property.

        :getter: Returns the value for ``power_user``.
        :setter: Sets the value for the property ``power_user``.
        :return:
        """
        return self._power_user

    @power_user.setter
    def power_user(self, power_user: str):
        """
        Setter for the power_user of the System class.


        :param power_user:
        :raises TypeError: In case power_user is no string.
        """
        if not isinstance(power_user, str):
            raise TypeError("Field power_user of object system needs to be of type str!")
        utils.safe_filter(power_user)
        self._power_user = power_user

    @LazyProperty
    def power_pass(self) -> str:
        """
        power_pass property.

        :getter: Returns the value for ``power_pass``.
        :setter: Sets the value for the property ``power_pass``.
        :return:
        """
        return self._power_pass

    @power_pass.setter
    def power_pass(self, power_pass: str):
        """
        Setter for the power_pass of the System class.


        :param power_pass:
        :raises TypeError: In case power_pass is no string.
        """
        if not isinstance(power_pass, str):
            raise TypeError("Field power_pass of object system needs to be of type str!")
        utils.safe_filter(power_pass)
        self._power_pass = power_pass

    @LazyProperty
    def power_address(self) -> str:
        """
        power_address property.

        :getter: Returns the value for ``power_address``.
        :setter: Sets the value for the property ``power_address``.
        :return:
        """
        return self._power_address

    @power_address.setter
    def power_address(self, power_address: str):
        """
        Setter for the power_address of the System class.


        :param power_address:
        :raises TypeError: In case power_address is no string.
        """
        if not isinstance(power_address, str):
            raise TypeError("Field power_address of object system needs to be of type str!")
        utils.safe_filter(power_address)
        self._power_address = power_address

    @LazyProperty
    def power_id(self) -> str:
        """
        power_id property.

        :getter: Returns the value for ``power_id``.
        :setter: Sets the value for the property ``power_id``.
        :return:
        """
        return self._power_id

    @power_id.setter
    def power_id(self, power_id: str):
        """
        Setter for the power_id of the System class.


        :param power_id:
        :raises TypeError: In case power_id is no string.
        """
        if not isinstance(power_id, str):
            raise TypeError("Field power_id of object system needs to be of type str!")
        utils.safe_filter(power_id)
        self._power_id = power_id

    @LazyProperty
    def repos_enabled(self) -> bool:
        """
        repos_enabled property.

        :getter: Returns the value for ``repos_enabled``.
        :setter: Sets the value for the property ``repos_enabled``.
        :return:
        """
        return self._repos_enabled

    @repos_enabled.setter
    def repos_enabled(self, repos_enabled: bool):
        """
        Setter for the repos_enabled of the System class.


        :param repos_enabled:
        :raises TypeError: In case is no string.
        """
        repos_enabled = utils.input_boolean(repos_enabled)
        if not isinstance(repos_enabled, bool):
            raise TypeError("Field repos_enabled of object system needs to be of type bool!")
        self._repos_enabled = repos_enabled

    @LazyProperty
    def serial_device(self) -> int:
        """
        serial_device property. "-1" disables the serial device functionality completely.

        :getter: Returns the value for ``serial_device``.
        :setter: Sets the value for the property ``serial_device``.
        """
        return self._serial_device

    @serial_device.setter
    def serial_device(self, device_number: int):
        """
        Setter for the serial_device of the System class.

        :param device_number: The number of the device which is going
        """
        self._serial_device = validate.validate_serial_device(device_number)

    @LazyProperty
    def serial_baud_rate(self) -> enums.BaudRates:
        """
        serial_baud_rate property. The value "disabled" will disable the functionality completely.

        :getter: Returns the value for ``serial_baud_rate``.
        :setter: Sets the value for the property ``serial_baud_rate``.
        """
        return self._serial_baud_rate

    @serial_baud_rate.setter
    def serial_baud_rate(self, baud_rate: int):
        """
        Setter for the serial_baud_rate of the System class.


        :param baud_rate:
        """
        self._serial_baud_rate = validate.validate_serial_baud_rate(baud_rate)

    @LazyProperty
    def children(self) -> List[str]:
        """
        children property.

        :getter: Returns the value for ``children``.
        :setter: Sets the value for the property ``children``.
        :return:
        """
        return self._children

    @children.setter
    def children(self, value: List[str]):
        """
        Setter for the children of the System class.


        :param value:
        """
        self._children = value

    def get_config_filename(self, interface: str, loader: Optional[str] = None):
        """
        The configuration file for each system pxe uses is either a form of the MAC address or the hex version or the
        IP address. If none of that is available, just use the given name, though the name given will be unsuitable for
        PXE
        configuration (For this, check system.is_management_supported()). This same file is used to store system config
        information in the Apache tree, so it's still relevant.

        :param interface: Name of the interface.
        :param loader: Bootloader type.
        """
        boot_loaders = self.boot_loaders
        if loader is None:
            if "grub" in boot_loaders or len(boot_loaders) < 1:
                loader = "grub"
            else:
                loader = boot_loaders[0]

        if interface not in self.interfaces:
            self.logger.warning(
                'System "%s" did not have an interface with the name "%s" attached to it.',
                self.name,
                interface,
            )
            return None

        if self.name == "default":
            if loader == "grub":
                return None
            return "default"

        mac = self.get_mac_address(interface)
        ip = self.get_ip_address(interface)
        if mac is not None and mac != "":
            if loader == "grub":
                return mac.lower()
            else:
                return "01-" + "-".join(mac.split(":")).lower()
        elif ip is not None and ip != "":
            return utils.get_host_ip(ip)
        else:
            return self.name
