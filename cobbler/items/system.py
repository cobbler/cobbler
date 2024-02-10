"""
All code belonging to Cobbler systems.

Changelog:

V3.4.0 (unreleased):
    * Added:
        * ``display_name``: str
    * Changes:
        * Constructor: ``kwargs`` can now be used to seed the item during creation.
        * ``from_dict()``: The method was moved to the base class.
        * ``parent``: The property was moved to the base class.
    * Removed:
        * ``fetchable_files``
V3.3.4 (unreleased):
    * Changed:
        * The network interface ``default`` is not created on object creation.
V3.3.3:
    * Changed:
        * ``boot_loaders``: Can now be set to ``<<inherit>>``
        * ``next_server_v4``: Can now be set to ``<<inhertit>>``
        * ``next_server_v6``: Can now be set to ``<<inhertit>>``
        * ``virt_cpus``: Can now be set to ``<<inhertit>>``
        * ``virt_file_size``: Can now be set to ``<<inhertit>>``
        * ``virt_disk_driver``: Can now be set to ``<<inhertit>>``
        * ``virt_auto_boot``: Can now be set to ``<<inhertit>>``
        * ``virt_ram``: Can now be set to ``<<inhertit>>``
        * ``virt_type``: Can now be set to ``<<inhertit>>``
        * ``virt_path``: Can now be set to ``<<inhertit>>``
V3.3.2:
    * No changes
V3.3.1:
    * Changed:
        * ``serial_device``: Default value is now ``-1``
V3.3.0:
    * This release switched from pure attributes to properties (getters/setters).
    * Added:
        * ``next_server_v4``
        * ``next_server_v6``
    * Changed:
        * ``virt_*``: Cannot be set to inherit anymore
        * ``enable_gpxe``: Renamed to ``enable_ipxe``
    * Removed:
        * ``get_fields()``
        * ``next_server`` - Please use one of ``next_server_v4`` or ``next_server_v6``
        * ``set_boot_loader()`` - Moved to ``boot_loader`` property
        * ``set_server()`` - Moved to ``server`` property
        * ``set_next_server()`` - Moved to ``next_server`` property
        * ``set_filename()`` - Moved to ``filename`` property
        * ``set_proxy()`` - Moved to ``proxy`` property
        * ``set_redhat_management_key()`` - Moved to ``redhat_management_key`` property
        * ``get_redhat_management_key()`` - Moved to ``redhat_management_key`` property
        * ``set_dhcp_tag()`` - Moved to ``NetworkInterface`` class property ``dhcp_tag``
        * ``set_cnames()`` - Moved to ``NetworkInterface`` class property ``cnames``
        * ``set_status()`` - Moved to ``status`` property
        * ``set_static()`` - Moved to ``NetworkInterface`` class property ``static``
        * ``set_management()`` - Moved to ``NetworkInterface`` class property ``management``
        * ``set_dns_name()`` - Moved to ``NetworkInterface`` class property ``dns_name``
        * ``set_hostname()`` - Moved to ``hostname`` property
        * ``set_ip_address()`` - Moved to ``NetworkInterface`` class property ``ip_address``
        * ``set_mac_address()`` - Moved to ``NetworkInterface`` class property ``mac_address``
        * ``set_gateway()`` - Moved to ``gateway`` property
        * ``set_name_servers()`` - Moved to ``name_servers`` property
        * ``set_name_servers_search()`` - Moved to ``name_servers_search`` property
        * ``set_netmask()`` - Moved to ``NetworkInterface`` class property ``netmask``
        * ``set_if_gateway()`` - Moved to ``NetworkInterface`` class property ``if_gateway``
        * ``set_virt_bridge()`` - Moved to ``NetworkInterface`` class property ``virt_bridge``
        * ``set_interface_type()`` - Moved to ``NetworkInterface`` class property ``interface_type``
        * ``set_interface_master()`` - Moved to ``NetworkInterface`` class property ``interface_master``
        * ``set_bonding_opts()`` - Moved to ``NetworkInterface`` class property ``bonding_opts``
        * ``set_bridge_opts()`` - Moved to ``NetworkInterface`` class property ``bridge_opts``
        * ``set_ipv6_autoconfiguration()`` - Moved to ``ipv6_autoconfiguration`` property
        * ``set_ipv6_default_device()`` - Moved to ``ipv6_default_device`` property
        * ``set_ipv6_address()`` - Moved to ``NetworkInterface`` class property ``ipv6_address``
        * ``set_ipv6_prefix()`` - Moved to ``NetworkInterface`` class property ``ipv6_prefix``
        * ``set_ipv6_secondaries()`` - Moved to ``NetworkInterface`` class property ``ipv6_secondaries``
        * ``set_ipv6_default_gateway()`` - Moved to ``NetworkInterface`` class property ``ipv6_default_gateway``
        * ``set_ipv6_static_routes()`` - Moved to ``NetworkInterface`` class property ``ipv6_static_routes``
        * ``set_ipv6_mtu()`` - Moved to ``NetworkInterface`` class property ``ipv6_mtu``
        * ``set_mtu()`` - Moved to ``NetworkInterface`` class property ``mtu``
        * ``set_connected_mode()`` - Moved to ``NetworkInterface`` class property ``connected_mode``
        * ``set_enable_gpxe()`` - Moved to ``enable_gpxe`` property
        * ``set_profile()`` - Moved to ``profile`` property
        * ``set_image()`` - Moved to ``image`` property
        * ``set_virt_cpus()`` - Moved to ``virt_cpus`` property
        * ``set_virt_file_size()`` - Moved to ``virt_file_size`` property
        * ``set_virt_disk_driver()`` - Moved to ``virt_disk_driver`` property
        * ``set_virt_auto_boot()`` - Moved to ``virt_auto_boot`` property
        * ``set_virt_pxe_boot()`` - Moved to ``virt_pxe_boot`` property
        * ``set_virt_ram()`` - Moved to ``virt_ram`` property
        * ``set_virt_type()`` - Moved to ``virt_type`` property
        * ``set_virt_path()`` - Moved to ``virt_path`` property
        * ``set_netboot_enabled()`` - Moved to ``netboot_enabled`` property
        * ``set_autoinstall()`` - Moved to ``autoinstall`` property
        * ``set_power_type()`` - Moved to ``power_type`` property
        * ``set_power_identity_file()`` - Moved to ``power_identity_file`` property
        * ``set_power_options()`` - Moved to ``power_options`` property
        * ``set_power_user()`` - Moved to ``power_user`` property
        * ``set_power_pass()`` - Moved to ``power_pass`` property
        * ``set_power_address()`` - Moved to ``power_address`` property
        * ``set_power_id()`` - Moved to ``power_id`` property
        * ``set_repos_enabled()`` - Moved to ``repos_enabled`` property
        * ``set_serial_device()`` - Moved to ``serial_device`` property
        * ``set_serial_baud_rate()`` - Moved to ``serial_baud_rate`` property
V3.2.2:
    * No changes
V3.2.1:
    * Added:
        * ``kickstart``: Resolves as a proxy to ``autoinstall``
V3.2.0:
    * No changes
V3.1.2:
    * Added:
        * ``filename``: str - Inheritable
        * ``set_filename()``
V3.1.1:
    * No changes
V3.1.0:
    * No changes
V3.0.1:
    * File was moved from ``cobbler/item_system.py`` to ``cobbler/items/system.py``.
V3.0.0:
    * Field definitions for network interfaces moved to own ``FIELDS`` array
    * Added:
        * ``boot_loader``: str - Inheritable
        * ``next_server``: str - Inheritable
        * ``power_options``: str
        * ``power_identity_file``: str
        * ``serial_device``: int
        * ``serial_baud_rate``: int - One of "", "2400", "4800", "9600", "19200", "38400", "57600", "115200"
        * ``set_next_server()``
        * ``set_serial_device()``
        * ``set_serial_baud_rate()``
        * ``get_config_filename()``
        * ``set_power_identity_file()``
        * ``set_power_options()``
    * Changed:
        * ``kickstart``: Renamed to ``autoinstall``
        * ``ks_meta``: Renamed to ``autoinstall_meta``
        * ``from_datastruct``: Renamed to ``from_dict()``
        * ``set_kickstart()``: Renamed to ``set_autoinstall()``
    * Removed:
        * ``redhat_management_server``
        * ``set_ldap_enabled()``
        * ``set_monit_enabled()``
        * ``set_template_remote_kickstarts()``
        * ``set_redhat_management_server()``
        * ``set_name()``
V2.8.5:
    * Inital tracking of changes for the changelog.
    * Network interface defintions part of this class
    * Added:
        * ``name``: str
        * ``uid``: str
        * ``owners``: List[str] - Inheritable
        * ``profile``: str - Name of the profile
        * ``image``: str - Name of the image
        * ``status``: str - One of "", "development", "testing", "acceptance", "production"
        * ``kernel_options``: Dict[str, Any]
        * ``kernel_options_post``: Dict[str, Any]
        * ``ks_meta``: Dict[str, Any]
        * ``enable_gpxe``: bool - Inheritable
        * ``proxy``: str - Inheritable
        * ``netboot_enabled``: bool
        * ``kickstart``: str - Inheritable
        * ``comment``: str
        * ``depth``: int
        * ``server``: str - Inheritable
        * ``virt_path``: str - Inheritable
        * ``virt_type``: str - Inheritable; One of "xenpv", "xenfv", "qemu", "kvm", "vmware", "openvz"
        * ``virt_cpus``: int - Inheritable
        * ``virt_file_size``: float - Inheritable
        * ``virt_disk_driver``: str - Inheritable; One of "<<inherit>>", "raw", "qcow", "qcow2", "aio", "vmdk", "qed"
        * ``virt_ram``: int - Inheritable
        * ``virt_auto_boot``: bool - Inheritable
        * ``virt_pxe_boot``: bool
        * ``ctime``: float
        * ``mtime``: float
        * ``power_type``: str - Default loaded from settings key ``power_management_default_type``
        * ``power_address``: str
        * ``power_user``: str
        * ``power_pass``: str
        * ``power_id``: str
        * ``hostname``: str
        * ``gateway``: str
        * ``name_servers``: List[str]
        * ``name_servers_search``: List[str]
        * ``ipv6_default_device``: str
        * ``ipv6_autoconfiguration``: bool
        * ``mgmt_classes``: List[Any] - Inheritable
        * ``mgmt_parameters``: str - Inheritable
        * ``boot_files``: Dict[str, Any]/List (Not reverse engineeriable) - Inheritable
        * ``fetchable_files``: Dict[str, Any] - Inheritable
        * ``template_files``: Dict[str, Any] - Inheritable
        * ``redhat_management_key``: str - Inheritable
        * ``redhat_management_server``: str - Inheritable
        * ``template_remote_kickstarts``: bool - Default loaded from settings key ``template_remote_kickstarts``
        * ``repos_enabled``: bool
        * ``ldap_enabled``: - bool
        * ``ldap_type``: str - Default loaded from settings key ``ldap_management_default_type``
        * ``monit_enabled``: bool

"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2008, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import copy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from cobbler import autoinstall_manager, enums, power_manager, utils, validate
from cobbler.cexceptions import CX
from cobbler.decorator import InheritableProperty, LazyProperty
from cobbler.items.abstract import item_bootable
from cobbler.items.network_interface import NetworkInterface
from cobbler.utils import filesystem_helpers, input_converters

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class System(item_bootable.BootableItem):
    """
    A Cobbler system object.
    """

    # Constants
    TYPE_NAME = "system"
    COLLECTION_TYPE = "system"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any) -> None:
        """
        Constructor

        :param api: The Cobbler API
        """
        super().__init__(api)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._interfaces: Dict[str, NetworkInterface] = {}
        self._ipv6_autoconfiguration = False
        self._repos_enabled = False
        self._autoinstall = enums.VALUE_INHERITED
        self._boot_loaders: Union[List[str], str] = enums.VALUE_INHERITED
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
        self._display_name = ""

        # Overwrite defaults from item.py
        self._owners = enums.VALUE_INHERITED
        self._boot_files = enums.VALUE_INHERITED
        self._autoinstall_meta = enums.VALUE_INHERITED
        self._kernel_options = enums.VALUE_INHERITED
        self._kernel_options_post = enums.VALUE_INHERITED

        if len(kwargs) > 0:
            self.from_dict(kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    def __getattr__(self, name: str) -> Any:
        if name == "kickstart":
            return self.autoinstall
        if name == "ks_meta":
            return self.autoinstall_meta
        raise AttributeError(f'Attribute "{name}" did not exist on object type System.')

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        _dict = copy.deepcopy(self.to_dict())
        _dict.pop("uid", None)
        return System(self.api, **_dict)

    def check_if_valid(self):
        """
        Checks if the current item passes logical validation.

        :raises CX: In case name is missing. Additionally either image or profile is required.
        """
        super().check_if_valid()
        if not self.inmemory:
            return

        # System specific validation
        if self.profile == "":
            if self.image == "":
                raise CX(
                    f"Error with system {self.name} - profile or image is required"
                )

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
        if not isinstance(value, dict):  # type: ignore
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
        raise ValueError(
            "The values of the interfaces must be fully of type dict (one level with values) or "
            "NetworkInterface objects"
        )

    def modify_interface(self, interface_values: Dict[str, Any]):
        """
        Modifies a magic interface dictionary in the form of: {"macaddress-eth0" : "aa:bb:cc:dd:ee:ff"}
        """
        for key in interface_values.keys():
            (_, interface) = key.split("-", 1)
            if interface not in self.interfaces:
                self.__create_interface(interface)
            self.interfaces[interface].modify_interface({key: interface_values[key]})

    def delete_interface(self, name: Union[str, Dict[Any, Any]]) -> None:
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
        if not isinstance(old_name, str):  # type: ignore
            raise TypeError("The old_name of the interface must be of type str")
        if not isinstance(new_name, str):  # type: ignore
            raise TypeError("The new_name of the interface must be of type str")
        if old_name not in self.interfaces:
            raise ValueError(f'Interface "{old_name}" does not exist')
        if new_name in self.interfaces:
            raise ValueError(f'Interface "{new_name}" already exists')
        self.interfaces[new_name] = self.interfaces[old_name]
        del self.interfaces[old_name]

    @LazyProperty
    def hostname(self) -> str:
        """
        hostname property.

        :getter: Returns the value for ``hostname``.
        :setter: Sets the value for the property ``hostname``.
        """
        return self._hostname

    @hostname.setter
    def hostname(self, value: str):
        """
        Setter for the hostname of the System class.

        :param value: The new hostname
        """
        if not isinstance(value, str):  # type: ignore
            raise TypeError("Field hostname of object system needs to be of type str!")
        self._hostname = value

    @LazyProperty
    def status(self) -> str:
        """
        status property.

        :getter: Returns the value for ``status``.
        :setter: Sets the value for the property ``status``.
        """
        return self._status

    @status.setter
    def status(self, status: str):
        """
        Setter for the status of the System class.

        :param status: The new system status.
        """
        if not isinstance(status, str):  # type: ignore
            raise TypeError("Field status of object system needs to be of type str!")
        self._status = status

    @InheritableProperty
    def boot_loaders(self) -> List[str]:
        """
        boot_loaders property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``boot_loaders``.
        :setter: Sets the value for the property ``boot_loaders``.
        """
        return self._resolve("boot_loaders")

    @boot_loaders.setter  # type: ignore[no-redef]
    def boot_loaders(self, boot_loaders: Union[str, List[str]]):
        """
        Setter of the boot loaders.

        :param boot_loaders: The boot loaders for the system.
        :raises CX: This is risen in case the bootloaders set are not valid ones.
        """
        if not isinstance(boot_loaders, (str, list)):  # type: ignore
            raise TypeError("The bootloaders need to be either a str or list")

        if boot_loaders == enums.VALUE_INHERITED:
            self._boot_loaders = enums.VALUE_INHERITED
            return

        if boot_loaders in ("", []):
            self._boot_loaders = []
            return

        if isinstance(boot_loaders, str):
            boot_loaders_split = input_converters.input_string_or_list(boot_loaders)
        else:
            boot_loaders_split = boot_loaders

        parent = self.logical_parent
        if parent is not None:
            # This can only be an item type that has the boot loaders property
            parent_boot_loaders: List[str] = parent.boot_loaders  # type: ignore
        else:
            self.logger.warning(
                'Parent of System "%s" could not be found for resolving the parent bootloaders.',
                self.name,
            )
            parent_boot_loaders = []
        if not set(boot_loaders_split).issubset(parent_boot_loaders):
            raise CX(
                f'Error with system "{self.name}" - not all boot_loaders are supported (given:'
                f'"{str(boot_loaders_split)}"; supported: "{str(parent_boot_loaders)}")'
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

    @server.setter  # type: ignore[no-redef]
    def server(self, server: str):
        """
        If a system can't reach the boot server at the value configured in settings
        because it doesn't have the same name on it's subnet this is there for an override.

        :param server: The new value for the ``server`` property.
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):  # type: ignore
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

    @next_server_v4.setter  # type: ignore[no-redef]
    def next_server_v4(self, server: str = ""):
        """
        Setter for the IPv4 next server. See profile.py for more details.

        :param server: The address of the IPv4 next server. Must be a string or ``enums.VALUE_INHERITED``.
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):  # type: ignore
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

    @next_server_v6.setter  # type: ignore[no-redef]
    def next_server_v6(self, server: str = ""):
        """
        Setter for the IPv6 next server. See profile.py for more details.

        :param server: The address of the IPv6 next server. Must be a string or ``enums.VALUE_INHERITED``.
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):  # type: ignore
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
        if self.image != "":
            return ""
        return self._resolve("filename")

    @filename.setter  # type: ignore[no-redef]
    def filename(self, filename: str):
        """
        Setter for the filename of the System class.

        :param filename: The new value for the ``filename`` property.
        :raises TypeError: In case filename is no string.
        """
        if not isinstance(filename, str):  # type: ignore
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
        if self.profile != "":
            return self._resolve("proxy")
        return self._resolve("proxy_url_int")

    @proxy.setter  # type: ignore[no-redef]
    def proxy(self, proxy: str):
        """
        Setter for the proxy of the System class.

        :param proxy: The new value for the proxy.
        :raises TypeError: In case proxy is no string.
        """
        if not isinstance(proxy, str):  # type: ignore
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

    @redhat_management_key.setter  # type: ignore[no-redef]
    def redhat_management_key(self, management_key: str):
        """
        Setter for the redhat_management_key of the System class.

        :param management_key: The new value for the redhat management key
        :raises TypeError: In case management_key is no string.
        """
        if not isinstance(management_key, str):  # type: ignore
            raise TypeError(
                "Field redhat_management_key of object system needs to be of type str!"
            )
        if management_key == "":
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
        return None

    def get_ip_address(self, interface: str) -> str:
        """
        Get the IP address for the given interface.

        :param interface: The name of the interface to get the IP address of.
        """
        intf = self.__get_interface(interface)
        if intf.ip_address:
            return intf.ip_address.strip()
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

    def __get_interface(
        self, interface_name: Optional[str] = "default"
    ) -> NetworkInterface:
        """
        Tries to retrieve an interface and creates it in case the interface doesn't exist. If no name is given the
        default interface is retrieved.

        :param interface_name: The name of the interface. If ``None`` is given then ``default`` is used.
        :raises TypeError: In case interface_name is no string.
        :return: The requested interface.
        """
        if interface_name is None:
            interface_name = "default"
        if not isinstance(interface_name, str):  # type: ignore
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
    def name_servers(self) -> List[str]:
        """
        name_servers property.
        FIXME: Differentiate between IPv4/6

        :getter: Returns the value for ``name_servers``.
        :setter: Sets the value for the property ``name_servers``.
        """
        return self._resolve("name_servers")

    @name_servers.setter
    def name_servers(self, data: Union[str, List[str]]):
        """
        Set the DNS servers.
        FIXME: Differentiate between IPv4/6

        :param data: string or list of nameservers
        :returns: True or CX
        """
        self._name_servers = validate.name_servers(data)

    @LazyProperty
    def name_servers_search(self) -> List[str]:
        """
        name_servers_search property.

        :getter: Returns the value for ``name_servers_search``.
        :setter: Sets the value for the property ``name_servers_search``.
        """
        return self._resolve("name_servers_search")

    @name_servers_search.setter
    def name_servers_search(self, data: Union[str, List[Any]]):
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
        """
        return self._ipv6_autoconfiguration

    @ipv6_autoconfiguration.setter
    def ipv6_autoconfiguration(self, value: bool):
        """
        Setter for the ipv6_autoconfiguration of the System class.

        :param value: The new value for the ``ipv6_autoconfiguration`` property.
        """
        value = input_converters.input_boolean(value)
        if not isinstance(value, bool):  # type: ignore
            raise TypeError("ipv6_autoconfiguration needs to be of type bool")
        self._ipv6_autoconfiguration = value

    @LazyProperty
    def ipv6_default_device(self) -> str:
        """
        ipv6_default_device property.

        :getter: Returns the value for ``ipv6_default_device``.
        :setter: Sets the value for the property ``ipv6_default_device``.
        """
        return self._ipv6_default_device

    @ipv6_default_device.setter
    def ipv6_default_device(self, interface_name: str):
        """
        Setter for the ipv6_default_device of the System class.

        :param interface_name: The new value for the ``ipv6_default_device`` property.
        """
        if not isinstance(interface_name, str):  # type: ignore
            raise TypeError(
                "Field ipv6_default_device of object system needs to be of type str!"
            )
        self._ipv6_default_device = interface_name

    @InheritableProperty
    def enable_ipxe(self) -> bool:
        """
        enable_ipxe property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``enable_ipxe``.
        :setter: Sets the value for the property ``enable_ipxe``.
        """
        return self._resolve("enable_ipxe")

    @enable_ipxe.setter  # type: ignore[no-redef]
    def enable_ipxe(self, enable_ipxe: Union[str, bool]):
        """
        Sets whether the system will use iPXE for booting.

        :param enable_ipxe: If ipxe should be enabled or not.
        :raises TypeError: In case enable_ipxe is not a boolean.
        """
        if enable_ipxe == enums.VALUE_INHERITED:
            self._enable_ipxe = enums.VALUE_INHERITED
            return

        enable_ipxe = input_converters.input_boolean(enable_ipxe)
        if not isinstance(enable_ipxe, bool):  # type: ignore
            raise TypeError("enable_ipxe needs to be of type bool")
        self._enable_ipxe = enable_ipxe

    @LazyProperty
    def profile(self) -> str:
        """
        profile property.

        :getter: Returns the value for ``profile``.
        :setter: Sets the value for the property ``profile``.
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
        if not isinstance(profile_name, str):  # type: ignore
            raise TypeError("The name of a profile needs to be of type str.")

        if profile_name in ["delete", "None", "~", ""]:
            self._profile = ""
            return

        profile = self.api.profiles().find(name=profile_name, return_list=False)
        if isinstance(profile, list):
            raise ValueError("Search returned ambigous match!")
        if profile is None:
            raise ValueError(f'Profile with the name "{profile_name}" is not existing')

        self.image = ""  # mutual exclusion rule
        self._profile = profile_name
        self.depth = profile.depth + 1  # subprofiles have varying depths.

    @LazyProperty
    def image(self) -> str:
        """
        image property.

        :getter: Returns the value for ``image``.
        :setter: Sets the value for the property ``image``.
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
        if not isinstance(image_name, str):  # type: ignore
            raise TypeError("The name of an image must be of type str.")

        if image_name in ["delete", "None", "~", ""]:
            self._image = ""
            return

        img = self.api.images().find(name=image_name)
        if isinstance(img, list):
            raise ValueError("Search returned ambigous match!")
        if img is None:
            raise ValueError(f'Image with the name "{image_name}" is not existing')

        self.profile = ""  # mutual exclusion rule
        self._image = image_name
        self.depth = img.depth + 1

    @InheritableProperty
    def virt_cpus(self) -> int:
        """
        virt_cpus property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``virt_cpus``.
        :setter: Sets the value for the property ``virt_cpus``.
        """
        return self._resolve("virt_cpus")

    @virt_cpus.setter  # type: ignore[no-redef]
    def virt_cpus(self, num: Union[int, str]):
        """
        Setter for the virt_cpus of the System class.

        :param num: The new value for the number of CPU cores.
        """
        if num == enums.VALUE_INHERITED:
            self._virt_cpus = enums.VALUE_INHERITED
            return

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

    @virt_file_size.setter  # type: ignore[no-redef]
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

    @virt_disk_driver.setter  # type: ignore[no-redef]
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

    @virt_auto_boot.setter  # type: ignore[no-redef]
    def virt_auto_boot(self, value: Union[bool, str]):
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

    @virt_ram.setter  # type: ignore[no-redef]
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

    @virt_type.setter  # type: ignore[no-redef]
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

    @virt_path.setter  # type: ignore[no-redef]
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
        netboot_enabled = input_converters.input_boolean(netboot_enabled)
        if not isinstance(netboot_enabled, bool):  # type: ignore
            raise TypeError("netboot_enabled needs to be a bool")
        self._netboot_enabled = netboot_enabled

    @InheritableProperty
    def autoinstall(self) -> str:
        """
        autoinstall property.

        :getter: Returns the value for ``autoinstall``.
        :setter: Sets the value for the property ``autoinstall``.
        """
        return self._resolve("autoinstall")

    @autoinstall.setter  # type: ignore[no-redef]
    def autoinstall(self, autoinstall: str):
        """
        Set the automatic installation template filepath, this must be a local file.

        :param autoinstall: local automatic installation template file path
        """
        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(self.api)
        self._autoinstall = autoinstall_mgr.validate_autoinstall_template_file_path(
            autoinstall
        )

    @LazyProperty
    def power_type(self) -> str:
        """
        power_type property.

        :getter: Returns the value for ``power_type``.
        :setter: Sets the value for the property ``power_type``.
        """
        return self._power_type

    @power_type.setter
    def power_type(self, power_type: str):
        """
        Setter for the power_type of the System class.

        :param power_type: The new value for the ``power_type`` property.
        :raises TypeError: In case power_type is no string.
        """
        if not isinstance(power_type, str):  # type: ignore
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
        """
        return self._power_identity_file

    @power_identity_file.setter
    def power_identity_file(self, power_identity_file: str):
        """
        Setter for the power_identity_file of the System class.

        :param power_identity_file: The new value for the ``power_identity_file`` property.
        :raises TypeError: In case power_identity_file is no string.
        """
        if not isinstance(power_identity_file, str):  # type: ignore
            raise TypeError(
                "Field power_identity_file of object system needs to be of type str!"
            )
        filesystem_helpers.safe_filter(power_identity_file)
        self._power_identity_file = power_identity_file

    @LazyProperty
    def power_options(self) -> str:
        """
        power_options property.

        :getter: Returns the value for ``power_options``.
        :setter: Sets the value for the property ``power_options``.
        """
        return self._power_options

    @power_options.setter
    def power_options(self, power_options: str):
        """
        Setter for the power_options of the System class.

        :param power_options: The new value for the ``power_options`` property.
        :raises TypeError: In case power_options is no string.
        """
        if not isinstance(power_options, str):  # type: ignore
            raise TypeError(
                "Field power_options of object system needs to be of type str!"
            )
        filesystem_helpers.safe_filter(power_options)
        self._power_options = power_options

    @LazyProperty
    def power_user(self) -> str:
        """
        power_user property.

        :getter: Returns the value for ``power_user``.
        :setter: Sets the value for the property ``power_user``.
        """
        return self._power_user

    @power_user.setter
    def power_user(self, power_user: str):
        """
        Setter for the power_user of the System class.

        :param power_user: The new value for the ``power_user`` property.
        :raises TypeError: In case power_user is no string.
        """
        if not isinstance(power_user, str):  # type: ignore
            raise TypeError(
                "Field power_user of object system needs to be of type str!"
            )
        filesystem_helpers.safe_filter(power_user)
        self._power_user = power_user

    @LazyProperty
    def power_pass(self) -> str:
        """
        power_pass property.

        :getter: Returns the value for ``power_pass``.
        :setter: Sets the value for the property ``power_pass``.
        """
        return self._power_pass

    @power_pass.setter
    def power_pass(self, power_pass: str):
        """
        Setter for the power_pass of the System class.

        :param power_pass: The new value for the ``power_pass`` property.
        :raises TypeError: In case power_pass is no string.
        """
        if not isinstance(power_pass, str):  # type: ignore
            raise TypeError(
                "Field power_pass of object system needs to be of type str!"
            )
        filesystem_helpers.safe_filter(power_pass)
        self._power_pass = power_pass

    @LazyProperty
    def power_address(self) -> str:
        """
        power_address property.

        :getter: Returns the value for ``power_address``.
        :setter: Sets the value for the property ``power_address``.
        """
        return self._power_address

    @power_address.setter
    def power_address(self, power_address: str):
        """
        Setter for the power_address of the System class.

        :param power_address: The new value for the ``power_address`` property.
        :raises TypeError: In case power_address is no string.
        """
        if not isinstance(power_address, str):  # type: ignore
            raise TypeError(
                "Field power_address of object system needs to be of type str!"
            )
        filesystem_helpers.safe_filter(power_address)
        self._power_address = power_address

    @LazyProperty
    def power_id(self) -> str:
        """
        power_id property.

        :getter: Returns the value for ``power_id``.
        :setter: Sets the value for the property ``power_id``.
        """
        return self._power_id

    @power_id.setter
    def power_id(self, power_id: str):
        """
        Setter for the power_id of the System class.

        :param power_id: The new value for the ``power_id`` property.
        :raises TypeError: In case power_id is no string.
        """
        if not isinstance(power_id, str):  # type: ignore
            raise TypeError("Field power_id of object system needs to be of type str!")
        filesystem_helpers.safe_filter(power_id)
        self._power_id = power_id

    @LazyProperty
    def repos_enabled(self) -> bool:
        """
        repos_enabled property.

        :getter: Returns the value for ``repos_enabled``.
        :setter: Sets the value for the property ``repos_enabled``.
        """
        return self._repos_enabled

    @repos_enabled.setter
    def repos_enabled(self, repos_enabled: bool):
        """
        Setter for the repos_enabled of the System class.

        :param repos_enabled: The new value for the ``repos_enabled`` property.
        :raises TypeError: In case is no string.
        """
        repos_enabled = input_converters.input_boolean(repos_enabled)
        if not isinstance(repos_enabled, bool):  # type: ignore
            raise TypeError(
                "Field repos_enabled of object system needs to be of type bool!"
            )
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

        :param baud_rate: The new value for the ``baud_rate`` property.
        """
        self._serial_baud_rate = validate.validate_serial_baud_rate(baud_rate)

    def get_config_filename(
        self, interface: str, loader: Optional[str] = None
    ) -> Optional[str]:
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
            if (
                "grub" in boot_loaders or len(boot_loaders) < 1
            ):  # pylint: disable=unsupported-membership-test
                loader = "grub"
            else:
                loader = boot_loaders[0]  # pylint: disable=unsubscriptable-object

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
        ip_address = self.get_ip_address(interface)
        if mac is not None and mac != "":
            if loader == "grub":
                return mac.lower()
            return "01-" + "-".join(mac.split(":")).lower()
        if ip_address != "":
            return utils.get_host_ip(ip_address)
        return self.name

    @LazyProperty
    def display_name(self) -> str:
        """
        Returns the display name.

        :getter: Returns the display name for the boot menu.
        :setter: Sets the display name for the boot menu.
        """
        return self._display_name

    @display_name.setter
    def display_name(self, display_name: str):
        """
        Setter for the display_name of the item.

        :param display_name: The new display_name. If ``None`` the display_name will be set to an emtpy string.
        """
        self._display_name = display_name

    def find_match_single_key(
        self, data: Dict[str, Any], key: str, value: Any, no_errors: bool = False
    ) -> bool:
        """
        Look if the data matches or not. This is an alternative for ``find_match()``.

        :param data: The data to search through.
        :param key: The key to look for int the item.
        :param value: The value for the key.
        :param no_errors: How strict this matching is.
        :return: Whether the data matches or not.
        """
        # special case for systems
        key_found_already = False
        if "interfaces" in data:
            if key in [
                "cnames",
                "connected_mode",
                "if_gateway",
                "ipv6_default_gateway",
                "ipv6_mtu",
                "ipv6_prefix",
                "ipv6_secondaries",
                "ipv6_static_routes",
                "management",
                "mtu",
                "static",
                "mac_address",
                "ip_address",
                "ipv6_address",
                "netmask",
                "virt_bridge",
                "dhcp_tag",
                "dns_name",
                "static_routes",
                "interface_type",
                "interface_master",
                "bonding_opts",
                "bridge_opts",
                "interface",
            ]:
                key_found_already = True
                for (name, interface) in list(data["interfaces"].items()):
                    if value == name:
                        return True
                    if value is not None and key in interface:
                        if self._find_compare(interface[key], value):
                            return True

        if key not in data:
            if not key_found_already:
                if not no_errors:
                    # FIXME: removed for 2.0 code, shouldn't cause any problems to not have an exception here?
                    # raise CX("searching for field that does not exist: %s" % key)
                    return False
            else:
                if value is not None:  # FIXME: new?
                    return False

        if value is None:
            return True
        return self._find_compare(value, data[key])
