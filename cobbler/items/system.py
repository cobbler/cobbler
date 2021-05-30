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
import enum
import logging
import uuid
from typing import Any, Dict, Optional, Union

from cobbler import autoinstall_manager, enums, power_manager, utils, validate
from cobbler.cexceptions import CX
from cobbler.items.item import Item

from ipaddress import AddressValueError


class NetworkInterface:
    """
    A subobject of a Cobbler System which represents the network interfaces
    """

    def __init__(self, api):
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
        TODO

        :param dictionary:
        """
        dictionary_keys = list(dictionary.keys())
        for key in dictionary:
            if hasattr(self, key):
                setattr(self, key, dictionary[key])
                dictionary_keys.remove(key)
        if len(dictionary_keys) > 0:
            self.__logger.info("The following keys were ignored and could not be set for the NetworkInterface object: "
                               "%s", str(dictionary_keys))

    def to_dict(self) -> dict:
        """
        TODO

        :return:
        """
        result = {}
        for key in self.__dict__:
            if "__" in key:
                continue
            if key.startswith("_"):
                if isinstance(self.__dict__[key], enum.Enum):
                    result[key[1:]] = self.__dict__[key].value
                else:
                    result[key[1:]] = self.__dict__[key]
        return result

    @property
    def dhcp_tag(self):
        """
        TODO

        :return:
        """
        return self._dhcp_tag

    @dhcp_tag.setter
    def dhcp_tag(self, dhcp_tag):
        """
        TODO

        :param dhcp_tag:
        """
        self._dhcp_tag = dhcp_tag

    @property
    def cnames(self):
        """
        TODO

        :return:
        """
        return self._cnames

    @cnames.setter
    def cnames(self, cnames):
        """
        TODO

        :param cnames:
        """
        self._cnames = utils.input_string_or_list(cnames)

    @property
    def static_routes(self):
        """
        TODO

        :return:
        """
        return self._static_routes

    @static_routes.setter
    def static_routes(self, routes):
        """
        TODO

        :param routes:
        """
        self._static_routes = utils.input_string_or_list(routes)

    @property
    def static(self):
        """
        TODO

        :return:
        """
        return self._static

    @static.setter
    def static(self, truthiness):
        self._static = utils.input_boolean(truthiness)

    @property
    def management(self):
        """
        TODO

        :return:
        """
        return self._management

    @management.setter
    def management(self, truthiness):
        """
        TODO

        :param truthiness:
        """
        self._management = utils.input_boolean(truthiness)

    @property
    def dns_name(self):
        """
        TODO

        :return:
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
        if dns_name != "" and not self.__api.settings().allow_duplicate_hostname:
            matched = self.__api.find_items("system", {"dns_name": dns_name})
            for x in matched:
                # FIXME: The check for the system does not work yet.
                if x.name != self.name:
                    raise ValueError("DNS name duplicated: %s" % dns_name)
        self._dns_name = dns_name

    @property
    def ip_address(self):
        """
        TODO

        :return:
        """
        return self._ip_address

    @ip_address.setter
    def ip_address(self, address: str):
        """
        Set IPv4 address on interface.

        :param address: IP address
        :raises ValueError: In case the ip address is already existing inside Cobbler.
        """
        address = validate.ipv4_address(address)
        if address != "" and not self.__api.settings().allow_duplicate_ips:
            matched = self.__api.find_items("system", {"ip_address": address})
            for x in matched:
                # FIXME: The check for the system does not work yet.
                if x.name != self.name:
                    raise ValueError("IP address duplicated: %s" % address)
        self._ip_address = address

    @property
    def mac_address(self):
        """
        TODO

        :return:
        """
        return self._mac_address

    @mac_address.setter
    def mac_address(self, address):
        """
        Set MAC address on interface.

        :param address: MAC address
        :raises CX:
        """
        address = validate.mac_address(address)
        if address == "random":
            address = utils.get_random_mac(self.__api)
        if address != "" and not self.__api.settings().allow_duplicate_macs:
            matched = self.__api.find_items("system", {"mac_address": address})
            for x in matched:
                # FIXME: The check for the system does not work yet.
                if x.name != self.name:
                    raise CX("MAC address duplicated: %s" % address)
        self._mac_address = address

    @property
    def netmask(self):
        """
        TODO

        :return:
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
    def if_gateway(self):
        """
        TODO

        :return:
        """
        return self._if_gateway

    @if_gateway.setter
    def if_gateway(self, gateway: str):
        """
        Set the per-interface gateway.

        :param gateway: IPv4 address for the gateway
        :returns: True or CX
        """
        self._if_gateway = validate.ipv4_address(gateway)

    @property
    def virt_bridge(self):
        """
        TODO

        :return:
        """
        return self._virt_bridge

    @virt_bridge.setter
    def virt_bridge(self, bridge: str):
        """
        TODO

        :param bridge:
        """
        if bridge == "":
            bridge = self.__api.settings().default_virt_bridge
        self._virt_bridge = bridge

    @property
    def interface_type(self):
        """
        TODO

        :return:
        """
        return self._interface_type

    @interface_type.setter
    def interface_type(self, intf_type: Union[enums.NetworkInterfaceType, int, str]):
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
        # Now it must be of the enum Type
        if intf_type not in enums.NetworkInterfaceType:
            raise ValueError("interface intf_type value must be one of: %s or blank" %
                             ",".join(list(map(str, enums.NetworkInterfaceType))))
        self._interface_type = intf_type

    @property
    def interface_master(self):
        """
        TODO

        :return:
        """
        return self._interface_master

    @interface_master.setter
    def interface_master(self, interface_master):
        """
        TODO

        :param interface_master:
        """
        self._interface_master = interface_master

    @property
    def bonding_opts(self):
        """
        TODO

        :return:
        """
        return self._bonding_opts

    @bonding_opts.setter
    def bonding_opts(self, bonding_opts):
        self._bonding_opts = bonding_opts

    @property
    def bridge_opts(self):
        """
        TODO

        :return:
        """
        return self._bridge_opts

    @bridge_opts.setter
    def bridge_opts(self, bridge_opts):
        self._bridge_opts = bridge_opts

    @property
    def ipv6_address(self):
        """
        TODO

        :return:
        """
        return self._ipv6_address

    @ipv6_address.setter
    def ipv6_address(self, address: str):
        """
        Set IPv6 address on interface.

        :param address: IP address
        :raises CX
        """
        address = validate.ipv6_address(address)
        if address != "" and self.__api.settings().allow_duplicate_ips is False:
            # FIXME: The check for the system does not work yet.
            matched = self.__api.find_items("system", {"ipv6_address": address})
            for x in matched:
                if x.name != self.name:
                    raise CX("IP address duplicated: %s" % address)
        self._ipv6_address = address

    @property
    def ipv6_prefix(self):
        """
        TODO

        :return:
        """
        return self._ipv6_address

    @ipv6_prefix.setter
    def ipv6_prefix(self, prefix):
        """
        Assign a IPv6 prefix
        """
        self._ipv6_prefix = prefix.strip()

    @property
    def ipv6_secondaries(self):
        """
        TODO

        :return:
        """
        return self._ipv6_secondaries

    @ipv6_secondaries.setter
    def ipv6_secondaries(self, addresses):
        data = utils.input_string_or_list(addresses)
        secondaries = []
        for address in data:
            if address == "" or utils.is_ip(address):
                secondaries.append(address)
            else:
                raise AddressValueError("invalid format for IPv6 IP address (%s)" % address)
        self._ipv6_secondaries = secondaries

    @property
    def ipv6_default_gateway(self):
        """
        TODO

        :return:
        """
        return self._ipv6_default_gateway

    @ipv6_default_gateway.setter
    def ipv6_default_gateway(self, address):
        if address == "" or utils.is_ip(address):
            self._ipv6_default_gateway = address.strip()
            return
        raise AddressValueError("invalid format for IPv6 IP address (%s)" % address)

    @property
    def ipv6_static_routes(self):
        """
        TODO

        :return:
        """
        return self._ipv6_static_routes

    @ipv6_static_routes.setter
    def ipv6_static_routes(self, routes):
        """
        TODO

        :param routes:
        """
        self._ipv6_static_routes = utils.input_string_or_list(routes)

    @property
    def ipv6_mtu(self):
        """
        TODO

        :return:
        """
        return self._ipv6_mtu

    @ipv6_mtu.setter
    def ipv6_mtu(self, mtu):
        self._ipv6_mtu = mtu

    @property
    def mtu(self):
        """
        TODO

        :return:
        """
        return self._mtu

    @mtu.setter
    def mtu(self, mtu):
        self._mtu = mtu

    @property
    def connected_mode(self):
        """
        TODO

        :return:
        """
        return self._connected_mode

    @connected_mode.setter
    def connected_mode(self, truthiness):
        self._connected_mode = utils.input_boolean(truthiness)

    def modify_interface(self, _dict: dict):
        """
        Used by the WUI to modify an interface more-efficiently
        """
        for (key, value) in list(_dict.items()):
            (field, interface) = key.split("-", 1)
            field = field.replace("_", "").replace("-", "")

            if field == "bondingopts":
                self.bonding_opts = value
            if field == "bridgeopts":
                self.bridge_opts = value
            if field == "connected_mode":
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

    COLLECTION_TYPE = "system"

    def __init__(self, api, *args, **kwargs):
        super().__init__(api, *args, **kwargs)
        self._interfaces: Dict[str, NetworkInterface] = {"default": NetworkInterface(api)}
        self._ipv6_autoconfiguration = False
        self._repos_enabled = False
        self._autoinstall = ""
        self._boot_loaders = []
        self._enable_ipxe = False
        self._gateway = ""
        self._hostname = ""
        self._image = ""
        self._ipv6_default_device = ""
        self._name_servers = []
        self._name_servers_search = []
        self._netboot_enabled = False
        self._next_server_v4 = ""
        self._next_server_v6 = ""
        self._filename = ""
        self._power_address = ""
        self._power_id = ""
        self._power_pass = ""
        self._power_type = ""
        self._power_user = ""
        self._power_options = ""
        self._power_identity_file = ""
        self._profile = ""
        self._proxy = ""
        self._redhat_management_key = ""
        self._server = ""
        self._status = ""
        self._virt_auto_boot = False
        self._virt_cpus = 0
        self._virt_disk_driver = enums.VirtDiskDrivers.INHERTIED
        self._virt_file_size = 0.0
        self._virt_path = ""
        self._virt_pxe_boot = False
        self._virt_ram = 0
        self._virt_type = enums.VirtType.AUTO
        self._serial_device = 0
        self._serial_baud_rate = enums.BaudRates.B0

    def __getattr__(self, name):
        if name == "kickstart":
            return self.autoinstall
        elif name == "ks_meta":
            return self.autoinstall_meta
        return self[name]

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
        Item._remove_depreacted_dict_keys(dictionary)
        to_pass = dictionary.copy()
        for key in dictionary:
            lowered_key = key.lower()
            if hasattr(self, "_" + lowered_key):
                try:
                    setattr(self, lowered_key, dictionary[key])
                except AttributeError as attr_error:
                    raise AttributeError("Attribute \"%s\" could not be set!" % lowered_key) from attr_error
                to_pass.pop(key)
        super().from_dict(to_pass)

    @property
    def parent(self) -> Optional[Item]:
        """
        Return object next highest up the tree.

        :returns: None when there is no parent or the corresponding Item.
        """
        if (self._parent is None or self._parent == '') and self.profile:
            return self.api.profiles().find(name=self.profile)
        elif (self._parent is None or self._parent == '') and self.image:
            return self.api.images().find(name=self.image)
        elif self._parent:
            return self.api.systems().find(name=self._parent)
        else:
            return None

    @parent.setter
    def parent(self, value: str):
        """
        TODO

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
        :raises CX
        """
        if self.name is None or self.name == "":
            raise CX("name is required")
        if self.profile is None or self.profile == "":
            if self.image is None or self.image == "":
                raise CX("Error with system %s - profile or image is required" % self.name)

    #
    # specific methods for item.System
    #

    @property
    def interfaces(self):
        """
        TODO

        :return:
        """
        return self._interfaces

    @interfaces.setter
    def interfaces(self, value: Dict[str, Any]):
        """
        This methods needs to be able to take a dictionary from ``make_clone()``

        :param value:
        """
        if not isinstance(value, dict):
            raise TypeError("interfaces must of of type dict")
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

    def delete_interface(self, name: str):
        """
        Used to remove an interface.

        :raises TypeError: If the name of the interface is not of type str
        """
        if not isinstance(name, str):
            raise TypeError("The name of the interface must be of type str")
        if not name:
            return
        if name in self.interfaces:
            self.interfaces.pop(name)

    def rename_interface(self, old_name: str, new_name: str):
        """
        Used to rename an interface.

        :raises CX
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

    @property
    def hostname(self):
        """
        TODO

        :return:
        """
        return self._hostname

    @hostname.setter
    def hostname(self, value):
        """
        TODO

        :param value:
        """
        self._hostname = value

    @property
    def status(self):
        """
        TODO

        :return:
        """
        return self._status

    @status.setter
    def status(self, status):
        """
        TODO

        :param status:
        """
        self._status = status

    @property
    def boot_loaders(self):
        """
        TODO

        :return:
        """
        if self._boot_loaders == '<<inherit>>':
            if self.profile and self.profile != "":
                profile = self.api.profiles().find(name=self.profile)
                return profile.boot_loaders
            if self.image and self.image != "":
                image = self.api.images().find(name=self.image)
                return image.boot_loaders
        return self._boot_loaders

    @boot_loaders.setter
    def boot_loaders(self, boot_loaders: str):
        """
        Setter of the boot loaders.

        :param boot_loaders: The boot loaders for the system.
        :raises CX
        """
        if boot_loaders == enums.VALUE_INHERITED:
            self._boot_loaders = enums.VALUE_INHERITED
            return

        if boot_loaders:
            boot_loaders_split = utils.input_string_or_list(boot_loaders)

            if self.profile:
                profile = self.api.profiles().find(name=self.profile)
                parent_boot_loaders = profile.boot_loaders
            elif self.image:
                image = self.api.images().find(name=self.image)
                parent_boot_loaders = image.boot_loaders
            else:
                parent_boot_loaders = []
            if not set(boot_loaders_split).issubset(parent_boot_loaders):
                raise CX("Error with system \"%s\" - not all boot_loaders are supported (given: \"%s\"; supported:"
                         "\"%s\")" % (self.name, str(boot_loaders_split), str(parent_boot_loaders)))
            self._boot_loaders = boot_loaders_split
        else:
            self._boot_loaders = []

    @property
    def server(self):
        """
        TODO

        :return:
        """
        return self._server

    @server.setter
    def server(self, server):
        """
        If a system can't reach the boot server at the value configured in settings
        because it doesn't have the same name on it's subnet this is there for an override.
        """
        if server is None or server == "":
            server = enums.VALUE_INHERITED
        self._server = server

    @property
    def next_server_v4(self):
        """
        TODO

        :return:
        """
        return self._next_server_v4

    @next_server_v4.setter
    def next_server_v4(self, server: str = ""):
        """
        Setter for the IPv4 next server. See profile.py for more details.

        :param server: The address of the IPv4 next server. Must be a string or ``enums.VALUE_INHERITED``.
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):
            raise TypeError("Server must be a string.")
        if server == enums.VALUE_INHERITED:
            self._next_server_v4 = enums.VALUE_INHERITED
        else:
            self._next_server_v4 = validate.ipv4_address(server)

    @property
    def next_server_v6(self):
        """
        TODO

        :return:
        """
        return self._next_server_v6

    @next_server_v6.setter
    def next_server_v6(self, server: str = ""):
        """
        Setter for the IPv6 next server. See profile.py for more details.

        :param server: The address of the IPv6 next server. Must be a string or ``enums.VALUE_INHERITED``.
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):
            raise TypeError("Server must be a string.")
        if server == enums.VALUE_INHERITED:
            self._next_server_v6 = enums.VALUE_INHERITED
        else:
            self._next_server_v6 = validate.ipv6_address(server)

    @property
    def filename(self):
        """
        TODO

        :return:
        """
        return self._filename

    @filename.setter
    def filename(self, filename):
        """
        TODO

        :param filename:
        :return:
        """
        if not filename:
            self._filename = enums.VALUE_INHERITED
        else:
            self._filename = filename.strip()

    @property
    def proxy(self):
        """
        TODO

        :return:
        """
        return self._proxy

    @proxy.setter
    def proxy(self, proxy):
        """
        TODO

        :param proxy:
        :return:
        """
        if proxy is None or proxy == "":
            proxy = enums.VALUE_INHERITED
        self._proxy = proxy

    @property
    def redhat_management_key(self):
        """
        TODO

        :return:
        """
        return self._redhat_management_key

    @redhat_management_key.setter
    def redhat_management_key(self, management_key):
        if management_key is None or management_key == "":
            self._redhat_management_key = enums.VALUE_INHERITED
        self._redhat_management_key = management_key

    def get_mac_address(self, interface):
        """
        Get the mac address, which may be implicit in the object name or explicit with --mac-address.
        Use the explicit location first.
        """

        intf = self.__get_interface(interface)

        if intf.mac_address != "":
            return intf.mac_address.strip()
        else:
            return None

    def get_ip_address(self, interface):
        """
        Get the IP address for the given interface.
        """
        intf = self.__get_interface(interface)
        if intf.ip_address:
            return intf.ip_address.strip()
        else:
            return ""

    def is_management_supported(self, cidr_ok: bool = True) -> bool:
        """
        Can only add system PXE records if a MAC or IP address is available, else it's a koan only record.
        """
        if self.name == "default":
            return True
        for (name, x) in list(self.interfaces.items()):
            mac = x.get("mac_address", None)
            ip = x.get("ip_address", None)
            if ip is not None and not cidr_ok and ip.find("/") != -1:
                # ip is in CIDR notation
                return False
            if mac is not None or ip is not None:
                # has ip and/or mac
                return True
        return False

    def __create_interface(self, interface):
        """
        TODO

        :param interface:
        """
        self.interfaces[interface] = NetworkInterface(self.api)

    def __get_interface(self, interface_name: str = "default") -> NetworkInterface:
        """
        TODO

        :param interface_name: The name of the interface. If ``None`` is given then ``default`` is used.
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

    @property
    def gateway(self):
        """
        TODO

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

    @property
    def name_servers(self):
        """
        TODO

        :return:
        """
        return self._name_servers

    @name_servers.setter
    def name_servers(self, data: Union[str, list]):
        """
        Set the DNS servers.

        :param data: string or list of nameservers
        :returns: True or CX
        """
        self._name_servers = validate.name_servers(data)

    @property
    def name_servers_search(self):
        """
        TODO

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

    @property
    def ipv6_autoconfiguration(self):
        """
        TODO

        :return:
        """
        return self._ipv6_autoconfiguration

    @ipv6_autoconfiguration.setter
    def ipv6_autoconfiguration(self, value: bool):
        """
        TODO

        :param value:
        """
        if not isinstance(value, bool):
            raise TypeError("ipv6_autoconfiguration needs to be of type bool")
        self._ipv6_autoconfiguration = value

    @property
    def ipv6_default_device(self):
        """
        TODO

        :return:
        """
        return self._ipv6_default_device

    @ipv6_default_device.setter
    def ipv6_default_device(self, interface_name):
        """
        TODO

        :param interface_name:
        """
        if interface_name is None:
            interface_name = ""
        self._ipv6_default_device = interface_name

    @property
    def enable_ipxe(self):
        """
        TODO

        :return:
        """
        return self._enable_ipxe

    @enable_ipxe.setter
    def enable_ipxe(self, enable_ipxe: bool):
        """
        Sets whether or not the system will use iPXE for booting.
        """
        if not isinstance(enable_ipxe, bool):
            raise TypeError("enable_ipxe needs to be of type bool")
        self._enable_ipxe = enable_ipxe

    @property
    def profile(self):
        """
        TODO

        :return:
        """
        return self._profile

    @profile.setter
    def profile(self, profile_name: str):
        """
        Set the system to use a certain named profile. The profile must have already been loaded into the profiles
        collection.

        :param profile_name: The name of the profile which the system is underneath.
        """
        if not isinstance(profile_name, str):
            raise TypeError("The name of a profile needs to be of type str.")
        old_parent = self.parent
        if profile_name in ["delete", "None", "~", ""]:
            self._profile = ""
            if isinstance(old_parent, Item):
                old_parent.children.pop(self.name, 'pass')
            return

        self.image = ""  # mutual exclusion rule

        p = self.api.profiles().find(name=profile_name)
        if p is None:
            raise ValueError("Profile with the name \"%s\" is not existing" % profile_name)
        self._profile = profile_name
        self.depth = p.depth + 1  # subprofiles have varying depths.
        if isinstance(old_parent, Item):
            old_parent.children.pop(self.name, 'pass')
        new_parent = self.parent
        if isinstance(new_parent, Item):
            new_parent.children[self.name] = self

    @property
    def image(self):
        """
        TODO

        :return:
        """
        return self._image

    @image.setter
    def image(self, image_name: str):
        """
        Set the system to use a certain named image. Works like ``set_profile()`` but cannot be used at the same time.
        It's one or the other.

        :param image_name: The name of the image which will act as a parent.
        :raises CX: In case the image name was invalid.
        """
        if not isinstance(image_name, str):
            raise TypeError("The name of an image must be of type str.")
        old_parent = self.parent
        if image_name in ["delete", "None", "~", ""]:
            self._image = ""
            if isinstance(old_parent, Item):
                old_parent.children.pop(self.name, 'pass')
            return

        self.profile = ""  # mutual exclusion rule

        img = self.api.images().find(name=image_name)

        if img is not None:
            self._image = image_name
            self.depth = img.depth + 1
            if isinstance(old_parent, Item):
                old_parent.children.pop(self.name, 'pass')
            new_parent = self.parent
            if isinstance(new_parent, Item):
                new_parent.children[self.name] = self
            return
        raise CX("invalid image name (%s)" % image_name)

    @property
    def virt_cpus(self):
        """
        TODO

        :return:
        """
        return self._virt_cpus

    @virt_cpus.setter
    def virt_cpus(self, num):
        """
        TODO

        :param num:
        """
        self._virt_cpus = validate.validate_virt_cpus(num)

    @property
    def virt_file_size(self):
        """
        TODO

        :return:
        """
        return self._virt_file_size

    @virt_file_size.setter
    def virt_file_size(self, num):
        """
        TODO

        :param num:
        """
        self._virt_file_size = validate.validate_virt_file_size(num)

    @property
    def virt_disk_driver(self):
        """
        TODO

        :return:
        """
        return self._virt_disk_driver

    @virt_disk_driver.setter
    def virt_disk_driver(self, driver):
        """
        TODO

        :param driver:
        """
        self._virt_disk_driver = validate.validate_virt_disk_driver(driver)

    @property
    def virt_auto_boot(self):
        """
        TODO

        :return:
        """
        return self._virt_auto_boot

    @virt_auto_boot.setter
    def virt_auto_boot(self, num):
        """
        TODO

        :param num:
        """
        self._virt_auto_boot = validate.validate_virt_auto_boot(num)

    @property
    def virt_pxe_boot(self):
        """
        TODO

        :return:
        """
        return self._virt_pxe_boot

    @virt_pxe_boot.setter
    def virt_pxe_boot(self, num):
        """
        TODO

        :param num:
        """
        self._virt_pxe_boot = validate.validate_virt_pxe_boot(num)

    @property
    def virt_ram(self):
        """
        TODO

        :return:
        """
        return self._virt_ram

    @virt_ram.setter
    def virt_ram(self, num):
        self._virt_ram = validate.validate_virt_ram(num)

    @property
    def virt_type(self):
        """
        TODO

        :return:
        """
        return self._virt_type

    @virt_type.setter
    def virt_type(self, vtype):
        """
        TODO

        :param vtype:
        """
        self._virt_type = validate.validate_virt_type(vtype)

    @property
    def virt_path(self):
        """
        TODO

        :return:
        """
        return self._virt_path

    @virt_path.setter
    def virt_path(self, path):
        """
        TODO

        :param path:
        """
        self._virt_path = validate.validate_virt_path(path, for_system=True)

    @property
    def netboot_enabled(self):
        """
        TODO

        :return:
        """
        return self._netboot_enabled

    @netboot_enabled.setter
    def netboot_enabled(self, netboot_enabled: bool):
        """
        If true, allows per-system PXE files to be generated on sync (or add).  If false,
        these files are not generated, thus eliminating the potential for an infinite install
        loop when systems are set to PXE boot first in the boot order.  In general, users
        who are PXE booting first in the boot order won't create system definitions, so this
        feature primarily comes into play for programmatic users of the API, who want to
        initially create a system with netboot enabled and then disable it after the system installs,
        as triggered by some action in automatic installation file's  %post section.
        For this reason, this option is not urfaced in the CLI, output, or documentation (yet).

        Use of this option does not affect the ability to use PXE menus.  If an admin has machines
        set up to PXE only after local boot fails, this option isn't even relevant.
        """
        if not isinstance(netboot_enabled, bool):
            raise TypeError("netboot_enabled needs to be a bool")
        self._netboot_enabled = netboot_enabled

    @property
    def autoinstall(self):
        """
        TODO

        :return:
        """
        return self._autoinstall

    @autoinstall.setter
    def autoinstall(self, autoinstall: str):
        """
        Set the automatic installation template filepath, this must be a local file.

        :param autoinstall: local automatic installation template file path
        """
        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(self.api._collection_mgr)
        self._autoinstall = autoinstall_mgr.validate_autoinstall_template_file_path(autoinstall)

    @property
    def power_type(self) -> str:
        """
        TODO

        :return:
        """
        return self._power_type

    @power_type.setter
    def power_type(self, power_type: str):
        """
        TODO

        :param power_type:
        """
        if not isinstance(power_type, str):
            raise TypeError("power_type must be of type str")
        if not power_type:
            self._power_type = ""
            return
        power_manager.validate_power_type(power_type)
        self._power_type = power_type

    @property
    def power_identity_file(self):
        """
        TODO

        :return:
        """
        return self._power_identity_file

    @power_identity_file.setter
    def power_identity_file(self, power_identity_file):
        """
        TODO

        :param power_identity_file:
        """
        if power_identity_file is None:
            power_identity_file = ""
        utils.safe_filter(power_identity_file)
        self._power_identity_file = power_identity_file

    @property
    def power_options(self):
        """
        TODO

        :return:
        """
        return self._power_options

    @power_options.setter
    def power_options(self, power_options):
        if power_options is None:
            power_options = ""
        utils.safe_filter(power_options)
        self._power_options = power_options

    @property
    def power_user(self):
        """
        TODO

        :return:
        """
        return self._power_user

    @power_user.setter
    def power_user(self, power_user):
        if power_user is None:
            power_user = ""
        utils.safe_filter(power_user)
        self._power_user = power_user

    @property
    def power_pass(self):
        """
        TODO

        :return:
        """
        return self._power_pass

    @power_pass.setter
    def power_pass(self, power_pass):
        """
        TODO

        :param power_pass:
        """
        if power_pass is None:
            power_pass = ""
        utils.safe_filter(power_pass)
        self._power_pass = power_pass

    @property
    def power_address(self):
        """
        TODO

        :return:
        """
        return self._power_address

    @power_address.setter
    def power_address(self, power_address):
        if power_address is None:
            power_address = ""
        utils.safe_filter(power_address)
        self._power_address = power_address

    @property
    def power_id(self):
        """
        TODO

        :return:
        """
        return self._power_id

    @power_id.setter
    def power_id(self, power_id):
        """
        TODO

        :param power_id:
        """
        if power_id is None:
            power_id = ""
        utils.safe_filter(power_id)
        self._power_id = power_id

    @property
    def repos_enabled(self) -> bool:
        """
        TODO

        :return:
        """
        return self._repos_enabled

    @repos_enabled.setter
    def repos_enabled(self, repos_enabled: bool):
        """
        TODO

        :param repos_enabled:
        """
        self._repos_enabled = repos_enabled

    @property
    def serial_device(self):
        """
        TODO

        :return:
        """
        return self._serial_device

    @serial_device.setter
    def serial_device(self, device_number: int):
        """
        TODO

        :param device_number:
        """
        self._serial_device = validate.validate_serial_device(device_number)

    @property
    def serial_baud_rate(self):
        """
        TODO

        :return:
        """
        return self._serial_baud_rate

    @serial_baud_rate.setter
    def serial_baud_rate(self, baud_rate: int):
        """
        TODO

        :param baud_rate:
        """
        self._serial_baud_rate = validate.validate_serial_baud_rate(baud_rate)

    def get_config_filename(self, interface: str, loader: Optional[str] = None):
        """
        The configuration file for each system pxe uses is either a form of the MAC address of the hex version of the
        IP. If none of that is available, just use the given name, though the name given will be unsuitable for PXE
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
