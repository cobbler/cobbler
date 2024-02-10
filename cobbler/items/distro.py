"""
Cobbler module that contains the code for a Cobbler distro object.

Changelog:

Schema: From -> To

V3.4.0 (unreleased):
    * Added:
        * ``find_distro_path()``
        * ``link_distro()``
    * Changed:
        * Constructor: ``kwargs`` can now be used to seed the item during creation.
        * ``children``: The property was moved to the base class.
        * ``from_dict()``: The method was moved to the base class.
    * Removed:
        * ``fetchable_files``
V3.3.4 (unreleased):
    * No changes
V3.3.3:
    * Changed:
        * ``redhat_management_key``: Inherits from the settings again
V3.3.2:
    * No changes
V3.3.1:
    * No changes
V3.3.0:
    * This release switched from pure attributes to properties (getters/setters).
    * Added:
        * ``from_dict()``
    * Moved to base class (Item):
        * ``ctime``: float
        * ``depth``: int
        * ``mtime``: float
        * ``uid``: str
        * ``kernel_options``: dict
        * ``kernel_options_post``: dict
        * ``autoinstall_meta``: dict
        * ``boot_files``: list/dict
        * ``template_files``: list/dict
        * ``comment``: str
        * ``name``: str
        * ``owners``: list[str]
    * Changed:
        * ``tree_build_time``: str -> float
        * ``arch``: str -> Union[list, str]
        * ``fetchable_files``: list/dict? -> dict
        * ``boot_loader`` -> boot_loaders (rename)
    * Removed:
        * ``get_fields()``
        * ``get_parent``
        * ``set_kernel()`` - Please use the property ``kernel``
        * ``set_remote_boot_kernel()`` - Please use the property ``remote_boot_kernel``
        * ``set_tree_build_time()`` - Please use the property ``tree_build_time``
        * ``set_breed()`` - Please use the property ``breed``
        * ``set_os_version()`` - Please use the property ``os_version``
        * ``set_initrd()`` - Please use the property ``initrd``
        * ``set_remote_boot_initrd()`` - Please use the property ``remote_boot_initrd``
        * ``set_source_repos()`` - Please use the property ``source_repos``
        * ``set_arch()`` - Please use the property ``arch``
        * ``get_arch()`` - Please use the property ``arch``
        * ``set_supported_boot_loaders()`` - Please use the property ``supported_boot_loaders``. It is readonly.
        * ``set_boot_loader()`` - Please use the property ``boot_loader``
        * ``set_redhat_management_key()`` - Please use the property ``redhat_management_key``
        * ``get_redhat_management_key()`` - Please use the property ``redhat_management_key``
V3.2.2:
    * No changes
V3.2.1:
    * Added:
        * ``kickstart``: Resolves as a proxy to ``autoinstall``
V3.2.0:
    * No changes
V3.1.2:
    * Added:
        * ``remote_boot_kernel``: str
        * ``remote_grub_kernel``: str
        * ``remote_boot_initrd``: str
        * ``remote_grub_initrd``: str
V3.1.1:
    * No changes
V3.1.0:
    * Added:
        * ``get_arch()``
V3.0.1:
    * File was moved from ``cobbler/item_distro.py`` to ``cobbler/items/distro.py``.
V3.0.0:
    * Added:
        * ``boot_loader``: Union[str, inherit]
    * Changed:
        * rename: ``ks_meta`` -> ``autoinstall_meta``
        * ``redhat_management_key``: Union[str, inherit] -> str
    * Removed:
        * ``redhat_management_server``: Union[str, inherit]
V2.8.5:
    * Inital tracking of changes for the changelog.
    * Added:
        * ``name``: str
        * ``ctime``: float
        * ``mtime``: float
        * ``uid``: str
        * ``owners``: Union[list, SETTINGS:default_ownership]
        * ``kernel``: str
        * ``initrd``: str
        * ``kernel_options``: dict
        * ``kernel_options_post``: dict
        * ``ks_meta``: dict
        * ``arch``: str
        * ``breed``: str
        * ``os_version``: str
        * ``source_repos``: list
        * ``depth``: int
        * ``comment``: str
        * ``tree_build_time``: str
        * ``mgmt_classes``: list
        * ``boot_files``: list/dict?
        * ``fetchable_files``: list/dict?
        * ``template_files``: list/dict?
        * ``redhat_management_key``: Union[str, inherit]
        * ``redhat_management_server``: Union[str, inherit]
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import copy
import glob
import os
from typing import TYPE_CHECKING, Any, Dict, List, Union

from cobbler import enums, grub, utils, validate
from cobbler.cexceptions import CX
from cobbler.decorator import InheritableProperty, LazyProperty
from cobbler.items.abstract import item_bootable
from cobbler.utils import input_converters, signatures

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Distro(item_bootable.BootableItem):
    """
    A Cobbler distribution object
    """

    # Constants
    TYPE_NAME = "distro"
    COLLECTION_TYPE = "distro"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any):
        """
        This creates a Distro object.

        :param api: The Cobbler API object which is used for resolving information.
        """
        super().__init__(api)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._tree_build_time = 0.0
        self._arch = enums.Archs.X86_64
        self._boot_loaders: Union[List[str], str] = enums.VALUE_INHERITED
        self._breed = ""
        self._initrd = ""
        self._kernel = ""
        self._mgmt_classes = []
        self._os_version = ""
        self._redhat_management_key = enums.VALUE_INHERITED
        self._source_repos = []
        self._remote_boot_kernel = ""
        self._remote_grub_kernel = ""
        self._remote_boot_initrd = ""
        self._remote_grub_initrd = ""
        self._supported_boot_loaders: List[str] = []

        if len(kwargs) > 0:
            self.from_dict(kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    def __getattr__(self, name: str) -> Any:
        if name == "ks_meta":
            return self.autoinstall_meta
        raise AttributeError(f'Attribute "{name}" did not exist on object type Distro.')

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone a distro object.

        :return: The cloned object. Not persisted on the disk or in a database.
        """
        # FIXME: Change unique base attributes
        _dict = copy.deepcopy(self.to_dict())
        # Drop attributes which are computed from other attributes
        computed_properties = ["remote_grub_initrd", "remote_grub_kernel", "uid"]
        for property_name in computed_properties:
            _dict.pop(property_name, None)
        return Distro(self.api, **_dict)

    @classmethod
    def _remove_depreacted_dict_keys(cls, dictionary: Dict[Any, Any]):
        r"""
        See :meth:`~cobbler.items.item.Item._remove_depreacted_dict_keys`.

        :param dictionary: The dict to update
        """
        if "parent" in dictionary:
            dictionary.pop("parent")
        super()._remove_depreacted_dict_keys(dictionary)

    def check_if_valid(self):
        """
        Check if a distro object is valid. If invalid an exception is raised.
        """
        super().check_if_valid()
        if not self.inmemory:
            return
        if self.kernel == "" and self.remote_boot_kernel == "":
            raise CX(
                f"Error with distro {self.name} - either kernel or remote-boot-kernel is required"
            )

    #
    # specific methods for item.Distro
    #

    @property
    def parent(self):
        """
        Distros don't have parent objects.
        """
        return None

    @parent.setter
    def parent(self, parent: str):
        """
        Setter for the parent property.

        :param value: Is ignored.
        """
        self.logger.warning(
            "Setting the parent of a distribution is not supported. Ignoring action!"
        )

    @LazyProperty
    def kernel(self) -> str:
        """
        Specifies a kernel. The kernel parameter is a full path, a filename in the configured kernel directory or a
        directory path that would contain a selectable kernel. Kernel naming conventions are checked, see docs in the
        utils module for ``find_kernel``.

        :getter: The last successfully validated kernel path.
        :setter: May raise a ``ValueError`` or ``TypeError`` in case of validation errors.
        """
        return self._kernel

    @kernel.setter
    def kernel(self, kernel: str):
        """
        Setter for the ``kernel`` property.

        :param kernel: The path to the kernel.
        :raises TypeError: If kernel was not of type str.
        :raises ValueError: If the kernel was not found.
        """
        if not isinstance(kernel, str):  # type: ignore
            raise TypeError("kernel was not of type str")
        if kernel:
            if not utils.find_kernel(kernel):
                raise ValueError(
                    "kernel not found or it does not match with allowed kernel filename pattern"
                    f"[{utils.re_kernel.pattern}]: {kernel}."
                )
        self._kernel = kernel

    @LazyProperty
    def remote_boot_kernel(self) -> str:
        """
        URL to a remote kernel. If the bootloader supports this feature, it directly tries to retrieve the kernel and
        boot it. (grub supports tftp and http protocol and server must be an IP).

        :getter: Returns the current remote URL to boot from.
        :setter: Raises a ``TypeError`` or ``ValueError`` in case the provided value was not correct.
        """
        # TODO: Obsolete it and merge with kernel property
        return self._remote_boot_kernel

    @remote_boot_kernel.setter
    def remote_boot_kernel(self, remote_boot_kernel: str):
        """
        Setter for the ``remote_boot_kernel`` property.

        :param remote_boot_kernel: The new URL to the remote booted kernel.
        :raises TypeError: Raised in case the URL is not of type str.
        :raises ValueError: Raised in case the validation is not succeeding.
        """
        if not isinstance(remote_boot_kernel, str):  # type: ignore
            raise TypeError(
                "Field remote_boot_kernel of distro needs to be of type str!"
            )
        if not remote_boot_kernel:
            self._remote_grub_kernel = remote_boot_kernel
            self._remote_boot_kernel = remote_boot_kernel
            return
        if not validate.validate_boot_remote_file(remote_boot_kernel):
            raise ValueError(
                "remote_boot_kernel needs to be a valid URL starting with tftp or http!"
            )
        parsed_url = grub.parse_grub_remote_file(remote_boot_kernel)
        if parsed_url is None:
            raise ValueError(
                f"Invalid URL for remote boot kernel: {remote_boot_kernel}"
            )
        self._remote_grub_kernel = parsed_url
        self._remote_boot_kernel = remote_boot_kernel

    @LazyProperty
    def tree_build_time(self) -> float:
        """
        Represents the import time of the distro. If not imported, this field is not meaningful.

        :getter:
        :setter:
        """
        return self._tree_build_time

    @tree_build_time.setter
    def tree_build_time(self, datestamp: float):
        r"""
        Setter for the ``tree_build_time`` property.

        :param datestamp: The datestamp to save the builddate. There is an attempt to convert it to a float, so please
                          make sure it is compatible to this.
        :raises TypeError: In case the value was not of type ``float``.
        """
        if isinstance(datestamp, int):
            datestamp = float(datestamp)
        if not isinstance(datestamp, float):  # type: ignore
            raise TypeError("datestamp needs to be of type float")
        self._tree_build_time = datestamp

    @LazyProperty
    def breed(self) -> str:
        """
        The repository system breed. This decides some defaults for most actions with a repo in Cobbler.

        :getter: The breed detected.
        :setter: May raise a ``ValueError`` or ``TypeError`` in case the given value is wrong.
        """
        return self._breed

    @breed.setter
    def breed(self, breed: str):
        """
        Set the Operating system breed.

        :param breed: The new breed to set.
        """
        self._breed = validate.validate_breed(breed)

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
        Set the Operating System Version.

        :param os_version: The new OS Version.
        """
        self._os_version = validate.validate_os_version(os_version, self.breed)

    @LazyProperty
    def initrd(self) -> str:
        r"""
        Specifies an initrd image. Path search works as in set_kernel. File must be named appropriately.

        :getter: The current path to the initrd.
        :setter: May raise a ``TypeError`` or ``ValueError`` in case the validation is not successful.
        """
        return self._initrd

    @initrd.setter
    def initrd(self, initrd: str):
        r"""
        Setter for the ``initrd`` property.

        :param initrd: The new path to the ``initrd``.
        :raises TypeError: In case the value was not of type ``str``.
        :raises ValueError: In case the new value was not found or specified.
        """
        if not isinstance(initrd, str):  # type: ignore
            raise TypeError("initrd must be of type str")
        if initrd:
            if not utils.find_initrd(initrd):
                raise ValueError(f"initrd not found: {initrd}")
        self._initrd = initrd

    @LazyProperty
    def remote_grub_kernel(self) -> str:
        r"""
        This is tied to the ``remote_boot_kernel`` property. It contains the URL of that field in a format which grub
        can use directly.

        :getter: The computed URL from ``remote_boot_kernel``.
        """
        return self._remote_grub_kernel

    @LazyProperty
    def remote_grub_initrd(self) -> str:
        r"""
        This is tied to the ``remote_boot_initrd`` property. It contains the URL of that field in a format which grub
        can use directly.

        :getter: The computed URL from ``remote_boot_initrd``.
        """
        return self._remote_grub_initrd

    @LazyProperty
    def remote_boot_initrd(self) -> str:
        r"""
        URL to a remote initrd. If the bootloader supports this feature, it directly tries to retrieve the initrd and
        boot it. (grub supports tftp and http protocol and server must be an IP).

        :getter: Returns the current remote URL to boot from.
        :setter: Raises a ``TypeError`` or ``ValueError`` in case the provided value was not correct.
        """
        return self._remote_boot_initrd

    @remote_boot_initrd.setter
    def remote_boot_initrd(self, remote_boot_initrd: str):
        r"""
        The setter for the ``remote_boot_initrd`` property.

        :param remote_boot_initrd: The new value for the property.
        :raises TypeError: In case the value was not of type ``str``.
        :raises ValueError: In case the new value could not be validated successfully.
        """
        if not isinstance(remote_boot_initrd, str):  # type: ignore
            raise TypeError("remote_boot_initrd must be of type str!")
        if not remote_boot_initrd:
            self._remote_boot_initrd = remote_boot_initrd
            self._remote_grub_initrd = remote_boot_initrd
            return
        if not validate.validate_boot_remote_file(remote_boot_initrd):
            raise ValueError(
                "remote_boot_initrd needs to be a valid URL starting with tftp or http!"
            )
        parsed_url = grub.parse_grub_remote_file(remote_boot_initrd)
        if parsed_url is None:
            raise ValueError(
                f"Invalid URL for remote boot initrd: {remote_boot_initrd}"
            )
        self._remote_grub_initrd = parsed_url
        self._remote_boot_initrd = remote_boot_initrd

    @LazyProperty
    def source_repos(self) -> List[Any]:
        """
        A list of http:// URLs on the Cobbler server that point to yum configuration files that can be used to
        install core packages. Use by ``cobbler import`` only.

        :getter: The source repos used.
        :setter: The new list of source repos to use.
        """
        return self._source_repos

    @source_repos.setter
    def source_repos(self, repos: List[Any]):
        r"""
        Setter for the ``source_repos`` property.

        :param repos: The list of URLs.
        :raises TypeError: In case the value was not of type ``str``.
        """
        if not isinstance(repos, list):  # type: ignore
            raise TypeError(
                "Field source_repos in object distro needs to be of type list."
            )
        self._source_repos = repos

    @LazyProperty
    def arch(self):
        """
        The field is mainly relevant to PXE provisioning.

        Using an alternative distro type allows for dhcpd.conf templating to "do the right thing" with those
        systems -- this also relates to bootloader configuration files which have different syntax for different
        distro types (because of the bootloaders).

        This field is named "arch" because mainly on Linux, we only care about the architecture, though if (in the
        future) new provisioning types are added, an arch value might be something like "bsd_x86".

        :return: Return the current architecture.
        """
        return self._arch

    @arch.setter
    def arch(self, arch: Union[str, enums.Archs]):
        """
        The setter for the arch property.

        :param arch: The architecture of the operating system distro.
        """
        self._arch = enums.Archs.to_enum(arch)

    @property
    def supported_boot_loaders(self) -> List[str]:
        """
        Some distributions, particularly on powerpc, can only be netbooted using specific bootloaders.

        :return: The bootloaders which are available for being set.
        """
        if len(self._supported_boot_loaders) == 0:
            self._supported_boot_loaders = signatures.get_supported_distro_boot_loaders(
                self
            )
        return self._supported_boot_loaders

    @InheritableProperty
    def boot_loaders(self) -> List[str]:
        """
        All boot loaders for which Cobbler generates entries for.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The bootloaders.
        :setter: Validates this against the list of well-known bootloaders and raises a ``TypeError`` or ``ValueError``
                 in case the validation goes south.
        """
        if self._boot_loaders == enums.VALUE_INHERITED:
            return self.supported_boot_loaders
        # The following line is missleading for pyright since it doesn't understand
        # that we use only a constant with str type.
        return self._boot_loaders  # type: ignore

    @boot_loaders.setter  # type: ignore[no-redef]
    def boot_loaders(self, boot_loaders: Union[str, List[str]]):
        """
        Set the bootloader for the distro.

        :param boot_loaders: The list with names of the bootloaders. Must be one of the supported ones.
        :raises TypeError: In case the value could not be converted to a list or was not of type list.
        :raises ValueError: In case the boot loader is not in the list of valid boot loaders.
        """
        if isinstance(boot_loaders, str):
            # allow the magic inherit string to persist, otherwise split the string.
            if boot_loaders == enums.VALUE_INHERITED:
                self._boot_loaders = enums.VALUE_INHERITED
                return
            boot_loaders = input_converters.input_string_or_list(boot_loaders)

        if not isinstance(boot_loaders, list):  # type: ignore
            raise TypeError("boot_loaders needs to be of type list!")

        if not set(boot_loaders).issubset(self.supported_boot_loaders):
            raise ValueError(
                f"Invalid boot loader names: {boot_loaders}. Supported boot loaders are:"
                f" {' '.join(self.supported_boot_loaders)}"
            )
        self._boot_loaders = boot_loaders

    @InheritableProperty
    def redhat_management_key(self) -> str:
        r"""
        Get the redhat management key. This is probably only needed if you have spacewalk, uyuni or SUSE Manager
        running.

        .. note:: This property can be set to ``<<inherit>>``.

        :return: The key as a string.
        """
        return self._resolve("redhat_management_key")

    @redhat_management_key.setter  # type: ignore[no-redef]
    def redhat_management_key(self, management_key: str):
        """
        Set the redhat management key. This is probably only needed if you have spacewalk, uyuni or SUSE Manager
        running.

        :param management_key: The redhat management key.
        """
        if not isinstance(management_key, str):  # type: ignore
            raise TypeError(
                "Field redhat_management_key of object distro needs to be of type str!"
            )
        self._redhat_management_key = management_key

    def find_distro_path(self):
        r"""
        This returns the absolute path to the distro under the ``distro_mirror`` directory. If that directory doesn't
        contain the kernel, the directory of the kernel in the distro is returned.

        :return: The path to the distribution files.
        """
        possible_dirs = glob.glob(self.api.settings().webdir + "/distro_mirror/*")
        for directory in possible_dirs:
            if os.path.dirname(self.kernel).find(directory) != -1:
                return os.path.join(
                    self.api.settings().webdir, "distro_mirror", directory
                )
        # non-standard directory, assume it's the same as the directory in which the given distro's kernel is
        return os.path.dirname(self.kernel)

    def link_distro(self):
        """
        Link a Cobbler distro from its source into the web directory to make it reachable from the outside.
        """
        # find the tree location
        base = self.find_distro_path()
        if not base:
            return

        dest_link = os.path.join(self.api.settings().webdir, "links", self.name)

        # create the links directory only if we are mirroring because with SELinux Apache can't symlink to NFS (without
        # some doing)

        if not os.path.lexists(dest_link):
            try:
                os.symlink(base, dest_link)
            except Exception:
                # FIXME: This shouldn't happen but I've (jsabo) seen it...
                self.logger.warning(
                    "- symlink creation failed: %s, %s", base, dest_link
                )
