"""
Virtualization option management for Cobbler items.
"""

from typing import TYPE_CHECKING, Any, Union

from cobbler import enums, validate
from cobbler.items.options.base import ItemOption

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.image import Image
    from cobbler.items.profile import Profile
    from cobbler.items.system import System

    InheritableProperty = property
    LazyProperty = property
else:
    from cobbler.decorator import InheritableProperty, LazyProperty


class VirtOption(ItemOption[Union["Image", "Profile", "System"]]):
    """
    Option class for managing virtualization settings for Cobbler Image, Profile, and System items.

    Provides properties for auto boot, CPU core count, disk driver, RAM, and other virtualization options.
    """

    def __init__(
        self,
        api: "CobblerAPI",
        item: Union["Image", "Profile", "System"],
        **kwargs: Any
    ) -> None:
        super().__init__(api=api, item=item, **kwargs)
        self._auto_boot: Union[bool, str] = enums.VALUE_INHERITED
        self._cpus: Union[int, str] = enums.VALUE_INHERITED
        self._disk_driver = enums.VirtDiskDrivers.INHERITED
        self._file_size: Union[float, str] = enums.VALUE_INHERITED
        self._path = enums.VALUE_INHERITED
        self._pxe_boot = False
        self._ram: Union[int, str] = enums.VALUE_INHERITED
        self._type = enums.VirtType.INHERITED

        if len(kwargs) > 0:
            self.from_dict(kwargs)

    @property
    def parent_name(self) -> str:
        return "virt"

    @InheritableProperty
    def auto_boot(self) -> bool:
        """
        auto_boot property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``auto_boot``.
        :setter: Sets the value for the property ``auto_boot``.
        """
        return self._resolve([self.parent_name, "auto_boot"])

    @auto_boot.setter
    def auto_boot(self, value: Union[bool, str]):
        """
        Setter for the auto_boot of the System class.

        :param value: Weather the VM should automatically boot or not.
        """
        if value == enums.VALUE_INHERITED:
            self._auto_boot = enums.VALUE_INHERITED
            return
        # TODO: An Image cannot inherit from anything
        self._auto_boot = validate.validate_virt_auto_boot(value)

    @InheritableProperty
    def cpus(self) -> int:
        """
        cpus property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``virt_cpus``.
        :setter: Sets the value for the property ``virt_cpus``.
        """
        return self._resolve([self.parent_name, "cpus"])

    @cpus.setter
    def cpus(self, num: Union[int, str]):
        """
        Setter for the cpus of the System class.

        :param num: The new value for the number of CPU cores.
        """
        if num == enums.VALUE_INHERITED:
            self._cpus = enums.VALUE_INHERITED
            return
        self._cpus = validate.validate_virt_cpus(num)

    @InheritableProperty
    def file_size(self) -> float:
        """
        file_size property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``file_size``.
        :setter: Sets the value for the property ``file_size``.
        """
        return self._resolve([self.parent_name, "file_size"])

    @file_size.setter
    def file_size(self, num: float):
        """
        Setter for the file_size of the System class.

        :param num:
        """
        self._file_size = validate.validate_virt_file_size(num)

    @InheritableProperty
    def disk_driver(self) -> enums.VirtDiskDrivers:
        """
        disk_driver property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``disk_driver``.
        :setter: Sets the value for the property ``disk_driver``.
        """
        return self._resolve_enum(
            [self.parent_name, "disk_driver"], enums.VirtDiskDrivers
        )

    @disk_driver.setter
    def disk_driver(self, driver: Union[str, enums.VirtDiskDrivers]):
        """
        Setter for the disk_driver of the System class.

        :param driver: The new disk driver for the virtual disk.
        """
        self._disk_driver = enums.VirtDiskDrivers.to_enum(driver)

    @LazyProperty
    def pxe_boot(self) -> bool:
        """
        pxe_boot property.

        :getter: Returns the value for ``pxe_boot``.
        :setter: Sets the value for the property ``pxe_boot``.
        """
        return self._pxe_boot

    @pxe_boot.setter
    def pxe_boot(self, num: bool):
        """
        Setter for the pxe_boot of the System class.

        :param num:
        """
        self._pxe_boot = validate.validate_virt_pxe_boot(num)

    @InheritableProperty
    def ram(self) -> int:
        """
        ram property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``ram``.
        :setter: Sets the value for the property ``ram``.
        """
        return self._resolve([self.parent_name, "ram"])

    @ram.setter
    def ram(self, num: Union[int, str]):
        """
        Setter for the ram of the System class.

        :param num: The new amount of RAM in MBs.
        """
        self._ram = validate.validate_virt_ram(num)

    @InheritableProperty
    def type(self) -> enums.VirtType:
        """
        type property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``type``.
        :setter: Sets the value for the property ``type``.
        """
        return self._resolve_enum([self.parent_name, "type"], enums.VirtType)

    @type.setter
    def type(self, vtype: Union[enums.VirtType, str]):
        """
        Setter for the type of the System class.

        :param vtype: The new virtual type.
        """
        self._type = enums.VirtType.to_enum(vtype)

    @InheritableProperty
    def path(self) -> str:
        """
        path property.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the value for ``path``.
        :setter: Sets the value for the property ``path``.
        """
        if self._item.TYPE_NAME in ("profile", "image"):  # type: ignore
            return self._path
        return self._resolve([self.parent_name, "path"])

    @path.setter
    def path(self, path: str):
        """
        Setter for the path of the System class.

        :param path: The new path.
        """
        if self._item.TYPE_NAME in ("profile", "image") and path == enums.VALUE_INHERITED:  # type: ignore
            raise ValueError("Profiles and Images cannot set virt.path as inherited!")
        self._path = validate.validate_virt_path(
            path, for_system=self._item.TYPE_NAME == "system"  # type: ignore
        )
