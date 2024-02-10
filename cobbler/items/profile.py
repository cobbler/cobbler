"""
Cobbler module that contains the code for a Cobbler profile object.

Changelog:

V3.4.0 (unreleased):
    * Changes:
        * Constructor: ``kwargs`` can now be used to seed the item during creation.
        * ``children``: The property was moved to the base class.
        * ``parent``: The property was moved to the base class.
        * ``from_dict()``: The method was moved to the base class.
    * Removed:
        * ``fetchable_files``
V3.3.4 (unreleased):
    * No changes
V3.3.3:
    * Changed:
        * ``next_server_v4``: str -> enums.VALUE_INHERITED
        * ``next_server_v6``: str -> enums.VALUE_INHERITED
        * ``virt_bridge``: str -> enums.VALUE_INHERITED
        * ``virt_file_size``: int -> enums.VALUE_INHERITED
        * ``virt_ram``: int -> enums.VALUE_INHERITED
V3.3.2:
    * No changes
V3.3.1:
    * No changes
V3.3.0:
    * This release switched from pure attributes to properties (getters/setters).
    * Added:
        * ``boot_loaders``: Union[list, str]
        * ``enable_ipxe``: bool
        * ``next_server_v4``: str
        * ``next_server_v6``: str
        * ``menu``: str
        * ``from_dict()``
    * Removed:
        * ``enable_gpxe``: Union[bool, SETTINGS:enable_gpxe]
        * ``next_server``: Union[str, inherit]
        * ``get_fields()``
        * ``get_parent()``: Please use the property ``parent`` instead
        * ``set_parent()``: Please use the property ``parent`` instead
        * ``set_distro()``: Please use the property ``distro`` instead
        * ``set_name_servers()``: Please use the property ``name_servers`` instead
        * ``set_name_servers_search()``: Please use the property ``name_servers_search`` instead
        * ``set_proxy()``: Please use the property ``proxy`` instead
        * ``set_enable_gpxe()``: Please use the property ``enable_gpxe`` instead
        * ``set_enable_menu()``: Please use the property ``enable_menu`` instead
        * ``set_dhcp_tag()``: Please use the property ``dhcp_tag`` instead
        * ``set_server()``: Please use the property ``server`` instead
        * ``set_next_server()``: Please use the property ``next_server`` instead
        * ``set_filename()``: Please use the property ``filename`` instead
        * ``set_autoinstall()``: Please use the property ``autoinstall`` instead
        * ``set_virt_auto_boot()``: Please use the property ``virt_auto_boot`` instead
        * ``set_virt_cpus()``: Please use the property ``virt_cpus`` instead
        * ``set_virt_file_size()``: Please use the property ``virt_file_size`` instead
        * ``set_virt_disk_driver()``: Please use the property ``virt_disk_driver`` instead
        * ``set_virt_ram()``: Please use the property ``virt_ram`` instead
        * ``set_virt_type()``: Please use the property ``virt_type`` instead
        * ``set_virt_bridge()``: Please use the property ``virt_bridge`` instead
        * ``set_virt_path()``: Please use the property ``virt_path`` instead
        * ``set_repos()``: Please use the property ``repos`` instead
        * ``set_redhat_management_key()``: Please use the property ``redhat_management_key`` instead
        * ``get_redhat_management_key()``: Please use the property ``redhat_management_key`` instead
        * ``get_arch()``: Please use the property ``arch`` instead
    * Changed:
        * ``autoinstall``: Union[str, SETTINGS:default_kickstart] -> enums.VALUE_INHERITED
        * ``enable_menu``: Union[bool, SETTINGS:enable_menu] -> bool
        * ``name_servers``: Union[list, SETTINGS:default_name_servers] -> list
        * ``name_servers_search``: Union[list, SETTINGS:default_name_servers_search] -> list
        * ``filename``: Union[str, inherit] -> str
        * ``proxy``: Union[str, SETTINGS:proxy_url_int] -> enums.VALUE_INHERITED
        * ``redhat_management_key``: Union[str, inherit] -> enums.VALUE_INHERITED
        * ``server``: Union[str, inherit] -> enums.VALUE_INHERITED
        * ``virt_auto_boot``: Union[bool, SETTINGS:virt_auto_boot] -> bool
        * ``virt_bridge``: Union[str, SETTINGS:default_virt_bridge] -> str
        * ``virt_cpus``: int -> Union[int, str]
        * ``virt_disk_driver``: Union[str, SETTINGS:default_virt_disk_driver] -> enums.VirtDiskDrivers
        * ``virt_file_size``: Union[int, SETTINGS:default_virt_file_size] -> int
        * ``virt_ram``: Union[int, SETTINGS:default_virt_ram] -> int
        * ``virt_type``: Union[str, SETTINGS:default_virt_type] -> enums.VirtType
        * ``boot_files``: list/dict? -> enums.VALUE_INHERITED
        * ``fetchable_files``: dict -> enums.VALUE_INHERITED
        * ``autoinstall_meta``: dict -> enums.VALUE_INHERITED
        * ``kernel_options``: dict -> enums.VALUE_INHERITED
        * ``kernel_options_post``: dict -> enums.VALUE_INHERITED
        * mgmt_classes: list -> enums.VALUE_INHERITED
        * ``mgmt_parameters``: Union[str, inherit] -> enums.VALUE_INHERITED
        (``mgmt_classes`` parameter has a duplicate)
V3.2.2:
    * No changes
V3.2.1:
    * Added:
        * ``kickstart``: Resolves as a proxy to ``autoinstall``
V3.2.0:
    * No changes
V3.1.2:
    * Added:
        * ``filename``: Union[str, inherit]
V3.1.1:
    * No changes
V3.1.0:
    * Added:
        * ``get_arch()``
V3.0.1:
    * File was moved from ``cobbler/item_profile.py`` to ``cobbler/items/profile.py``.
V3.0.0:
    * Added:
        * ``next_server``: Union[str, inherit]
    * Changed:
        * Renamed: ``kickstart`` -> ``autoinstall``
        * Renamed: ``ks_meta`` -> ``autoinstall_meta``
        * ``autoinstall``: Union[str, SETTINGS:default_kickstart] -> Union[str, SETTINGS:default_autoinstall]
        * ``set_kickstart()``: Renamed to ``set_autoinstall()``
    * Removed:
        * ``redhat_management_server``: Union[str, inherit]
        * ``template_remote_kickstarts``: Union[bool, SETTINGS:template_remote_kickstarts]
        * ``set_redhat_management_server()``
        * ``set_template_remote_kickstarts()``
V2.8.5:
    * Inital tracking of changes for the changelog.
    * Added
        * ``ctime``: int
        * ``depth``: int
        * ``mtime``: int
        * ``uid``: str

        * ``kickstart``: Union[str, SETTINGS:default_kickstart]
        * ``ks_meta``: dict
        * ``boot_files``: list/dict?
        * ``comment``: str
        * ``dhcp_tag``: str
        * ``distro``: str
        * ``enable_gpxe``: Union[bool, SETTINGS:enable_gpxe]
        * ``enable_menu``: Union[bool, SETTINGS:enable_menu]
        * ``fetchable_files``: dict
        * ``kernel_options``: dict
        * ``kernel_options_post``: dict
        * ``mgmt_classes``: list
        * ``mgmt_parameters``: Union[str, inherit]
        * ``name``: str
        * ``name_servers``: Union[list, SETTINGS:default_name_servers]
        * ``name_servers_search``: Union[list, SETTINGS:default_name_servers_search]
        * ``owners``: Union[list, SETTINGS:default_ownership]
        * ``parent``: str
        * ``proxy``: Union[str, SETTINGS:proxy_url_int]
        * ``redhat_management_key``: Union[str, inherit]
        * ``redhat_management_server``: Union[str, inherit]
        * ``template_remote_kickstarts``: Union[bool, SETTINGS:template_remote_kickstarts]
        * ``repos``: list
        * ``server``: Union[str, inherit]
        * ``template_files``: dict
        * ``virt_auto_boot``: Union[bool, SETTINGS:virt_auto_boot]
        * ``virt_bridge``: Union[str, SETTINGS:default_virt_bridge]
        * ``virt_cpus``: int
        * ``virt_disk_driver``: Union[str, SETTINGS:default_virt_disk_driver]
        * ``virt_file_size``: Union[int, SETTINGS:default_virt_file_size]
        * ``virt_path``: str
        * ``virt_ram``: Union[int, SETTINGS:default_virt_ram]
        * ``virt_type``: Union[str, SETTINGS:default_virt_type]
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import copy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from cobbler import autoinstall_manager, enums, validate
from cobbler.cexceptions import CX
from cobbler.decorator import InheritableProperty, LazyProperty
from cobbler.items.abstract import item_bootable
from cobbler.utils import input_converters

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.distro import Distro


class Profile(item_bootable.BootableItem):
    """
    A Cobbler profile object.
    """

    TYPE_NAME = "profile"
    COLLECTION_TYPE = "profile"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any) -> None:
        """
        Constructor

        :param api: The Cobbler API object which is used for resolving information.
        """
        super().__init__(api)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._template_files = {}
        self._autoinstall = enums.VALUE_INHERITED
        self._boot_loaders: Union[List[str], str] = enums.VALUE_INHERITED
        self._dhcp_tag = ""
        self._distro = ""
        self._enable_ipxe: Union[str, bool] = enums.VALUE_INHERITED
        self._enable_menu: Union[str, bool] = enums.VALUE_INHERITED
        self._name_servers = enums.VALUE_INHERITED
        self._name_servers_search = enums.VALUE_INHERITED
        self._next_server_v4 = enums.VALUE_INHERITED
        self._next_server_v6 = enums.VALUE_INHERITED
        self._filename = ""
        self._proxy = enums.VALUE_INHERITED
        self._redhat_management_key = enums.VALUE_INHERITED
        self._repos: Union[List[str], str] = []
        self._server = enums.VALUE_INHERITED
        self._menu = ""
        self._display_name = ""
        self._virt_auto_boot: Union[str, bool] = enums.VALUE_INHERITED
        self._virt_bridge = enums.VALUE_INHERITED
        self._virt_cpus: int = 1
        self._virt_disk_driver: enums.VirtDiskDrivers = enums.VirtDiskDrivers.INHERITED
        self._virt_file_size: Union[str, float] = enums.VALUE_INHERITED
        self._virt_path = ""
        self._virt_ram: Union[str, int] = enums.VALUE_INHERITED
        self._virt_type: Union[str, enums.VirtType] = enums.VirtType.INHERITED

        # Overwrite defaults from item.py
        self._boot_files: Union[Dict[Any, Any], str] = enums.VALUE_INHERITED
        self._autoinstall_meta: Union[Dict[Any, Any], str] = enums.VALUE_INHERITED
        self._kernel_options: Union[Dict[Any, Any], str] = enums.VALUE_INHERITED
        self._kernel_options_post: Union[Dict[Any, Any], str] = enums.VALUE_INHERITED

        if self._is_subobject:
            self._filename = enums.VALUE_INHERITED

        # Use setters to validate settings
        self.virt_disk_driver = api.settings().default_virt_disk_driver
        self.virt_type = api.settings().default_virt_type

        if len(kwargs) > 0:
            self.from_dict(kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    def __getattr__(self, name: str) -> Any:
        if name == "kickstart":
            return self.autoinstall
        if name == "ks_meta":
            return self.autoinstall_meta
        raise AttributeError(
            f'Attribute "{name}" did not exist on object type Profile.'
        )

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this file object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = copy.deepcopy(self.to_dict())
        _dict.pop("uid", None)
        return Profile(self.api, **_dict)

    def check_if_valid(self):
        """
        Check if the profile is valid. This checks for an existing name and a distro as a conceptual parent.

        :raises CX: In case the distro or name is not present.
        """
        # name validation
        super().check_if_valid()
        if not self.inmemory:
            return

        # distro validation
        distro = self.get_conceptual_parent()
        if distro is None:
            raise CX(f"Error with profile {self.name} - distro is required")

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
        # special case for profile, since arch is a derived property from the parent distro
        if key == "arch":
            if self.arch:
                return self.arch.value == value
            return value is None

        return super().find_match_single_key(data, key, value, no_errors)

    #
    # specific methods for item.Profile
    #

    @property
    def arch(self) -> Optional[enums.Archs]:
        """
        This represents the architecture of a profile. It is read only.

        :getter: ``None`` or the parent architecture.
        """
        # FIXME: This looks so wrong. It cries: Please open a bug for me!
        parent = self.logical_parent
        if parent is not None:
            return parent.arch
        return None

    @LazyProperty
    def distro(self) -> Optional["Distro"]:
        """
        The parent distro of a profile. This is not representing the Distro but the id of it.

        This is a required property, if saved to the disk, with the exception if this is a subprofile.

        :return: The distro object or None.
        """
        if not self._distro:
            return None
        parent_distro = self.api.distros().find(name=self._distro)
        if isinstance(parent_distro, list):
            raise ValueError("Ambigous parent distro name detected!")
        return parent_distro

    @distro.setter
    def distro(self, distro_name: str):
        """
        Sets the distro. This must be the name of an existing Distro object in the Distros collection.

        :param distro_name: The name of the distro.
        """
        if not isinstance(distro_name, str):  # type: ignore
            raise TypeError("distro_name needs to be of type str")
        if not distro_name:
            self._distro = ""
            return
        distro = self.api.distros().find(name=distro_name)
        if distro is None or isinstance(distro, list):
            raise ValueError(f'distribution "{distro_name}" not found')
        self._distro = distro_name
        self.depth = (
            distro.depth + 1
        )  # reset depth if previously a subprofile and now top-level

    @InheritableProperty
    def name_servers(self) -> List[Any]:
        """
        Represents the list of nameservers to set for the profile.

        :getter: The nameservers.
        :setter: Comma delimited ``str`` or list with the nameservers.
        """
        return self._resolve("name_servers")

    @name_servers.setter  # type: ignore[no-redef]
    def name_servers(self, data: List[Any]):
        """
        Set the DNS servers.

        :param data: string or list of nameservers
        """
        self._name_servers = validate.name_servers(data)

    @InheritableProperty
    def name_servers_search(self) -> List[Any]:
        """
        Represents the list of DNS search paths.

        :getter: The list of DNS search paths.
        :setter: Comma delimited ``str`` or list with the nameservers search paths.
        """
        return self._resolve("name_servers_search")

    @name_servers_search.setter  # type: ignore[no-redef]
    def name_servers_search(self, data: List[Any]):
        """
        Set the DNS search paths.

        :param data: string or list of search domains
        """
        self._name_servers_search = validate.name_servers_search(data)

    @InheritableProperty
    def proxy(self) -> str:
        """
        Override the default external proxy which is used for accessing the internet.

        :getter: Returns the default one or the specific one for this repository.
        :setter: May raise a ``TypeError`` in case the wrong value is given.
        """
        return self._resolve("proxy_url_int")

    @proxy.setter  # type: ignore[no-redef]
    def proxy(self, proxy: str):
        """
        Setter for the proxy setting of the repository.

        :param proxy: The new proxy which will be used for the repository.
        :raises TypeError: In case the new value is not of type ``str``.
        """
        if not isinstance(proxy, str):  # type: ignore
            raise TypeError("Field proxy of object profile needs to be of type str!")
        self._proxy = proxy

    @InheritableProperty
    def enable_ipxe(self) -> bool:
        r"""
        Sets whether or not the profile will use iPXE for booting.

        :getter: If set to inherit then this returns the parent value, otherwise it returns the real value.
        :setter: May throw a ``TypeError`` in case the new value cannot be cast to ``bool``.
        """
        return self._resolve("enable_ipxe")

    @enable_ipxe.setter  # type: ignore[no-redef]
    def enable_ipxe(self, enable_ipxe: Union[str, bool]):
        r"""
        Setter for the ``enable_ipxe`` property.

        :param enable_ipxe: New boolean value for enabling iPXE.
        :raises TypeError: In case after the conversion, the new value is not of type ``bool``.
        """
        if enable_ipxe == enums.VALUE_INHERITED:
            self._enable_ipxe = enums.VALUE_INHERITED
            return

        enable_ipxe = input_converters.input_boolean(enable_ipxe)
        if not isinstance(enable_ipxe, bool):  # type: ignore
            raise TypeError("enable_ipxe needs to be of type bool")
        self._enable_ipxe = enable_ipxe

    @InheritableProperty
    def enable_menu(self) -> bool:
        """
        Sets whether or not the profile will be listed in the default PXE boot menu. This is pretty forgiving for
        YAML's sake.

        :getter: The value resolved from the defaults or the value specific to the profile.
        :setter: May raise a ``TypeError`` in case the boolean could not be converted.
        """
        return self._resolve("enable_menu")

    @enable_menu.setter  # type: ignore[no-redef]
    def enable_menu(self, enable_menu: Union[str, bool]):
        """
        Setter for the ``enable_menu`` property.

        :param enable_menu: New boolean value for enabling the menu.
        :raises TypeError: In case the boolean could not be converted successfully.
        """
        if enable_menu == enums.VALUE_INHERITED:
            self._enable_menu = enums.VALUE_INHERITED
            return

        enable_menu = input_converters.input_boolean(enable_menu)
        if not isinstance(enable_menu, bool):  # type: ignore
            raise TypeError("enable_menu needs to be of type bool")
        self._enable_menu = enable_menu

    @LazyProperty
    def dhcp_tag(self) -> str:
        """
        Represents the VLAN tag the DHCP Server is in/answering to.

        :getter: The VLAN tag or nothing if a system with the profile should not be in a VLAN.
        :setter: The new VLAN tag.
        """
        return self._dhcp_tag

    @dhcp_tag.setter
    def dhcp_tag(self, dhcp_tag: str):
        r"""
        Setter for the ``dhcp_tag`` property.

        :param dhcp_tag: The new VLAN tag.
        :raises TypeError: Raised in case the tag was not of type ``str``.
        """
        if not isinstance(dhcp_tag, str):  # type: ignore
            raise TypeError("Field dhcp_tag of object profile needs to be of type str!")
        self._dhcp_tag = dhcp_tag

    @InheritableProperty
    def server(self) -> str:
        """
        Represents the hostname the Cobbler server is reachable by a client.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The hostname of the Cobbler server.
        :setter: May raise a ``TypeError`` in case the new value is not a ``str``.
        """
        return self._resolve("server")

    @server.setter  # type: ignore[no-redef]
    def server(self, server: str):
        """
        Setter for the server property.

        :param server: The str with the new value for the server property.
        :raises TypeError: In case the new value was not of type ``str``.
        """
        if not isinstance(server, str):  # type: ignore
            raise TypeError("Field server of object profile needs to be of type str!")
        self._server = server

    @InheritableProperty
    def next_server_v4(self) -> str:
        """
        Represents the next server for IPv4.

        :getter: The IP for the next server.
        :setter: May raise a ``TypeError`` if the new value is not of type ``str``.
        """
        return self._resolve("next_server_v4")

    @next_server_v4.setter
    def next_server_v4(self, server: str = ""):
        """
        Setter for the next server value.

        :param server: The address of the IPv4 next server. Must be a string or ``enums.VALUE_INHERITED``.
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):  # type: ignore
            raise TypeError("Server must be a string.")
        if server == enums.VALUE_INHERITED:
            self._next_server_v4 = enums.VALUE_INHERITED
        else:
            self._next_server_v4 = validate.ipv4_address(server)

    @InheritableProperty
    def next_server_v6(self) -> str:
        r"""
        Represents the next server for IPv6.

        :getter: The IP for the next server.
        :setter: May raise a ``TypeError`` if the new value is not of type ``str``.
        """
        return self._resolve("next_server_v6")

    @next_server_v6.setter
    def next_server_v6(self, server: str = ""):
        """
        Setter for the next server value.

        :param server: The address of the IPv6 next server. Must be a string or ``enums.VALUE_INHERITED``.
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):  # type: ignore
            raise TypeError("Server must be a string.")
        if server == enums.VALUE_INHERITED:
            self._next_server_v6 = enums.VALUE_INHERITED
        else:
            self._next_server_v6 = validate.ipv6_address(server)

    @InheritableProperty
    def filename(self) -> str:
        """
        The filename which is fetched by the client from TFTP.

        If the filename is set to ``<<inherit>>`` and there is no parent profile then it will be set to an empty string.

        :getter: Either the default/inherited one, or the one specific to this profile.
        :setter: The new filename which is fetched on boot. May raise a ``TypeError`` when the wrong type was given.
        """
        return self._resolve("filename")

    @filename.setter  # type: ignore[no-redef]
    def filename(self, filename: str):
        """
        The setter for the ``filename`` property.

        :param filename: The new ``filename`` for the profile.
        :raises TypeError: In case the new value was not of type ``str``.
        """
        if not isinstance(filename, str):  # type: ignore
            raise TypeError("Field filename of object profile needs to be of type str!")
        parent = self.parent
        if filename == enums.VALUE_INHERITED and parent is None:
            filename = ""
        if not filename:
            if parent:
                filename = enums.VALUE_INHERITED
            else:
                filename = ""
        self._filename = filename

    @InheritableProperty
    def autoinstall(self) -> str:
        """
        Represents the automatic OS installation template file path, this must be a local file.

        :getter: Either the inherited name or the one specific to this profile.
        :setter: The name of the new autoinstall template is validated. The path should come in the format of a ``str``.
        """
        return self._resolve("autoinstall")

    @autoinstall.setter
    def autoinstall(self, autoinstall: str):
        """
        Setter for the ``autoinstall`` property.

        :param autoinstall: local automatic installation template path
        """
        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(self.api)
        self._autoinstall = autoinstall_mgr.validate_autoinstall_template_file_path(
            autoinstall
        )

    @InheritableProperty
    def virt_auto_boot(self) -> bool:
        """
        Whether the VM should be booted when booting the host or not.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: ``True`` means autoboot is enabled, otherwise VM is not booted automatically.
        :setter: The new state for the property.
        """
        return self._resolve("virt_auto_boot")

    @virt_auto_boot.setter  # type: ignore[no-redef]
    def virt_auto_boot(self, num: Union[bool, str, int]):
        """
        Setter for booting a virtual machine automatically.

        :param num: The new value for whether to enable it or not.
        """
        if num == enums.VALUE_INHERITED:
            self._virt_auto_boot = enums.VALUE_INHERITED
            return
        self._virt_auto_boot = validate.validate_virt_auto_boot(num)

    @LazyProperty
    def virt_cpus(self) -> int:
        """
        The amount of vCPU cores used in case the image is being deployed on top of a VM host.

        :getter: The cores used.
        :setter: The new number of cores.
        """
        return self._resolve("virt_cpus")

    @virt_cpus.setter
    def virt_cpus(self, num: Union[int, str]):
        """
        Setter for the number of virtual CPU cores to assign to the virtual machine.

        :param num: The number of cpu cores.
        """
        self._virt_cpus = validate.validate_virt_cpus(num)

    @InheritableProperty
    def virt_file_size(self) -> float:
        r"""
        The size of the image and thus the usable size for the guest.

        .. warning:: There is a regression which makes the usage of multiple disks not possible right now. This will be
                     fixed in a future release.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The size of the image(s) in GB.
        :setter: The float with the new size in GB.
        """
        return self._resolve("virt_file_size")

    @virt_file_size.setter  # type: ignore[no-redef]
    def virt_file_size(self, num: Union[str, int, float]):
        """
        Setter for the size of the virtual image size.

        :param num: The new size of the image.
        """
        self._virt_file_size = validate.validate_virt_file_size(num)

    @InheritableProperty
    def virt_disk_driver(self) -> enums.VirtDiskDrivers:
        """
        The type of disk driver used for storing the image.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The enum type representation of the disk driver.
        :setter: May be a ``str`` with the name of the disk driver or from the enum type directly.
        """
        return self._resolve_enum("virt_disk_driver", enums.VirtDiskDrivers)

    @virt_disk_driver.setter  # type: ignore[no-redef]
    def virt_disk_driver(self, driver: str):
        """
        Setter for the virtual disk driver that will be used.

        :param driver: The new driver.
        """
        self._virt_disk_driver = enums.VirtDiskDrivers.to_enum(driver)

    @InheritableProperty
    def virt_ram(self) -> int:
        """
        The amount of RAM given to the guest in MB.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The amount of RAM currently assigned to the image.
        :setter: The new amount of ram. Must be an integer.
        """
        return self._resolve("virt_ram")

    @virt_ram.setter  # type: ignore[no-redef]
    def virt_ram(self, num: Union[str, int]):
        """
        Setter for the virtual RAM used for the VM.

        :param num: The number of RAM to use for the VM.
        """
        self._virt_ram = validate.validate_virt_ram(num)

    @InheritableProperty
    def virt_type(self) -> enums.VirtType:
        """
        The type of image used.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The value of the virtual machine.
        :setter: May be of the enum type or a str which is then converted to the enum type.
        """
        return self._resolve_enum("virt_type", enums.VirtType)

    @virt_type.setter  # type: ignore[no-redef]
    def virt_type(self, vtype: Union[enums.VirtType, str]):
        """
        Setter for the virtual machine type.

        :param vtype: May be on out of "qemu", "kvm", "xenpv", "xenfv", "vmware", "vmwarew", "openvz" or "auto".
        """
        self._virt_type = enums.VirtType.to_enum(vtype)

    @InheritableProperty
    def virt_bridge(self) -> str:
        """
        Represents the name of the virtual bridge to use.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Either the default name for the bridge or the specific one for this profile.
        :setter: The new name. Does not overwrite the default one.
        """
        return self._resolve("virt_bridge")

    @virt_bridge.setter  # type: ignore[no-redef]
    def virt_bridge(self, vbridge: str):
        """
        Setter for the name of the virtual bridge to use.

        :param vbridge: The name of the virtual bridge to use.
        """
        self._virt_bridge = validate.validate_virt_bridge(vbridge)

    @LazyProperty
    def virt_path(self) -> str:
        """
        The path to the place where the image will be stored.

        :getter: The path to the image.
        :setter: The new path for the image.
        """
        return self._virt_path

    @virt_path.setter
    def virt_path(self, path: str):
        """
        Setter for the ``virt_path`` property.

        :param path: The path to where the image will be stored.
        """
        self._virt_path = validate.validate_virt_path(path)

    @LazyProperty
    def repos(self) -> Union[str, List[str]]:
        """
        The repositories to add once the system is provisioned.

        :getter: The names of the repositories the profile has assigned.
        :setter: The new names of the repositories for the profile. Validated against existing repositories.
        """
        return self._repos

    @repos.setter
    def repos(self, repos: Union[str, List[str]]):
        """
        Setter of the repositories for the profile.

        :param repos: The new repositories which will be set.
        """
        self._repos = validate.validate_repos(repos, self.api, bypass_check=False)

    @InheritableProperty
    def redhat_management_key(self) -> str:
        """
        Getter of the redhat management key of the profile or it's parent.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the redhat_management_key of the profile.
        :setter: May raise a ``TypeError`` in case of a validation error.
        """
        return self._resolve("redhat_management_key")

    @redhat_management_key.setter  # type: ignore[no-redef]
    def redhat_management_key(self, management_key: str):
        """
        Setter of the redhat management key.

        :param management_key: The value may be reset by setting it to None.
        """
        if not isinstance(management_key, str):  # type: ignore
            raise TypeError("Field management_key of object profile is of type str!")
        if not management_key:
            self._redhat_management_key = enums.VALUE_INHERITED
        self._redhat_management_key = management_key

    @InheritableProperty
    def boot_loaders(self) -> List[str]:
        """
        This represents all boot loaders for which Cobbler will try to generate bootloader configuration for.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The bootloaders.
        :setter: The new bootloaders. Will be validates against a list of well known ones.
        """
        return self._resolve("boot_loaders")

    @boot_loaders.setter  # type: ignore[no-redef]
    def boot_loaders(self, boot_loaders: Union[List[str], str]):
        """
        Setter of the boot loaders.

        :param boot_loaders: The boot loaders for the profile.
        :raises ValueError: In case the supplied boot loaders were not a subset of the valid ones.
        """
        if boot_loaders == enums.VALUE_INHERITED:
            self._boot_loaders = enums.VALUE_INHERITED
            return

        if boot_loaders:
            boot_loaders_split = input_converters.input_string_or_list(boot_loaders)

            parent = self.parent
            if parent is None:
                parent = self.distro
            if parent is not None:
                parent_boot_loaders = parent.boot_loaders  # type: ignore
            else:
                self.logger.warning(
                    'Parent of profile "%s" could not be found for resolving the parent bootloaders.',
                    self.name,
                )
                parent_boot_loaders = []
            if not set(boot_loaders_split).issubset(parent_boot_loaders):  # type: ignore
                raise CX(
                    f'Error with profile "{self.name}" - not all boot_loaders are supported (given:'
                    f'"{str(boot_loaders_split)}"; supported: "{str(parent_boot_loaders)}")'  # type: ignore
                )
            self._boot_loaders = boot_loaders_split
        else:
            self._boot_loaders = []

    @LazyProperty
    def menu(self) -> str:
        r"""
        Property to represent the menu which this image should be put into.

        :getter: The name of the menu or an emtpy str.
        :setter: Should only be the name of the menu not the object. May raise ``CX`` in case the menu does not exist.
        """
        return self._menu

    @menu.setter
    def menu(self, menu: str):
        """
        Setter for the menu property.

        :param menu: The menu for the image.
        :raises CX: In case the menu to be set could not be found.
        """
        if not isinstance(menu, str):  # type: ignore
            raise TypeError("Field menu of object profile needs to be of type str!")
        if menu and menu != "":
            menu_list = self.api.menus()
            if not menu_list.find(name=menu):
                raise CX(f"menu {menu} not found")
        self._menu = menu

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
