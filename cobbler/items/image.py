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
from cobbler.items.item import Item


class Image(item.Item):
    """
    A Cobbler Image.  Tracks a virtual or physical image, as opposed to a answer
    file (autoinst) led installation.
    """

    TYPE_NAME = "image"
    COLLECTION_TYPE = "image"

    def __init__(self, api, *args, **kwargs):
        super().__init__(api, *args, **kwargs)
        self._arch = enums.Archs.X86_64
        self._autoinstall = ""
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
        self._virt_file_size = 0.0
        self._virt_path = ""
        self._virt_ram = 0
        self._virt_type = enums.VirtType.AUTO
        self._supported_boot_loaders = []

    def __getattr__(self, name):
        if name == "kickstart":
            return self.autoinstall
        return self[name]

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
        Item._remove_depreacted_dict_keys(dictionary)
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
    # specific methods for item.Image
    #

    @property
    def arch(self):
        """
        TODO

        :return:
        """
        return self._arch

    @arch.setter
    def arch(self, arch):
        """
        The field is mainly relevant to PXE provisioning.
        See comments for arch property in distro.py, this works the same.

        :param arch: The new architecture to set.
        """
        self._arch = validate.validate_arch(arch)

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
        Set the automatic installation file path, this must be a local file.

        It may not make sense for images to have automatic installation templates.
        It really doesn't. However if the image type is 'iso' koan can create a virtual
        floppy and shove an answer file on it, to script an installation.  This may
        not be a automatic installation template per se, it might be a Windows answer
        file (SIF) etc.

        :param autoinstall: local automatic installation template file path
        """
        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(self.api._collection_mgr)
        self._autoinstall = autoinstall_mgr.validate_autoinstall_template_file_path(autoinstall)

    @property
    def file(self):
        """
        TODO

        :return:
        """
        return self._file

    @file.setter
    def file(self, filename: str):
        """
        Stores the image location. This should be accessible on all nodes that need to access it.

        Format: can be one of the following:
        * username:password@hostname:/path/to/the/filename.ext
        * username@hostname:/path/to/the/filename.ext
        * hostname:/path/to/the/filename.ext
        * /path/to/the/filename.ext

        :param filename: The location where the image is stored.
        :raises SyntaxError
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

    @property
    def os_version(self):
        """
        TODO

        :return:
        """
        return self._os_version

    @os_version.setter
    def os_version(self, os_version):
        """
        Set the operating system version with this setter.

        :param os_version: This must be a valid OS-Version.
        """
        self._os_version = validate.validate_os_version(os_version, self.breed)

    @property
    def breed(self):
        """
        TODO

        :return:
        """
        return self._breed

    @breed.setter
    def breed(self, breed):
        """
        Set the operating system breed with this setter.

        :param breed: The breed of the operating system which is available in the image.
        :raises CX
        """
        self._breed = validate.validate_breed(breed)

    @property
    def image_type(self):
        """
        TODO

        :return:
        """
        return self._image_type

    @image_type.setter
    def image_type(self, image_type: Union[enums.ImageTypes, str]):
        """
        Indicates what type of image this is.
        direct     = something like "memdisk", physical only
        iso        = a bootable ISO that pxe's or can be used for virt installs, virtual only
        virt-clone = a cloned virtual disk (FIXME: not yet supported), virtual only
        memdisk    = hdd image (physical only)

        :param image_type: One of the four options from above.
        """
        if not isinstance(image_type, (enums.ImageTypes, str)):
            raise TypeError("image_type must be of type str or enum.ImageTypes")
        if isinstance(image_type, str):
            if not image_type:
                # FIXME: Add None Image type
                self._image_type = enums.ImageTypes.DIRECT
            try:
                image_type = enums.ImageTypes[image_type.upper()]
            except KeyError as e:
                raise ValueError("image_type choices include: %s" % list(map(str, enums.ImageTypes))) from e
        # str was converted now it must be an enum.ImageType
        if not isinstance(image_type, enums.ImageTypes):
            raise TypeError("image_type needs to be of type enums.ImageTypes")
        if image_type not in enums.ImageTypes:
            raise ValueError("image type must be on of the following: %s" % ", ".join(list(map(str, enums.ImageTypes))))
        self._image_type = image_type

    @property
    def virt_cpus(self):
        """
        TODO

        :return:
        """
        return self._virt_cpus

    @virt_cpus.setter
    def virt_cpus(self, num: int):
        """
        Setter for the number of virtual cpus.

        :param num: The number of virtual cpu cores.
        """
        self._virt_cpus = validate.validate_virt_cpus(num)

    @property
    def network_count(self):
        """
        TODO

        :return:
        """
        return self._network_count

    @network_count.setter
    def network_count(self, num: int):
        """
        Setter for the number of networks.

        :param num: If None or emtpy will be set to one. Otherwise will be cast to int and then set.
        :raises CX
        """
        if num is None or num == "":
            num = 1
        try:
            self._network_count = int(num)
        except:
            raise ValueError("invalid network count (%s)" % num)

    @property
    def virt_auto_boot(self) -> bool:
        """
        TODO

        :return:
        """
        return self._virt_auto_boot

    @virt_auto_boot.setter
    def virt_auto_boot(self, num: bool):
        """
        Setter for the virtual automatic boot option.

        :param num: May be "0" (disabled) or "1" (enabled)
        """
        self._virt_auto_boot = validate.validate_virt_auto_boot(num)

    @property
    def virt_file_size(self) -> float:
        """
        TODO

        :return:
        """
        return self._virt_file_size

    @virt_file_size.setter
    def virt_file_size(self, num: float):
        """
        Setter for the virtual file size of the image.

        :param num: Is a non-negative integer (0 means default). Can also be a comma seperated list -- for usage with
                    multiple disks
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
    def virt_disk_driver(self, driver: enums.VirtDiskDrivers):
        """
        Setter for the virtual disk driver.

        :param driver: The virtual disk driver which will be set.
        """
        self._virt_disk_driver = validate.validate_virt_disk_driver(driver)

    @property
    def virt_ram(self):
        """
        TODO

        :return:
        """
        return self._virt_ram

    @virt_ram.setter
    def virt_ram(self, num: int):
        """
        Setter for the amount of virtual RAM the machine will have.

        :param num: 0 tells Koan to just choose a reasonable default.
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
    def virt_type(self, vtype: enums.VirtType):
        """
        Setter for the virtual type

        :param vtype: May be one of "qemu", "kvm", "xenpv", "xenfv", "vmware", "vmwarew", "openvz" or "auto".
        """
        self._virt_type = validate.validate_virt_type(vtype)

    @property
    def virt_bridge(self):
        """
        TODO

        :return:
        """
        return self._virt_bridge

    @virt_bridge.setter
    def virt_bridge(self, vbridge):
        """
        Setter for the virtual bridge which is used.

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
    def virt_path(self, path):
        """
        Setter for the virtual path which is used.

        :param path: The path to where the virtual image is stored.
        """
        self._virt_path = validate.validate_virt_path(path)

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

        :param menu: The menu for the image.
        :raises CX

        """
        if menu and menu != "":
            menu_list = self.api.menus()
            if not menu_list.find(name=menu):
                raise CX("menu %s not found" % menu)
        self._menu = menu

    @property
    def supported_boot_loaders(self):
        """
        :return: The bootloaders which are available for being set.
        """
        try:
            # If we have already loaded the supported boot loaders from
            # the signature, use that data
            return self._supported_boot_loaders
        except:
            # otherwise, refresh from the signatures / defaults
            self._supported_boot_loaders = utils.get_supported_distro_boot_loaders(self)
            return self._supported_boot_loaders

    @property
    def boot_loaders(self):
        """
        :return: The bootloaders.
        """
        if self._boot_loaders == enums.VALUE_INHERITED:
            return self.supported_boot_loaders
        return self._boot_loaders

    @boot_loaders.setter
    def boot_loaders(self, boot_loaders: list):
        """
        Setter of the boot loaders.

        :param boot_loaders: The boot loaders for the image.
        :raises CX
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
