"""
Cobbler module that contains the code for a Cobbler image object.

Changelog:

V3.4.0 (unreleased):
    * Added:
        * ``display_name``
    * Changed:
        * Constructor: ``kwargs`` can now be used to seed the item during creation.
        * ``autoinstall``: Restored inheritance of the property.
        * ``children``: The proqperty was moved to the base class.
        * ``from_dict()``: The method was moved to the base class.
        * ``virt_disk_driver``: Restored inheritance of the property.
        * ``virt_ram``: Restored inheritance of the property.
        * ``virt_type``: Restored inheritance of the property.
        * ``virt_bridge``: Restored inheritance of the property.
V3.3.4 (unreleased):
    * No changes
V3.3.3:
    * Added:
        * ``children``
    * Changes:
        * ``virt_file_size``: Inherits from the settings again
        * ``boot_loaders``: Inherits from the settings again
V3.3.2:
    * No changes
V3.3.1:
    * No changes
V3.3.0:
    * This release switched from pure attributes to properties (getters/setters).
    * Added:
        * ``boot_loaders``: list
        * ``menu``: str
        * ``supported_boot_loaders``: list
        * ``from_dict()``
    * Moved to parent class (Item):
        * ``ctime``: float
        * ``mtime``: float
        * ``depth``: int
        * ``parent``: str
        * ``uid``: str
        * ``comment``: str
        * ``name``: str
    * Removed:
        * ``get_fields()``
        * ``get_parent()``
        * ``set_arch()`` - Please use the ``arch`` property.
        * ``set_autoinstall()`` - Please use the ``autoinstall`` property.
        * ``set_file()`` - Please use the ``file`` property.
        * ``set_os_version()`` - Please use the ``os_version`` property.
        * ``set_breed()`` - Please use the ``breed`` property.
        * ``set_image_type()`` - Please use the ``image_type`` property.
        * ``set_virt_cpus()`` - Please use the ``virt_cpus`` property.
        * ``set_network_count()`` - Please use the ``network_count`` property.
        * ``set_virt_auto_boot()`` - Please use the ``virt_auto_boot`` property.
        * ``set_virt_file_size()`` - Please use the ``virt_file_size`` property.
        * ``set_virt_disk_driver()`` - Please use the ``virt_disk_driver`` property.
        * ``set_virt_ram()`` - Please use the ``virt_ram`` property.
        * ``set_virt_type()`` - Please use the ``virt_type`` property.
        * ``set_virt_bridge()`` - Please use the ``virt_bridge`` property.
        * ``set_virt_path()`` - Please use the ``virt_path`` property.
        * ``get_valid_image_types()``
    * Changes:
        * ``arch``: str -> enums.Archs
        * ``autoinstall``: str -> enums.VALUE_INHERITED
        * ``image_type``: str -> enums.ImageTypes
        * ``virt_auto_boot``: Union[bool, SETTINGS:virt_auto_boot] -> bool
        * ``virt_bridge``: Union[str, SETTINGS:default_virt_bridge] -> str
        * ``virt_disk_driver``: Union[str, SETTINGS:default_virt_disk_driver] -> enums.VirtDiskDrivers
        * ``virt_file_size``: Union[float, SETTINGS:default_virt_file_size] -> float
        * ``virt_ram``: Union[int, SETTINGS:default_virt_ram] -> int
        * ``virt_type``: Union[str, SETTINGS:default_virt_type] -> enums.VirtType
V3.2.2:
    * No changes
V3.2.1:
    * Added:
        * ``kickstart``: Resolves as a proxy to ``autoinstall``
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
    * Added:
        * ``set_autoinstall()``
    * Changes:
        * Rename: ``kickstart`` -> ``autoinstall``
    * Removed:
        * ``set_kickstart()`` - Please use ``set_autoinstall()``
V2.8.5:
    * Inital tracking of changes for the changelog.
    * Added:
        * ``ctime``: float
        * ``depth``: int
        * ``mtime``: float
        * ``parent``: str
        * ``uid``: str

        * ``arch``: str
        * ``kickstart``: str
        * ``breed``: str
        * ``comment``: str
        * ``file``: str
        * ``image_type``: str
        * ``name``: str
        * ``network_count``: int
        * ``os_version``: str
        * ``owners``: Union[list, SETTINGS:default_ownership]
        * ``virt_auto_boot``: Union[bool, SETTINGS:virt_auto_boot]
        * ``virt_bridge``: Union[str, SETTINGS:default_virt_bridge]
        * ``virt_cpus``: int
        * ``virt_disk_driver``: Union[str, SETTINGS:default_virt_disk_driver]
        * ``virt_file_size``: Union[float, SETTINGS:default_virt_file_size]
        * ``virt_path``: str
        * ``virt_ram``: Union[int, SETTINGS:default_virt_ram]
        * ``virt_type``: Union[str, SETTINGS:default_virt_type]
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import copy
from typing import TYPE_CHECKING, Any, List, Union

from cobbler import autoinstall_manager, enums, validate
from cobbler.cexceptions import CX
from cobbler.decorator import InheritableProperty, LazyProperty
from cobbler.items.abstract import item_bootable
from cobbler.utils import input_converters, signatures

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Image(item_bootable.BootableItem):
    """
    A Cobbler Image. Tracks a virtual or physical image, as opposed to a answer file (autoinst) led installation.
    """

    TYPE_NAME = "image"
    COLLECTION_TYPE = "image"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any) -> None:
        """
        Constructor

        :param api: The Cobbler API object which is used for resolving information.
        """
        super().__init__(api)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._arch = enums.Archs.X86_64
        self._autoinstall = enums.VALUE_INHERITED
        self._breed = ""
        self._file = ""
        self._image_type = enums.ImageTypes.DIRECT
        self._network_count = 0
        self._os_version = ""
        self._supported_boot_loaders: List[str] = []
        self._boot_loaders: Union[List[str], str] = enums.VALUE_INHERITED
        self._menu = ""
        self._display_name = ""
        self._virt_auto_boot: Union[str, bool] = enums.VALUE_INHERITED
        self._virt_bridge = enums.VALUE_INHERITED
        self._virt_cpus = 1
        self._virt_disk_driver: enums.VirtDiskDrivers = enums.VirtDiskDrivers.INHERITED
        self._virt_file_size: Union[str, float] = enums.VALUE_INHERITED
        self._virt_path = ""
        self._virt_ram: Union[str, int] = enums.VALUE_INHERITED
        self._virt_type: Union[str, enums.VirtType] = enums.VirtType.INHERITED

        if len(kwargs):
            self.from_dict(kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    def __getattr__(self, name: str):
        if name == "kickstart":
            return self.autoinstall
        raise AttributeError(f'Attribute "{name}" did not exist on object type Image.')

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this image object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = copy.deepcopy(self.to_dict())
        _dict.pop("uid", None)
        return Image(self.api, **_dict)

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

    @InheritableProperty
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
        return self._resolve("autoinstall")

    @autoinstall.setter
    def autoinstall(self, autoinstall: str):
        """
        Set the automatic installation file path, this must be a local file.

        :param autoinstall: local automatic installation template file path
        """
        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(self.api)
        self._autoinstall = autoinstall_mgr.validate_autoinstall_template_file_path(
            autoinstall
        )

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
        if not isinstance(filename, str):  # type: ignore
            raise TypeError("file must be of type str to be parsable.")

        if not filename:
            self._file = ""
            return

        # validate file location format
        if filename.find("://") != -1:
            raise SyntaxError(
                "Invalid image file path location, it should not contain a protocol"
            )
        uri = filename
        auth = ""
        hostname = ""

        if filename.find("@") != -1:
            auth, filename = filename.split("@")
        # extract the hostname
        # 1. if we have a colon, then everything before it is a hostname
        # 2. if we don't have a colon, there is no hostname
        if filename.find(":") != -1:
            hostname, filename = filename.split(":")
        elif filename[0] != "/":
            raise SyntaxError(f"invalid file: {filename}")
        # raise an exception if we don't have a valid path
        if len(filename) > 0 and filename[0] != "/":
            raise SyntaxError(f"file contains an invalid path: {filename}")
        if filename.find("/") != -1:
            _, filename = filename.rsplit("/", 1)

        if len(filename) == 0:
            raise SyntaxError("missing filename")
        if len(auth) > 0 and len(hostname) == 0:
            raise SyntaxError(
                "a hostname must be specified with authentication details"
            )

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
    def os_version(self, os_version: str):
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
        if not isinstance(image_type, (enums.ImageTypes, str)):  # type: ignore
            raise TypeError("image_type must be of type str or enum.ImageTypes")
        if isinstance(image_type, str):
            if not image_type:
                # FIXME: Add None Image type
                self._image_type = enums.ImageTypes.DIRECT
            try:
                image_type = enums.ImageTypes[image_type.upper()]
            except KeyError as error:
                raise ValueError(
                    f"image_type choices include: {list(map(str, enums.ImageTypes))}"
                ) from error
        # str was converted now it must be an enum.ImageTypes
        if not isinstance(image_type, enums.ImageTypes):  # type: ignore
            raise TypeError("image_type needs to be of type enums.ImageTypes")
        if image_type not in enums.ImageTypes:
            raise ValueError(
                f"image type must be one of the following: {', '.join(list(map(str, enums.ImageTypes)))}"
            )
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
    def network_count(self, network_count: Union[int, str]):
        """
        Setter for the number of networks.

        :param network_count: If None or emtpy will be set to ``1``, otherwise the given integer value will be set.
        :raises TypeError: In case the network_count was not of type int.
        """
        if network_count is None or network_count == "":  # type: ignore
            network_count = 1
        if not isinstance(network_count, int):  # type: ignore
            raise TypeError(
                "Field network_count of object image needs to be of type int."
            )
        self._network_count = network_count

    @InheritableProperty
    def virt_auto_boot(self) -> bool:
        r"""
        Whether the VM should be booted when booting the host or not.

        :getter: ``True`` means autoboot is enabled, otherwise VM is not booted automatically.
        :setter: The new state for the property.
        """
        return self._resolve("virt_auto_boot")

    @virt_auto_boot.setter
    def virt_auto_boot(self, num: Union[str, bool]):
        """
        Setter for the virtual automatic boot option.

        :param num: May be "0" (disabled) or "1" (enabled), will be converted to a real bool.
        """
        self._virt_auto_boot = validate.validate_virt_auto_boot(num)

    @InheritableProperty
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

    @InheritableProperty
    def virt_disk_driver(self) -> enums.VirtDiskDrivers:
        """
        The type of disk driver used for storing the image.

        :getter: The enum type representation of the disk driver.
        :setter: May be a ``str`` with the name of the disk driver or from the enum type directly.
        """
        return self._resolve_enum("virt_disk_driver", enums.VirtDiskDrivers)

    @virt_disk_driver.setter
    def virt_disk_driver(self, driver: enums.VirtDiskDrivers):
        """
        Setter for the virtual disk driver.

        :param driver: The virtual disk driver which will be set.
        """
        self._virt_disk_driver = enums.VirtDiskDrivers.to_enum(driver)

    @InheritableProperty
    def virt_ram(self) -> int:
        """
        The amount of RAM given to the guest in MB.

        :getter: The amount of RAM currently assigned to the image.
        :setter: The new amount of ram. Must be an integer.
        """
        return self._resolve("virt_ram")

    @virt_ram.setter
    def virt_ram(self, num: int):
        """
        Setter for the amount of virtual RAM the machine will have.

        :param num: 0 tells Koan to just choose a reasonable default.
        """
        self._virt_ram = validate.validate_virt_ram(num)

    @InheritableProperty
    def virt_type(self) -> enums.VirtType:
        """
        The type of image used.

        :getter: The value of the virtual machine.
        :setter: May be of the enum type or a str which is then converted to the enum type.
        """
        return self._resolve_enum("virt_type", enums.VirtType)

    @virt_type.setter
    def virt_type(self, vtype: enums.VirtType):
        """
        Setter for the virtual type

        :param vtype: May be one of "qemu", "kvm", "xenpv", "xenfv", "vmware", "vmwarew", "openvz" or "auto".
        """
        self._virt_type = enums.VirtType.to_enum(vtype)

    @InheritableProperty
    def virt_bridge(self) -> str:
        r"""
        The name of the virtual bridge used for networking.

        .. warning:: The new validation for the setter is not working. Thus the inheritance from the settings is broken.

        :getter: The name of the bridge.
        :setter: The new name of the bridge. If set to an empty ``str``, it will be taken from the settings.
        """
        return self._resolve("virt_bridge")

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

    @property
    def supported_boot_loaders(self) -> List[str]:
        """
        Read only property which represents the subset of settable bootloaders.

        :getter: The bootloaders which are available for being set.
        """
        if len(self._supported_boot_loaders) == 0:
            self._supported_boot_loaders = signatures.get_supported_distro_boot_loaders(
                self
            )
        return self._supported_boot_loaders

    @InheritableProperty
    def boot_loaders(self) -> List[str]:
        """
        Represents the boot loaders which are able to boot this image.

        :getter: The bootloaders. May be an emtpy list.
        :setter: A list with the supported boot loaders for this image.
        """
        if self._boot_loaders == enums.VALUE_INHERITED:
            return self.supported_boot_loaders
        # The following line is missleading for pyright since it doesn't understand
        # that we use only a constant with str type.
        return self._boot_loaders  # type: ignore

    @boot_loaders.setter  # type: ignore[no-redef]
    def boot_loaders(self, boot_loaders: Union[List[str], str]):
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
            boot_loaders_split = input_converters.input_string_or_list(boot_loaders)

            if not isinstance(boot_loaders_split, list):
                raise TypeError("boot_loaders needs to be of type list!")

            if not set(boot_loaders_split).issubset(self.supported_boot_loaders):
                raise ValueError(
                    f"Error with image {self.name} - not all boot_loaders {boot_loaders_split} are"
                    f" supported {self.supported_boot_loaders}"
                )
            self._boot_loaders = boot_loaders_split
        else:
            self._boot_loaders = []
