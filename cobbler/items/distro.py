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


class Distro(item.Item):
    """
    A Cobbler distribution object
    """

    COLLECTION_TYPE = "distro"

    def __init__(self, api, *args, **kwargs):
        """
        This creates a Distro object.

        :param args: Place for extra parameters in this distro object.
        :param kwargs: Place for extra parameters in this distro object.
        """
        super().__init__(api, *args, **kwargs)
        self._tree_build_time = 0.0
        self._arch = enums.Archs.X86_64
        self._boot_loaders = []
        self._breed = ""
        self._initrd = ""
        self._kernel = ""
        self._mgmt_classes = []
        self._os_version = ""
        self._owners = []
        self._redhat_management_key = ""
        self._source_repos = []
        self._fetchable_files = {}
        self._remote_boot_kernel = ""
        self._remote_grub_kernel = ""
        self._remote_boot_initrd = ""
        self._remote_grub_initrd = ""
        self._supported_boot_loaders = []

    def __getattr__(self, name):
        if name == "ks_meta":
            return self.autoinstall_meta
        return self[name]

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
        cloned = Distro(self.api)
        cloned.from_dict(_dict)
        cloned.uid = uuid.uuid4().hex
        return cloned

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

    def check_if_valid(self):
        """
        Check if a distro object is valid. If invalid an exception is raised.
        """
        if self.name is None:
            raise CX("name is required")
        if self.kernel is None:
            raise CX("Error with distro %s - kernel is required" % self.name)
        if self.initrd is None:
            raise CX("Error with distro %s - initrd is required" % self.name)

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
    def parent(self, value):
        """
        TODO

        :param value:
        :return:
        """
        self.logger.warning("Setting the parent of a distribution is not supported. Ignoring action!")
        pass

    @property
    def kernel(self):
        """
        TODO

        :return:
        """
        return self._kernel

    @kernel.setter
    def kernel(self, kernel: str):
        """
        Specifies a kernel. The kernel parameter is a full path, a filename in the configured kernel directory or a
        directory path that would contain a selectable kernel. Kernel naming conventions are checked, see docs in the
        utils module for ``find_kernel``.

        :param kernel: The path to the kernel.
        :raises TypeError: If kernel was not of type str.
        :raises ValueError: If the kernel was not found.
        """
        if not isinstance(kernel, str):
            raise TypeError("kernel was not of type str")
        if not utils.find_kernel(kernel):
            raise ValueError("kernel not found: %s" % kernel)
        self._kernel = kernel

    @property
    def remote_boot_kernel(self):
        """
        TODO

        :return:
        """
        return self._remote_boot_kernel

    @remote_boot_kernel.setter
    def remote_boot_kernel(self, remote_boot_kernel):
        """
        URL to a remote kernel. If the bootloader supports this feature, it directly tries to retrieve the kernel and
        boot it. (grub supports tftp and http protocol and server must be an IP).
        TODO: Obsolete it and merge with kernel property
        """
        if remote_boot_kernel:
            parsed_url = grub.parse_grub_remote_file(remote_boot_kernel)
            if parsed_url is None:
                raise ValueError("Invalid URL for remote boot kernel: %s" % remote_boot_kernel)
            self._remote_grub_kernel = parsed_url
            self._remote_boot_kernel = remote_boot_kernel
            return
        self._remote_grub_kernel = remote_boot_kernel
        self._remote_boot_kernel = remote_boot_kernel

    @property
    def tree_build_time(self):
        """
        TODO

        :return:
        """
        return self._tree_build_time

    @tree_build_time.setter
    def tree_build_time(self, datestamp: float):
        """
        Sets the import time of the distro. If not imported, this field is not meaningful.

        :param datestamp: The datestamp to save the builddate. There is an attempt to convert it to a float, so please
                          make sure it is compatible to this.
        """
        if isinstance(datestamp, int):
            datestamp = float(datestamp)
        if not isinstance(datestamp, float):
            raise TypeError("datestamp needs to be of type float")
        self._tree_build_time = datestamp

    @property
    def breed(self):
        """
        TODO

        :return:
        """
        return self._breed

    @breed.setter
    def breed(self, breed: str):
        """
        Set the Operating system breed.

        :param breed: The new breed to set.
        """
        self._breed = validate.validate_breed(breed)

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
        Set the Operating System Version.

        :param os_version: The new OS Version.
        """
        self._os_version = validate.validate_os_version(os_version, self.breed)

    @property
    def initrd(self):
        """
        TODO

        :return:
        """
        return self._initrd

    @initrd.setter
    def initrd(self, initrd: str):
        """
        Specifies an initrd image. Path search works as in set_kernel. File must be named appropriately.

        :param initrd: The new path to the ``initrd``.
        """
        if not isinstance(initrd, str):
            raise TypeError("initrd must be of type str")
        if not initrd:
            raise ValueError("initrd not specified")
        if utils.find_initrd(initrd):
            self._initrd = initrd
            return
        raise ValueError("initrd not found")

    @property
    def remote_grub_initrd(self):
        """
        TODO

        :return:
        """
        return self._remote_grub_initrd

    @remote_grub_initrd.setter
    def remote_grub_initrd(self, value: str):
        """
        TODO

        :param value:
        """
        if not isinstance(value, str):
            raise TypeError("remote_grub_initrd must be of type str")
        if not value:
            self._remote_grub_initrd = ""
            return
        parsed_url = grub.parse_grub_remote_file(value)
        if parsed_url is None:
            raise ValueError("Invalid URL for remote boot initrd: %s" % value)
        self._remote_grub_initrd = parsed_url

    @property
    def remote_boot_initrd(self):
        """
        TODO

        :return:
        """
        return self._remote_boot_initrd

    @remote_boot_initrd.setter
    def remote_boot_initrd(self, remote_boot_initrd: str):
        """
        URL to a remote initrd. If the bootloader supports this feature, it directly tries to retrieve the initrd and
        boot it. (grub supports tftp and http protocol and server must be an IP).
        """
        if not isinstance(remote_boot_initrd, str):
            raise TypeError("remote_boot_initrd must be of type str!")
        self.remote_grub_initrd = remote_boot_initrd
        self._remote_boot_initrd = remote_boot_initrd

    @property
    def source_repos(self):
        """
        TODO

        :return:
        """
        return self._source_repos

    @source_repos.setter
    def source_repos(self, repos):
        """
        A list of http:// URLs on the Cobbler server that point to yum configuration files that can be used to
        install core packages. Use by ``cobbler import`` only.

        :param repos: The list of URLs.
        """
        self._source_repos = repos

    @property
    def arch(self):
        """
        Return the architecture of the distribution

        :return: Return the current architecture.
        """
        return self._arch

    @arch.setter
    def arch(self, arch: Union[str, enums.Archs]):
        """
        The field is mainly relevant to PXE provisioning.

        Using an alternative distro type allows for dhcpd.conf templating to "do the right thing" with those
        systems -- this also relates to bootloader configuration files which have different syntax for different
        distro types (because of the bootloaders).

        This field is named "arch" because mainly on Linux, we only care about the architecture, though if (in the
        future) new provisioning types are added, an arch value might be something like "bsd_x86".

        :param arch: The architecture of the operating system distro.
        """
        self._arch = validate.validate_arch(arch)

    @property
    def supported_boot_loaders(self):
        """
        Some distributions, particularly on powerpc, can only be netbooted using specific bootloaders.

        :return: The bootloaders which are available for being set.
        """
        if len(self._supported_boot_loaders) == 0:
            self._supported_boot_loaders = utils.get_supported_distro_boot_loaders(self)
        return self._supported_boot_loaders

    @property
    def boot_loaders(self):
        """
        TODO

        :return: The bootloaders.
        """
        if self._boot_loaders == enums.VALUE_INHERITED:
            return self.supported_boot_loaders
        return self._boot_loaders

    @boot_loaders.setter
    def boot_loaders(self, boot_loaders: List[str]):
        """
        Set the bootloader for the distro.

        :param boot_loaders: The list with names of the bootloaders. Must be one of the supported ones.
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

    @property
    def redhat_management_key(self) -> str:
        """
        Get the redhat management key. This is probably only needed if you have spacewalk, uyuni or SUSE Manager
        running.

        :return: The key as a string.
        """
        return self._redhat_management_key

    @redhat_management_key.setter
    def redhat_management_key(self, management_key):
        """
        Set the redhat management key. This is probably only needed if you have spacewalk, uyuni or SUSE Manager
        running.

        :param management_key: The redhat management key.
        """
        if management_key is None:
            self._redhat_management_key = ""
        self._redhat_management_key = management_key
