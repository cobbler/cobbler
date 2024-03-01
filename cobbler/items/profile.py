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
import uuid
from typing import Optional, Union

from cobbler import autoinstall_manager, enums, utils, validate
from cobbler.cexceptions import CX
from cobbler.decorator import InheritableProperty, LazyProperty
from cobbler.items import item
from cobbler.items.distro import Distro


class Profile(item.Item):
    """
    A Cobbler profile object.
    """

    TYPE_NAME = "profile"
    COLLECTION_TYPE = "profile"

    def __init__(self, api, *args, **kwargs):
        """

        :param api: The Cobbler API object which is used for resolving information.
        :param args:
        :param kwargs:
        """
        super().__init__(api, *args, **kwargs)
        self._has_initialized = False

        self._template_files = {}
        self._autoinstall = enums.VALUE_INHERITED
        self._boot_loaders: Union[list, str] = enums.VALUE_INHERITED
        self._dhcp_tag = ""
        self._distro = ""
        self._enable_ipxe = api.settings().enable_ipxe
        self._enable_menu = api.settings().enable_menu
        self._name_servers = api.settings().default_name_servers
        self._name_servers_search = api.settings().default_name_servers_search
        self._next_server_v4 = enums.VALUE_INHERITED
        self._next_server_v6 = enums.VALUE_INHERITED
        self._filename = ""
        self._proxy = enums.VALUE_INHERITED
        self._redhat_management_key = enums.VALUE_INHERITED
        self._repos = []
        self._server = enums.VALUE_INHERITED
        self._menu = ""
        self._virt_auto_boot = api.settings().virt_auto_boot
        self._virt_bridge = enums.VALUE_INHERITED
        self._virt_cpus: Union[int, str] = 1
        self._virt_disk_driver = enums.VirtDiskDrivers.INHERITED
        self._virt_file_size = enums.VALUE_INHERITED
        self._virt_path = ""
        self._virt_ram = enums.VALUE_INHERITED
        self._virt_type = enums.VirtType.AUTO

        # Overwrite defaults from item.py
        self._boot_files = enums.VALUE_INHERITED
        self._fetchable_files = enums.VALUE_INHERITED
        self._autoinstall_meta = enums.VALUE_INHERITED
        self._kernel_options = enums.VALUE_INHERITED
        self._kernel_options_post = enums.VALUE_INHERITED
        self._mgmt_classes = enums.VALUE_INHERITED
        self._mgmt_parameters = enums.VALUE_INHERITED

        # Use setters to validate settings
        self.virt_disk_driver = api.settings().default_virt_disk_driver
        self.virt_type = api.settings().default_virt_type

        if not self._has_initialized:
            self._has_initialized = True

    def __getattr__(self, name):
        if name == "kickstart":
            return self.autoinstall
        elif name == "ks_meta":
            return self.autoinstall_meta
        raise AttributeError(
            'Attribute "%s" did not exist on object type Profile.' % name
        )

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this file object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = self.to_dict()
        cloned = Profile(self.api)
        cloned.from_dict(_dict)
        cloned.uid = uuid.uuid4().hex
        return cloned

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
            raise CX("Error with profile %s - distro is required" % self.name)

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
        if "distro" in dictionary:
            self.distro = dictionary["distro"]
        self._remove_depreacted_dict_keys(dictionary)
        self._has_initialized = old_has_initialized
        super().from_dict(dictionary)

    #
    # specific methods for item.Profile
    #

    @LazyProperty
    def parent(self) -> Optional[item.Item]:
        r"""
        Instead of a ``--distro``, set the parent of this object to another profile and use the values from the parent
        instead of this one where the values for this profile aren't filled in, and blend them together where they
        are dictionaries. Basically this enables profile inheritance. To use this, the object MUST have been
        constructed with ``is_subobject=True`` or the default values for everything will be screwed up and this will
        likely NOT work. So, API users -- make sure you pass ``is_subobject=True`` into the constructor when using this.

        Return object next highest up the tree. If this property is not set it falls back to the value of the
        ``distro``. In case neither distro nor parent is set, it returns None (which would make the profile invalid).

        :getter: The parent object which can be either another profile, a distro or None in case the object could not be
                 resolved.
        :setter: The name of the parent object. Might throw a ``CX`` in case the object could not be found.
        """
        if not self._parent:
            parent = self.distro
            if parent is None:
                return None
            return parent
        else:
            result = self.api.profiles().find(name=self._parent)
        return result

    @parent.setter
    def parent(self, parent: str):
        r"""
        Setter for the ``parent`` property.

        :param parent: The name of the parent object.
        :raises CX: In case self parentage is found or the profile given could not be found.
        """
        if not isinstance(parent, str):  # type: ignore
            raise TypeError('Property "parent" must be of type str!')
        old_parent = self.parent
        if isinstance(old_parent, item.Item) and self.name in old_parent.children:
            old_parent.children.remove(self.name)
        if not parent:
            self._parent = ""
            return
        if parent == self.name:
            # check must be done in two places as setting parent could be called before/after setting name...
            raise CX("self parentage is weird")
        found = self.api.profiles().find(name=parent)
        if found is None:
            raise CX('profile "%s" not found, inheritance not possible' % parent)
        self._parent = parent
        self.depth = found.depth + 1
        new_parent = self.parent
        if isinstance(new_parent, item.Item) and self.name not in new_parent.children:
            new_parent.children.append(self.name)

    @LazyProperty
    def arch(self):
        """
        This represents the architecture of a profile. It is read only.

        :getter: ``None`` or the parent architecture.
        """
        # FIXME: This looks so wrong. It cries: Please open a bug for me!
        parent = self.parent
        if parent:
            return parent.arch
        return None

    @LazyProperty
    def distro(self):
        """
        The parent distro of a profile. This is not representing the Distro but the id of it.

        This is a required property, if saved to the disk, with the exception if this is a subprofile.

        :return: The distro object or None.
        """
        if not self._distro:
            return None
        return self.api.distros().find(name=self._distro)

    @distro.setter
    def distro(self, distro_name: str):
        """
        Sets the distro. This must be the name of an existing Distro object in the Distros collection.

        :param distro_name: The name of the distro.
        """
        if not isinstance(distro_name, str):
            raise TypeError("distro_name needs to be of type str")
        if not distro_name:
            self._distro = ""
            return
        distro = self.api.distros().find(name=distro_name)
        if distro is None:
            raise ValueError('distribution "%s" not found' % distro_name)
        old_parent = self.parent
        if isinstance(old_parent, item.Item) and self.name in old_parent.children:
            old_parent.children.remove(self.name)
        self._distro = distro_name
        self.depth = (
            distro.depth + 1
        )  # reset depth if previously a subprofile and now top-level
        if self.name not in distro.children:
            distro.children.append(self.name)

    @InheritableProperty
    def name_servers(self) -> list:
        """
        Represents the list of nameservers to set for the profile.

        :getter: The nameservers.
        :setter: Comma delimited ``str`` or list with the nameservers.
        """
        return self._resolve("name_servers")

    @name_servers.setter
    def name_servers(self, data: list):
        """
        Set the DNS servers.

        :param data: string or list of nameservers
        """
        self._name_servers = validate.name_servers(data)

    @InheritableProperty
    def name_servers_search(self) -> list:
        """
        Represents the list of DNS search paths.

        :getter: The list of DNS search paths.
        :setter: Comma delimited ``str`` or list with the nameservers search paths.
        """
        return self._resolve("name_servers_search")

    @name_servers_search.setter
    def name_servers_search(self, data: list):
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

    @proxy.setter
    def proxy(self, proxy: str):
        """
        Setter for the proxy setting of the repository.

        :param proxy: The new proxy which will be used for the repository.
        :raises TypeError: In case the new value is not of type ``str``.
        """
        if not isinstance(proxy, str):
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

    @enable_ipxe.setter
    def enable_ipxe(self, enable_ipxe: bool):
        r"""
        Setter for the ``enable_ipxe`` property.

        :param enable_ipxe: New boolean value for enabling iPXE.
        :raises TypeError: In case after the conversion, the new value is not of type ``bool``.
        """
        enable_ipxe = utils.input_boolean(enable_ipxe)
        if not isinstance(enable_ipxe, bool):
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

    @enable_menu.setter
    def enable_menu(self, enable_menu: bool):
        """
        Setter for the ``enable_menu`` property.

        :param enable_menu: New boolean value for enabling the menu.
        :raises TypeError: In case the boolean could not be converted successfully.
        """
        enable_menu = utils.input_boolean(enable_menu)
        if not isinstance(enable_menu, bool):
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
        if not isinstance(dhcp_tag, str):
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

    @server.setter
    def server(self, server: str):
        """
        Setter for the server property.

        :param server: The str with the new value for the server property.
        :raises TypeError: In case the new value was not of type ``str``.
        """
        if not isinstance(server, str):
            raise TypeError("Field server of object profile needs to be of type str!")
        self._server = server

    @LazyProperty
    def next_server_v4(self) -> str:
        """
        Represents the next server for IPv4.

        :getter: The IP for the next server.
        :setter: May raise a ``TypeError`` if the new value is not of type ``str``.
        """
        return self._next_server_v4

    @next_server_v4.setter
    def next_server_v4(self, server: str = ""):
        """
        Setter for the next server value.

        :param server: The address of the IPv4 next server. Must be a string or ``enums.VALUE_INHERITED``.
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):
            raise TypeError("Server must be a string.")
        if server == enums.VALUE_INHERITED:
            self._next_server_v4 = enums.VALUE_INHERITED
        else:
            self._next_server_v4 = validate.ipv4_address(server)

    @LazyProperty
    def next_server_v6(self) -> str:
        r"""
        Represents the next server for IPv6.

        :getter: The IP for the next server.
        :setter: May raise a ``TypeError`` if the new value is not of type ``str``.
        """
        return self._next_server_v6

    @next_server_v6.setter
    def next_server_v6(self, server: str = ""):
        """
        Setter for the next server value.

        :param server: The address of the IPv6 next server. Must be a string or ``enums.VALUE_INHERITED``.
        :raises TypeError: In case server is no string.
        """
        if not isinstance(server, str):
            raise TypeError("Server must be a string.")
        if server == enums.VALUE_INHERITED:
            self._next_server_v6 = enums.VALUE_INHERITED
        else:
            self._next_server_v6 = validate.ipv6_address(server)

    @InheritableProperty
    def filename(self) -> str:
        """
        The filename which is fetched by the client from TFTP.

        :getter: Either the default/inherited one, or the one specific to this profile.
        :setter: The new filename which is fetched on boot. May raise a ``TypeError`` when the wrong type was given.
        """
        return self._resolve("filename")

    @filename.setter
    def filename(self, filename: str):
        """
        The setter for the ``filename`` property.

        :param filename: The new ``filename`` for the profile.
        :raises TypeError: In case the new value was not of type ``str``.
        """
        if not isinstance(filename, str):  # type: ignore
            raise TypeError("Field filename of object profile needs to be of type str!")
        parent = self.parent
        if (
            filename == enums.VALUE_INHERITED
            and parent
            and parent.TYPE_NAME == "distro"  # type: ignore
        ):
            filename = ""
        if not filename:
            if parent and parent.TYPE_NAME == "profile":  # type: ignore
                filename = enums.VALUE_INHERITED
            else:
                filename = ""
        self._filename = filename

    @LazyProperty
    def autoinstall(self) -> str:
        """
        Represents the automatic OS installation template file path, this must be a local file.

        :getter: Either the inherited name or the one specific to this profile.
        :setter: The name of the new autoinstall template is validated. The path should come in the format of a ``str``.
        """
        if self._autoinstall == enums.VALUE_INHERITED:
            parent = self.parent
            if parent is not None and isinstance(parent, Profile):
                return self.parent.autoinstall
            elif parent is not None and isinstance(parent, Distro):
                return self.api.settings().autoinstall
            else:
                self.logger.info(
                    'Profile "%s" did not have a valid parent of type Profile but autoinstall is set to '
                    '"<<inherit>>".',
                    self.name,
                )
                return ""
        return self._autoinstall

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

    @virt_auto_boot.setter
    def virt_auto_boot(self, num: bool):
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
        return self._virt_cpus

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

    @virt_file_size.setter
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

    @virt_disk_driver.setter
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

    @virt_ram.setter
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

    @virt_type.setter
    def virt_type(self, vtype: str):
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

    @virt_bridge.setter
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
    def repos(self) -> list:
        """
        The repositories to add once the system is provisioned.

        :getter: The names of the repositories the profile has assigned.
        :setter: The new names of the repositories for the profile. Validated against existing repositories.
        """
        return self._repos

    @repos.setter
    def repos(self, repos: list):
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

    @redhat_management_key.setter
    def redhat_management_key(self, management_key: str):
        """
        Setter of the redhat management key.

        :param management_key: The value may be reset by setting it to None.
        """
        if not isinstance(management_key, str):
            raise TypeError("Field management_key of object profile is of type str!")
        if not management_key:
            self._redhat_management_key = enums.VALUE_INHERITED
        self._redhat_management_key = management_key

    @InheritableProperty
    def boot_loaders(self) -> list:
        """
        This represents all boot loaders for which Cobbler will try to generate bootloader configuration for.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The bootloaders.
        :setter: The new bootloaders. Will be validates against a list of well known ones.
        """
        return self._resolve("boot_loaders")

    @boot_loaders.setter
    def boot_loaders(self, boot_loaders: list):
        """
        Setter of the boot loaders.

        :param boot_loaders: The boot loaders for the profile.
        :raises ValueError: In case the supplied boot loaders were not a subset of the valid ones.
        """
        if boot_loaders == enums.VALUE_INHERITED:
            self._boot_loaders = enums.VALUE_INHERITED
            return

        if boot_loaders:
            boot_loaders_split = utils.input_string_or_list(boot_loaders)

            parent = self.parent
            if parent is not None:
                parent_boot_loaders = parent.boot_loaders
            else:
                self.logger.warning(
                    'Parent of profile "%s" could not be found for resolving the parent bootloaders.',
                    self.name,
                )
                parent_boot_loaders = []
            if not set(boot_loaders_split).issubset(parent_boot_loaders):
                raise CX(
                    'Error with profile "%s" - not all boot_loaders are supported (given: "%s"; supported:'
                    '"%s")'
                    % (self.name, str(boot_loaders_split), str(parent_boot_loaders))
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
        if not isinstance(menu, str):
            raise TypeError("Field menu of object profile needs to be of type str!")
        if menu and menu != "":
            menu_list = self.api.menus()
            if not menu_list.find(name=menu):
                raise CX("menu %s not found" % menu)
        self._menu = menu

    @LazyProperty
    def children(self) -> list:
        """
        This property represents all children of a distribution. It should not be set manually.

        :getter: The children of the distro.
        :setter: No validation is done because this is a Cobbler internal property.
        """
        return self._children

    @children.setter
    def children(self, value: list):
        """
        Setter for the children property.

        :param value: The new children of the distro.
        """
        self._children = value
