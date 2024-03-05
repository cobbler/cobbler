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

from cobbler import autoinstall_manager, enums, utils, validate
from cobbler.cexceptions import CX
from cobbler.items import item
from cobbler.decorator import InheritableProperty, LazyProperty


class Image(item.Item):
    """
    A Cobbler Image. Tracks a virtual or physical image, as opposed to a answer file (autoinst) led installation.
    """

    TYPE_NAME = "image"
    COLLECTION_TYPE = "image"

    def __init__(self, api, *args, **kwargs):
        """
        Constructor

        :param api: The Cobbler API object which is used for resolving information.
        :param args: The arguments which should be passed additionally to the base Item class constructor.
        :param kwargs: The keyword arguments which should be passed additionally to the base Item class constructor.
        """
        super().__init__(api, *args, **kwargs)
        self._has_initialized = False

        self._arch = enums.Archs.X86_64
        self._autoinstall = enums.VALUE_INHERITED
        self._breed = ""
        self._file = ""
        self._image_type = enums.ImageTypes.DIRECT
        self._network_count = 0
        self._os_version = ""
        self._boot_loaders = []
        self._menu = ""
        self._virt_auto_boot = False
        self._virt_bridge = ""
        self._virt_cpus = 0
        self._virt_disk_driver = enums.VirtDiskDrivers.RAW
        self._virt_file_size = enums.VALUE_INHERITED
        self._virt_path = ""
        self._virt_ram = 0
        self._virt_type = enums.VirtType.AUTO
        self._supported_boot_loaders = []

        if not self._has_initialized:
            self._has_initialized = True

    def __getattr__(self, name):
        if name == "kickstart":
            return self.autoinstall
        raise AttributeError("Attribute \"%s\" did not exist on object type Image." % name)

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this image object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = self.to_dict()
        cloned = Image(self.api)
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
        self._remove_depreacted_dict_keys(dictionary)
        self._has_initialized = old_has_initialized
        super().from_dict(dictionary)

    #
    # specific methods for item.Image
    #

    @LazyProperty
    def arch(self) -> enums.Archs:
        """
        Represents the architecture the image has. If deployed to a physical host this should be enforced, a virtual
        image may be deployed on a host with any architecture.

        :getter: The current architecture. Default is ``X86_64``.
        :setter: Should be of the enum type or str. May raise an exception in case the architecture is not known to
                 Cobbler.
        """
        return self._arch

    @arch.setter
    def arch(self, arch: Union[str, enums.Archs]):
        """
        The field is mainly relevant to PXE provisioning.
        See comments for arch property in distro.py, this works the same.

        :param arch: The new architecture to set.
        """
        self._arch = enums.Archs.to_enum(arch)

    @LazyProperty
    def autoinstall(self) -> str:
        """
        Property for the automatic installation file path, this must be a local file.

        It may not make sense for images to have automatic installation templates. It really doesn't. However if the
        image type is 'iso' koan can create a virtual floppy and shove an answer file on it, to script an installation.
        This may not be a automatic installation template per se, it might be a Windows answer file (SIF) etc.

        This property can inherit from a parent. Which is actually the default value.

        :getter: The path relative to the template directory.
        :setter: The location of the template relative to the template base directory.
        """
        return self._autoinstall

    @autoinstall.setter
    def autoinstall(self, autoinstall: str):
        """
        Set the automatic installation file path, this must be a local file.

        :param autoinstall: local automatic installation template file path
        """
        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(self.api)
        self._autoinstall = autoinstall_mgr.validate_autoinstall_template_file_path(autoinstall)

    @LazyProperty
    def file(self) -> str:
        """
        Stores the image location. This should be accessible on all nodes that need to access it.

        Format: can be one of the following:
        * username:password@hostname:/path/to/the/filename.ext
        * username@hostname:/path/to/the/filename.ext
        * hostname:/path/to/the/filename.ext
        * /path/to/the/filename.ext

        :getter: The path to the image location or an emtpy string.
        :setter: May raise a TypeError or SyntaxError in case the validation of the location fails.
        """
        return self._file

    @file.setter
    def file(self, filename: str):
        """
        The setter for the image location.

        :param filename: The location where the image is stored.
        :raises SyntaxError: In case a protocol was found.
        """
        if not isinstance(filename, str):
            raise TypeError("file must be of type str to be parsable.")

        if not filename:
            self._file = ""
            return

        # validate file location format
        if filename.find("://") != -1:
            raise SyntaxError("Invalid image file path location, it should not contain a protocol")
        uri = filename
        auth = ""
        hostname = ""
        path = ""

        if filename.find("@") != -1:
            auth, filename = filename.split("@")
        # extract the hostname
        # 1. if we have a colon, then everything before it is a hostname
        # 2. if we don't have a colon, there is no hostname
        if filename.find(":") != -1:
            hostname, filename = filename.split(":")
        elif filename[0] != '/':
            raise SyntaxError("invalid file: %s" % filename)
        # raise an exception if we don't have a valid path
        if len(filename) > 0 and filename[0] != '/':
            raise SyntaxError("file contains an invalid path: %s" % filename)
        if filename.find("/") != -1:
            path, filename = filename.rsplit("/", 1)

        if len(filename) == 0:
            raise SyntaxError("missing filename")
        if len(auth) > 0 and len(hostname) == 0:
            raise SyntaxError("a hostname must be specified with authentication details")

        self._file = uri

    @LazyProperty
    def os_version(self) -> str:
        r"""
        The operating system version which the image contains.

        :getter: The sanitized operating system version.
        :setter: Accepts a str which will be validated against the ``distro_signatures.json``.
        """
        return self._os_version

    @os_version.setter
    def os_version(self, os_version):
        """
        Set the operating system version with this setter.

        :param os_version: This must be a valid OS-Version.
        """
        self._os_version = validate.validate_os_version(os_version, self.breed)

    @LazyProperty
    def breed(self) -> str:
        r"""
        The operating system breed.

        :getter: Returns the current breed.
        :setter: When setting this it is validated against the ``distro_signatures.json`` file.
        """
        return self._breed

    @breed.setter
    def breed(self, breed: str):
        """
        Set the operating system breed with this setter.

        :param breed: The breed of the operating system which is available in the image.
        """
        self._breed = validate.validate_breed(breed)

    @LazyProperty
    def image_type(self) -> enums.ImageTypes:
        """
        Indicates what type of image this is.
        direct     = something like "memdisk", physical only
        iso        = a bootable ISO that pxe's or can be used for virt installs, virtual only
        virt-clone = a cloned virtual disk (FIXME: not yet supported), virtual only
        memdisk    = hdd image (physical only)

        :getter: The enum type value of the image type.
        :setter: Accepts str like and enum type values and raises a TypeError or ValueError in the case of a problem.
        """
        return self._image_type

    @image_type.setter
    def image_type(self, image_type: Union[enums.ImageTypes, str]):
        """
        The setter which accepts enum type or str type values. Latter ones will be automatically converted if possible.

        :param image_type: One of the four options from above.
        :raises TypeError: In case a disallowed type was found.
        :raises ValueError: In case the conversion from str could not successfully executed.
        """
        if not isinstance(image_type, (enums.ImageTypes, str)):
            raise TypeError("image_type must be of type str or enum.ImageTypes")
        if isinstance(image_type, str):
            if not image_type:
                # FIXME: Add None Image type
                self._image_type = enums.ImageTypes.DIRECT
            try:
                image_type = enums.ImageTypes[image_type.upper()]
            except KeyError as error:
                raise ValueError("image_type choices include: %s" % list(map(str, enums.ImageTypes))) from error
        # str was converted now it must be an enum.ImageTypes
        if not isinstance(image_type, enums.ImageTypes):
            raise TypeError("image_type needs to be of type enums.ImageTypes")
        if image_type not in enums.ImageTypes:
            raise ValueError("image type must be one of the following: %s"
                             % ", ".join(list(map(str, enums.ImageTypes))))
        self._image_type = image_type

    @LazyProperty
    def virt_cpus(self) -> int:
        """
        The amount of vCPU cores used in case the image is being deployed on top of a VM host.

        :getter: The cores used.
        :setter: The new number of cores.
        """
        return self._virt_cpus

    @virt_cpus.setter
    def virt_cpus(self, num: int):
        """
        Setter for the number of virtual cpus.

        :param num: The number of virtual cpu cores.
        """
        self._virt_cpus = validate.validate_virt_cpus(num)

    @LazyProperty
    def network_count(self) -> int:
        """
        Represents the number of virtual NICs this image has.

        .. deprecated:: 3.3.0
           This is nowhere used in the project and will be removed in a future release.

        :getter: The number of networks.
        :setter: Raises a ``TypeError`` in case the value is not an int.
        """
        return self._network_count

    @network_count.setter
    def network_count(self, network_count: int):
        """
        Setter for the number of networks.

        :param network_count: If None or emtpy will be set to ``1``, otherwise the given integer value will be set.
        :raises TypeError: In case the network_count was not of type int.
        """
        if network_count is None or network_count == "":
            network_count = 1
        if not isinstance(network_count, int):
            raise TypeError("Field network_count of object image needs to be of type int.")
        self._network_count = network_count

    @LazyProperty
    def virt_auto_boot(self) -> bool:
        r"""
        Whether the VM should be booted when booting the host or not.

        :getter: ``True`` means autoboot is enabled, otherwise VM is not booted automatically.
        :setter: The new state for the property.
        """
        return self._virt_auto_boot

    @virt_auto_boot.setter
    def virt_auto_boot(self, num: bool):
        """
        Setter for the virtual automatic boot option.

        :param num: May be "0" (disabled) or "1" (enabled), will be converted to a real bool.
        """
        self._virt_auto_boot = validate.validate_virt_auto_boot(num)

    @LazyProperty
    def virt_file_size(self) -> float:
        r"""
        The size of the image and thus the usable size for the guest.

        .. warning:: There is a regression which makes the usage of multiple disks not possible right now. This will be
                     fixed in a future release.

        :getter: The size of the image(s) in GB.
        :setter: The float with the new size in GB.
        """
        return self._resolve("virt_file_size")

    @virt_file_size.setter
    def virt_file_size(self, num: float):
        """
        Setter for the virtual file size of the image.

        :param num: Is a non-negative integer (0 means default). Can also be a comma seperated list -- for usage with
                    multiple disks
        """
        self._virt_file_size = validate.validate_virt_file_size(num)

    @LazyProperty
    def virt_disk_driver(self) -> enums.VirtDiskDrivers:
        """
        The type of disk driver used for storing the image.

        :getter: The enum type representation of the disk driver.
        :setter: May be a ``str`` with the name of the disk driver or from the enum type directly.
        """
        return self._virt_disk_driver

    @virt_disk_driver.setter
    def virt_disk_driver(self, driver: enums.VirtDiskDrivers):
        """
        Setter for the virtual disk driver.

        :param driver: The virtual disk driver which will be set.
        """
        self._virt_disk_driver = enums.VirtDiskDrivers.to_enum(driver)

    @LazyProperty
    def virt_ram(self) -> int:
        """
        The amount of RAM given to the guest in MB.

        :getter: The amount of RAM currently assigned to the image.
        :setter: The new amount of ram. Must be an integer.
        """
        return self._virt_ram

    @virt_ram.setter
    def virt_ram(self, num: int):
        """
        Setter for the amount of virtual RAM the machine will have.

        :param num: 0 tells Koan to just choose a reasonable default.
        """
        self._virt_ram = validate.validate_virt_ram(num)

    @LazyProperty
    def virt_type(self) -> enums.VirtType:
        """
        The type of image used.

        :getter: The value of the virtual machine.
        :setter: May be of the enum type or a str which is then converted to the enum type.
        """
        return self._virt_type

    @virt_type.setter
    def virt_type(self, vtype: enums.VirtType):
        """
        Setter for the virtual type

        :param vtype: May be one of "qemu", "kvm", "xenpv", "xenfv", "vmware", "vmwarew", "openvz" or "auto".
        """
        self._virt_type = enums.VirtType.to_enum(vtype)

    @LazyProperty
    def virt_bridge(self) -> str:
        r"""
        The name of the virtual bridge used for networking.

        .. warning:: The new validation for the setter is not working. Thus the inheritance from the settings is broken.

        :getter: The name of the bridge.
        :setter: The new name of the bridge. If set to an empty ``str``, it will be taken from the settings.
        """
        return self._virt_bridge

    @virt_bridge.setter
    def virt_bridge(self, vbridge: str):
        """
        Setter for the virtual bridge which is used.

        :param vbridge: The name of the virtual bridge to use.
        """
        self._virt_bridge = validate.validate_virt_bridge(vbridge)

    @LazyProperty
    def virt_path(self) -> str:
        """
        Represents the location where the image for the VM is stored.

        :getter: The path.
        :setter: Is being validated for being a reasonable path. If yes is set, otherwise ignored.
        """
        return self._virt_path

    @virt_path.setter
    def virt_path(self, path: str):
        """
        Setter for the virtual path which is used.

        :param path: The path to where the virtual image is stored.
        """
        self._virt_path = validate.validate_virt_path(path)

    @LazyProperty
    def menu(self) -> str:
        """
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
        if menu and menu != "":
            menu_list = self.api.menus()
            if not menu_list.find(name=menu):
                raise CX("menu %s not found" % menu)
        self._menu = menu

    @LazyProperty
    def supported_boot_loaders(self):
        """
        Read only property which represents the subset of settable bootloaders.

        :getter: The bootloaders which are available for being set.
        """
        try:
            # If we have already loaded the supported boot loaders from the signature, use that data
            return self._supported_boot_loaders
        except:
            # otherwise, refresh from the signatures / defaults
            self._supported_boot_loaders = utils.get_supported_distro_boot_loaders(self)
            return self._supported_boot_loaders

    @InheritableProperty
    def boot_loaders(self) -> list:
        """
        Represents the boot loaders which are able to boot this image.

        :getter: The bootloaders. May be an emtpy list.
        :setter: A list with the supported boot loaders for this image.
        """
        if self._boot_loaders == enums.VALUE_INHERITED:
            return self.supported_boot_loaders
        return self._boot_loaders

    @boot_loaders.setter
    def boot_loaders(self, boot_loaders: list):
        """
        Setter of the boot loaders.

        :param boot_loaders: The boot loaders for the image.
        :raises TypeError: In case this was of a not allowed type.
        :raises ValueError: In case the str which contained the list could not be successfully split.
        """
        # allow the magic inherit string to persist
        if boot_loaders == enums.VALUE_INHERITED:
            self._boot_loaders = enums.VALUE_INHERITED
            return

        if boot_loaders:
            boot_loaders_split = utils.input_string_or_list(boot_loaders)

            if not isinstance(boot_loaders_split, list):
                raise TypeError("boot_loaders needs to be of type list!")

            if not set(boot_loaders_split).issubset(self.supported_boot_loaders):
                raise ValueError("Error with image %s - not all boot_loaders %s are supported %s" %
                                 (self.name, boot_loaders_split, self.supported_boot_loaders))
            self._boot_loaders = boot_loaders_split
        else:
            self._boot_loaders = []

    @LazyProperty
    def children(self) -> list:
        """
        This property represents all children of an image. It should not be set manually.

        :getter: The children of the image.
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
