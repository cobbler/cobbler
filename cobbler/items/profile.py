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
from typing import Union

from cobbler import autoinstall_manager
from cobbler.items import item
from cobbler import utils, validate, enums
from cobbler.cexceptions import CX


class Profile(item.Item):
    """
    A Cobbler profile object.
    """

    TYPE_NAME = "profile"
    COLLECTION_TYPE = "profile"

    def __init__(self, api, *args, **kwargs):
        super().__init__(api, *args, **kwargs)
        self._template_files = {}
        self._autoinstall = ""
        self._boot_loaders = []
        self._dhcp_tag = ""
        self._distro = ""
        self._enable_ipxe = False
        self._enable_menu = False
        self._name_servers = []
        self._name_servers_search = []
        self._next_server_v4 = ""
        self._next_server_v6 = ""
        self._filename = ""
        self._proxy = ""
        self._redhat_management_key = ""
        self._repos = []
        self._server = ""
        self._menu = ""
        self._virt_auto_boot = False
        self._virt_bridge = ""
        self._virt_cpus = 0
        self._virt_disk_driver = enums.VirtDiskDrivers.RAW
        self._virt_file_size = 0
        self._virt_path = ""
        self._virt_ram = 0
        self._virt_type = enums.VirtType.AUTO

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

        :raises CX
        """
        # name validation
        if not self.name:
            raise CX("Name is required")

        # distro validation
        distro = self.get_conceptual_parent()
        if distro is None:
            raise CX("Error with profile %s - distro is required" % self.name)

    def from_dict(self, dictionary: dict):
        """
        Initializes the object with attributes from the dictionary.

        :param dictionary: The dictionary with values.
        """
        item.Item._remove_depreacted_dict_keys(dictionary)
        dictionary.pop("parent")
        to_pass = dictionary.copy()
        for key in dictionary:
            lowered_key = key.lower()
            if hasattr(self, "_" + lowered_key):
                try:
                    setattr(self, lowered_key, dictionary[key])
                except AttributeError as e:
                    raise AttributeError("Attribute \"%s\" could not be set!" % lowered_key) from e
                to_pass.pop(key)
        super().from_dict(to_pass)

    #
    # specific methods for item.Profile
    #

    @property
    def parent(self):
        """
        Return object next highest up the tree.

        :return:
        """
        if not self._parent:
            if self.distro is None:
                return None
            result = self.api.distros().find(name=self.distro.name)
        else:
            result = self.api.profiles().find(name=self._parent)
        return result

    @parent.setter
    def parent(self, parent: str):
        r"""
        Instead of a ``--distro``, set the parent of this object to another profile and use the values from the parent
        instead of this one where the values for this profile aren't filled in, and blend them together where they
        are dictionaries. Basically this enables profile inheritance. To use this, the object MUST have been
        constructed with ``is_subobject=True`` or the default values for everything will be screwed up and this will
        likely NOT work. So, API users -- make sure you pass ``is_subobject=True`` into the constructor when using this.

        :param parent: The name of the parent object.
        :raises CX
        """
        old_parent = self.parent
        if isinstance(old_parent, item.Item):
            old_parent.children.pop(self.name, 'pass')
        if not parent:
            self._parent = ''
            return
        if parent == self.name:
            # check must be done in two places as setting parent could be called before/after setting name...
            raise CX("self parentage is weird")
        found = self.api.profiles().find(name=parent)
        if found is None:
            raise CX("profile %s not found, inheritance not possible" % parent)
        self._parent = parent
        self.depth = found.depth + 1
        parent = self.parent
        if isinstance(parent, item.Item):
            parent.children[self.name] = self

    @property
    def arch(self):
        """
        TODO

        :return:
        """
        parent = self.parent
        if parent:
            return parent.arch
        return None

    @property
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
            raise ValueError("distribution not found")
        old_parent = self.parent
        if isinstance(old_parent, item.Item):
            old_parent.children.pop(self.name, 'pass')
        self._distro = distro_name
        self.depth = distro.depth + 1    # reset depth if previously a subprofile and now top-level
        distro.children[self.name] = self

    @property
    def name_servers(self):
        """
        TODO

        :return:
        """
        return self._name_servers

    @name_servers.setter
    def name_servers(self, data):
        """
        Set the DNS servers.

        :param data: string or list of nameservers
        :returns: True or throws exception
        :raises CX: If the nameservers are not valid.
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
    def name_servers_search(self, data):
        """
        Set the DNS search paths.

        :param data: string or list of search domains
        :returns: True or throws exception
        :raises CX: If the search domains are not valid.
        """
        self._name_servers_search = validate.name_servers_search(data)

    @property
    def proxy(self) -> str:
        """
        TODO

        :return:
        """
        return self._proxy

    @proxy.setter
    def proxy(self, proxy: str):
        """
        Setter for the proxy.

        :param proxy: The new proxy for the profile.
        """
        self._proxy = proxy

    @property
    def enable_ipxe(self) -> bool:
        """
        TODO

        :return:
        """
        return self._enable_ipxe

    @enable_ipxe.setter
    def enable_ipxe(self, enable_ipxe: bool):
        """
        Sets whether or not the profile will use iPXE for booting.

        :param enable_ipxe: New boolean value for enabling iPXE.
        """
        if not isinstance(enable_ipxe, bool):
            raise TypeError("enable_ipxe needs to be of type bool")
        self._enable_ipxe = enable_ipxe

    @property
    def enable_menu(self):
        """
        TODO

        :return:
        """
        return self._enable_menu

    @enable_menu.setter
    def enable_menu(self, enable_menu: bool):
        """
        Sets whether or not the profile will be listed in the default PXE boot menu. This is pretty forgiving for
        YAML's sake.

        :param enable_menu: New boolean value for enabling the menu.
        """
        if not isinstance(enable_menu, bool):
            raise TypeError("enable_menu needs to be of type bool")
        self._enable_menu = enable_menu

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
        Setter for the dhcp tag property.

        :param dhcp_tag:
        """
        if dhcp_tag is None:
            dhcp_tag = ""
        self._dhcp_tag = dhcp_tag

    @property
    def server(self) -> str:
        """
        TODO

        :return:
        """
        return self._server

    @server.setter
    def server(self, server: str):
        """
        Setter for the server property.

        :param server: If this is None or an emtpy string this will be reset to be inherited from the parent object.
        """
        if server in [None, ""]:
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

    @property
    def filename(self):
        """
        TODO

        :return:
        """
        return self._filename

    @filename.setter
    def filename(self, filename):
        if not filename:
            self._filename = enums.VALUE_INHERITED
        else:
            self._filename = filename.strip()

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
        Set the automatic OS installation template file path, this must be a local file.

        :param autoinstall: local automatic installation template path
        """
        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(self.api._collection_mgr)
        self._autoinstall = autoinstall_mgr.validate_autoinstall_template_file_path(autoinstall)

    @property
    def virt_auto_boot(self):
        """
        TODO

        :return:
        """
        return self._virt_auto_boot

    @virt_auto_boot.setter
    def virt_auto_boot(self, num: bool):
        """
        Setter for booting a virtual machine automatically.

        :param num: The new value for whether to enable it or not.
        """
        self._virt_auto_boot = validate.validate_virt_auto_boot(num)

    @property
    def virt_cpus(self):
        """
        TODO

        :return:
        """
        return self._virt_cpus

    @virt_cpus.setter
    def virt_cpus(self, num: Union[int, str]):
        """
        Setter for the number of virtual CPU cores to assign to the virtual machine.

        :param num: The number of cpu cores.
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
    def virt_file_size(self, num: Union[str, int, float]):
        """
        Setter for the size of the virtual image size.

        :param num: The new size of the image.
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
    def virt_disk_driver(self, driver: str):
        """
        Setter for the virtual disk driver that will be used.

        :param driver: The new driver.
        """
        self._virt_disk_driver = validate.validate_virt_disk_driver(driver)

    @property
    def virt_ram(self) -> int:
        """
        TODO

        :return:
        """
        return self._virt_ram

    @virt_ram.setter
    def virt_ram(self, num: Union[str, int, float]):
        """
        Setter for the virtual RAM used for the VM.

        :param num: The number of RAM to use for the VM.
        """
        self._virt_ram = validate.validate_virt_ram(num)

    @property
    def virt_type(self):
        """
        TODO

        :return:
        """
        return self._virt_type

    @virt_type.setter
    def virt_type(self, vtype: str):
        """
        Setter for the virtual machine type.

        :param vtype: May be on out of "qemu", "kvm", "xenpv", "xenfv", "vmware", "vmwarew", "openvz" or "auto".
        """
        self._virt_type = validate.validate_virt_type(vtype)

    @property
    def virt_bridge(self) -> str:
        """
        TODO

        :return:
        """
        if not self._virt_bridge:
            return self.api.settings().default_virt_bridge
        return self._virt_bridge

    @virt_bridge.setter
    def virt_bridge(self, vbridge: str):
        """
        Setter for the name of the virtual bridge to use.

        :param vbridge: The name of the virtual bridge to use.
        """
        self._virt_bridge = validate.validate_virt_bridge(vbridge)

    @property
    def virt_path(self):
        """
        TODO

        :return:
        """
        return self._virt_path

    @virt_path.setter
    def virt_path(self, path: str):
        """
        Setter of the path to the place where the image will be stored.

        :param path: The path to where the image will be stored.
        """
        self._virt_path = validate.validate_virt_path(path)

    @property
    def repos(self):
        """
        TODO

        :return:
        """
        return self._repos

    @repos.setter
    def repos(self, repos):
        """
        Setter of the repositories for the profile.

        :param repos: The new repositories which will be set.
        """
        self._repos = validate.validate_repos(repos, False)

    @property
    def redhat_management_key(self):
        """
        Getter of the redhat management key of the profile or it's parent.

        :return: Returns the redhat_management_key of the profile.
        """
        return self._redhat_management_key

    @redhat_management_key.setter
    def redhat_management_key(self, management_key: str):
        """
        Setter of the redhat management key.

        :param management_key: The value may be reset by setting it to None.
        """
        if not management_key:
            self._redhat_management_key = enums.VALUE_INHERITED
        self._redhat_management_key = management_key

    @property
    def boot_loaders(self):
        """
        :return: The bootloaders.
        """
        if self._boot_loaders == enums.VALUE_INHERITED:
            parent = self.parent
            if parent:
                return parent.boot_loaders
            return None
        return self._boot_loaders

    @boot_loaders.setter
    def boot_loaders(self, boot_loaders):
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
            distro = self.get_conceptual_parent()

            if distro:
                distro_boot_loaders = distro.boot_loaders
            else:
                distro_boot_loaders = utils.get_supported_system_boot_loaders()
            if not set(boot_loaders_split).issubset(distro_boot_loaders):
                raise ValueError("Error with profile %s - not all boot_loaders %s are supported %s" %
                                 (self.name, boot_loaders_split, distro_boot_loaders))
            self._boot_loaders = boot_loaders_split
        else:
            self._boot_loaders = []

    @property
    def menu(self):
        """
        TODO

        :return:
        """
        return self._menu

    @menu.setter
    def menu(self, menu):
        """
        TODO

        :param menu: The menu for the profile.
        :raises CX
        """
        if menu and menu != "":
            menu_list = self.api.menus()
            if not menu_list.find(name=menu):
                raise CX("menu %s not found" % menu)
        self._menu = menu
