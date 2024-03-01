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
from typing import List, Union

from cobbler import enums, validate
from cobbler.items import item
from cobbler import utils
from cobbler.cexceptions import CX
from cobbler import grub
from cobbler.decorator import InheritableProperty, LazyProperty


class Distro(item.Item):
    """
    A Cobbler distribution object
    """

    # Constants
    TYPE_NAME = "distro"
    COLLECTION_TYPE = "distro"

    def __init__(self, api, *args, **kwargs):
        """
        This creates a Distro object.

        :param api: The Cobbler API object which is used for resolving information.
        :param args: Place for extra parameters in this distro object.
        :param kwargs: Place for extra parameters in this distro object.
        """
        super().__init__(api, *args, **kwargs)
        self._has_initialized = False

        self._tree_build_time = 0.0
        self._arch = enums.Archs.X86_64
        self._boot_loaders: Union[list, str] = enums.VALUE_INHERITED
        self._breed = ""
        self._initrd = ""
        self._kernel = ""
        self._mgmt_classes = []
        self._os_version = ""
        self._redhat_management_key = enums.VALUE_INHERITED
        self._source_repos = []
        self._fetchable_files = {}
        self._remote_boot_kernel = ""
        self._remote_grub_kernel = ""
        self._remote_boot_initrd = ""
        self._remote_grub_initrd = ""
        self._supported_boot_loaders = []

        if not self._has_initialized:
            self._has_initialized = True

    def __getattr__(self, name):
        if name == "ks_meta":
            return self.autoinstall_meta
        raise AttributeError("Attribute \"%s\" did not exist on object type Distro." % name)

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone a distro object.

        :return: The cloned object. Not persisted on the disk or in a database.
        """
        # FIXME: Change unique base attributes
        _dict = self.to_dict()
        # Drop attributes which are computed from other attributes
        computed_properties = ["remote_grub_initrd", "remote_grub_kernel"]
        for property_name in computed_properties:
            _dict.pop(property_name, None)
        cloned = Distro(self.api)
        cloned.from_dict(_dict)
        cloned.uid = uuid.uuid4().hex
        return cloned

    @classmethod
    def _remove_depreacted_dict_keys(cls, dictionary: dict):
        r"""
        See :meth:`~cobbler.items.item.Item._remove_depreacted_dict_keys`.

        :param dictionary: The dict to update
        """
        if "parent" in dictionary:
            dictionary.pop("parent")
        super()._remove_depreacted_dict_keys(dictionary)

    def from_dict(self, dictionary: dict):
        """
        Initializes the object with attributes from the dictionary.

        :param dictionary: The dictionary with values.
        """
        if "name" in dictionary:
            self.name = dictionary["name"]
        self._remove_depreacted_dict_keys(dictionary)
        super().from_dict(dictionary)

    def check_if_valid(self):
        """
        Check if a distro object is valid. If invalid an exception is raised.
        """
        super().check_if_valid()
        if not self.inmemory:
            return
        if self.kernel is None:
            raise CX("Error with distro %s - kernel is required" % self.name)

    #
    # specific methods for item.Distro
    #

    @LazyProperty
    def parent(self):
        """
        Distros don't have parent objects.
        """
        return None

    @parent.setter
    def parent(self, value):
        """
        Setter for the parent property.

        :param value: Is ignored.
        """
        self.logger.warning("Setting the parent of a distribution is not supported. Ignoring action!")

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
        if not isinstance(kernel, str):
            raise TypeError("kernel was not of type str")
        if not utils.find_kernel(kernel):
            raise ValueError(
                "kernel not found or it does not match with allowed kernel filename pattern [%s]: %s."
                % (utils._re_kernel.pattern, kernel)
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
        if not isinstance(remote_boot_kernel, str):
            raise TypeError("Field remote_boot_kernel of distro needs to be of type str!")
        if not remote_boot_kernel:
            self._remote_grub_kernel = remote_boot_kernel
            self._remote_boot_kernel = remote_boot_kernel
            return
        if not validate.validate_boot_remote_file(remote_boot_kernel):
            raise ValueError("remote_boot_kernel needs to be a valid URL starting with tftp or http!")
        parsed_url = grub.parse_grub_remote_file(remote_boot_kernel)
        if parsed_url is None:
            raise ValueError("Invalid URL for remote boot kernel: %s" % remote_boot_kernel)
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
        if not isinstance(datestamp, float):
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
        """
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
        if not isinstance(initrd, str):
            raise TypeError("initrd must be of type str")
        if not initrd:
            raise ValueError("initrd not specified")
        if utils.find_initrd(initrd):
            self._initrd = initrd
            return
        raise ValueError("initrd not found")

    @LazyProperty
    def remote_grub_kernel(self) -> str:
        """
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
        """
        The setter for the ``remote_boot_initrd`` property.

        :param remote_boot_initrd: The new value for the property.
        :raises TypeError: In case the value was not of type ``str``.
        :raises ValueError: In case the new value could not be validated successfully.
        """
        if not isinstance(remote_boot_initrd, str):
            raise TypeError("remote_boot_initrd must be of type str!")
        if not remote_boot_initrd:
            self._remote_boot_initrd = remote_boot_initrd
            self._remote_grub_initrd = remote_boot_initrd
            return
        if not validate.validate_boot_remote_file(remote_boot_initrd):
            raise ValueError("remote_boot_initrd needs to be a valid URL starting with tftp or http!")
        parsed_url = grub.parse_grub_remote_file(remote_boot_initrd)
        if parsed_url is None:
            raise ValueError("Invalid URL for remote boot initrd: %s" % remote_boot_initrd)
        self._remote_grub_initrd = parsed_url
        self._remote_boot_initrd = remote_boot_initrd

    @LazyProperty
    def source_repos(self) -> list:
        """
        A list of http:// URLs on the Cobbler server that point to yum configuration files that can be used to
        install core packages. Use by ``cobbler import`` only.

        :getter: The source repos used.
        :setter: The new list of source repos to use.
        """
        return self._source_repos

    @source_repos.setter
    def source_repos(self, repos: list):
        r"""
        Setter for the ``source_repos`` property.

        :param repos: The list of URLs.
        :raises TypeError: In case the value was not of type ``str``.
        """
        if not isinstance(repos, list):
            raise TypeError("Field source_repos in object distro needs to be of type list.")
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

    @LazyProperty
    def supported_boot_loaders(self):
        """
        Some distributions, particularly on powerpc, can only be netbooted using specific bootloaders.

        :return: The bootloaders which are available for being set.
        """
        if len(self._supported_boot_loaders) == 0:
            self._supported_boot_loaders = utils.get_supported_distro_boot_loaders(self)
        return self._supported_boot_loaders

    @InheritableProperty
    def boot_loaders(self) -> list:
        """
        All boot loaders for which Cobbler generates entries for.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The bootloaders.
        :setter: Validates this against the list of well-known bootloaders and raises a ``TypeError`` or ``ValueError``
                 in case the validation goes south.
        """
        if self._boot_loaders == enums.VALUE_INHERITED:
            return self.supported_boot_loaders
        return self._boot_loaders

    @boot_loaders.setter
    def boot_loaders(self, boot_loaders: List[str]):
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
            else:
                boot_loaders = utils.input_string_or_list(boot_loaders)

        if not isinstance(boot_loaders, list):
            raise TypeError("boot_loaders needs to be of type list!")

        if not set(boot_loaders).issubset(self.supported_boot_loaders):
            raise ValueError("Invalid boot loader names: %s. Supported boot loaders are: %s" %
                             (boot_loaders, ' '.join(self.supported_boot_loaders)))
        self._boot_loaders = boot_loaders

    @InheritableProperty
    def redhat_management_key(self) -> str:
        """
        Get the redhat management key. This is probably only needed if you have spacewalk, uyuni or SUSE Manager
        running.

        .. note:: This property can be set to ``<<inherit>>``.

        :return: The key as a string.
        """
        return self._resolve("redhat_management_key")

    @redhat_management_key.setter
    def redhat_management_key(self, management_key: str):
        """
        Set the redhat management key. This is probably only needed if you have spacewalk, uyuni or SUSE Manager
        running.

        :param management_key: The redhat management key.
        """
        if not isinstance(management_key, str):
            raise TypeError("Field redhat_management_key of object distro needs to be of type str!")
        self._redhat_management_key = management_key

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
