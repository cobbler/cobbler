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

import os

from cobbler.items import item
from cobbler import utils
from cobbler.cexceptions import CX
from cobbler import grub

# this data structure is described in item.py
FIELDS = [
    # non-editable in UI (internal)
    ["ctime", 0, 0, "", False, "", 0, "float"],
    ["depth", 0, 0, "Depth", False, "", 0, "int"],
    ["mtime", 0, 0, "", False, "", 0, "float"],
    ["source_repos", [], 0, "Source Repos", False, "", 0, "list"],
    ["tree_build_time", 0, 0, "Tree Build Time", False, "", 0, "str"],
    ["uid", "", 0, "", False, "", 0, "str"],

    # editable in UI
    ["arch", 'x86_64', 0, "Architecture", True, "", utils.get_valid_archs(), "str"],
    ["autoinstall_meta", {}, 0, "Automatic Installation Template Metadata", True, "Ex: dog=fang agent=86", 0, "dict"],
    ["boot_files", {}, 0, "TFTP Boot Files", True, "Files copied into tftpboot beyond the kernel/initrd", 0, "list"],
    ["boot_loader", "<<inherit>>", 0, "Boot loader", True, "Network installation boot loader",
     utils.get_supported_system_boot_loaders(), "str"],
    ["breed", 'redhat', 0, "Breed", True, "What is the type of distribution?", utils.get_valid_breeds(), "str"],
    ["comment", "", 0, "Comment", True, "Free form text description", 0, "str"],
    ["fetchable_files", {}, 0, "Fetchable Files", True, "Templates for tftp or wget/curl", 0, "list"],
    ["initrd", None, 0, "Initrd", True, "Absolute path to kernel on filesystem", 0, "str"],
    ["kernel", None, 0, "Kernel", True, "Absolute path to kernel on filesystem", 0, "str"],
    ["remote_boot_initrd", None, 0, "Remote Boot Initrd", True, "URL the bootloader directly retrieves and boots from", 0, "str"],
    ["remote_boot_kernel", None, 0, "Remote Boot Kernel", True, "URL the bootloader directly retrieves and boots from", 0, "str"],
    ["kernel_options", {}, 0, "Kernel Options", True, "Ex: selinux=permissive", 0, "dict"],
    ["kernel_options_post", {}, 0, "Kernel Options (Post Install)", True, "Ex: clocksource=pit noapic", 0, "dict"],
    ["mgmt_classes", [], 0, "Management Classes", True, "Management classes for external config management", 0, "list"],
    ["name", "", 0, "Name", True, "Ex: Fedora-11-i386", 0, "str"],
    ["os_version", "virtio26", 0, "OS Version", True, "Needed for some virtualization optimizations",
     utils.get_valid_os_versions(), "str"],
    ["owners", "SETTINGS:default_ownership", 0, "Owners", True, "Owners list for authz_ownership (space delimited)", 0, "list"],
    ["redhat_management_key", "", "", "Redhat Management Key", True, "Registration key for RHN, Spacewalk, or Satellite", 0, "str"],
    ["template_files", {}, 0, "Template Files", True, "File mappings for built-in config management", 0, "dict"]
]


class Distro(item.Item):
    """
    A Cobbler distribution object
    """

    TYPE_NAME = "distro"
    COLLECTION_TYPE = "distro"

    def __init__(self, *args, **kwargs):
        """
        This creates a Distro object.

        :param args: Place for extra parameters in this distro object.
        :param kwargs: Place for extra parameters in this distro object.
        """
        super(Distro, self).__init__(*args, **kwargs)
        self.kernel_options = {}
        self.kernel_options_post = {}
        self.autoinstall_meta = {}
        self.source_repos = []
        self.fetchable_files = {}
        self.boot_files = {}
        self.template_files = {}
        self.remote_grub_kernel = ""
        self.remote_grub_initrd = ""

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
        _dict = self.to_dict()
        cloned = Distro(self.collection_mgr)
        cloned.from_dict(_dict)
        return cloned

    def get_fields(self):
        """
        Return the list of fields and their properties
        """
        return FIELDS

    def get_parent(self):
        """
        Distros don't have parent objects.
        """
        return None

    def check_if_valid(self):
        """
        Check if a distro object is valid. If invalid an exception is raised.
        """
        if self.name is None:
            raise CX("name is required")
        if self.kernel is None:
            raise CX("Error with distro %s - kernel is required" % (self.name))
        if self.initrd is None:
            raise CX("Error with distro %s - initrd is required" % (self.name))

        # self.remote_grub_kernel has to be set in set_remote_boot_kernel and here
        # in case the distro is read from json file (setters are not called).
        if self.remote_boot_kernel:
            self.remote_grub_kernel = grub.parse_grub_remote_file(self.remote_boot_kernel)
            if not self.remote_grub_kernel:
                raise CX("Invalid URL for remote boot kernel: %s" % self.remote_boot_kernel)
        if self.remote_boot_initrd:
            self.remote_grub_initrd = grub.parse_grub_remote_file(self.remote_boot_initrd)
            if not self.remote_grub_initrd:
                raise CX("Invalid URL for remote boot initrd: %s" % self.remote_boot_initrd)

        if utils.file_is_remote(self.kernel):
            if not utils.remote_file_exists(self.kernel):
                raise CX("Error with distro %s - kernel '%s' not found" % (self.name, self.kernel))
        elif not os.path.exists(self.kernel):
            raise CX("Error with distro %s - kernel '%s' not found" % (self.name, self.kernel))

        if utils.file_is_remote(self.initrd):
            if not utils.remote_file_exists(self.initrd):
                raise CX("Error with distro %s - initrd path '%s' not found" % (self.name, self.initrd))
        elif not os.path.exists(self.initrd):
            raise CX("Error with distro %s - initrd path '%s' not found" % (self.name, self.initrd))

    #
    # specific methods for item.Distro
    #

    def set_kernel(self, kernel):
        """
        Specifies a kernel. The kernel parameter is a full path, a filename in the configured kernel directory (set in
        /etc/cobbler.conf) or a directory path that would contain a selectable kernel. Kernel naming conventions are
        checked, see docs in the utils module for ``find_kernel``.

        :param kernel:
        :raises CX: If the kernel was not found
        """
        if kernel is None or kernel == "":
            raise CX("kernel not specified")
        if utils.find_kernel(kernel):
            self.kernel = kernel
            return
        raise CX("kernel not found: %s" % kernel)

    def set_remote_boot_kernel(self, remote_boot_kernel):
        """
        URL to a remote kernel. If the bootloader supports this feature,
        it directly tries to retrieve the kernel and boot it.
        (grub supports tftp and http protocol and server must be an IP).
        """
        if remote_boot_kernel:
            self.remote_grub_kernel = grub.parse_grub_remote_file(remote_boot_kernel)
            if not self.remote_grub_kernel:
                raise CX("Invalid URL for remote boot kernel: %s" % remote_boot_kernel)
            self.remote_boot_kernel = remote_boot_kernel
            return
        # Set to None or ""
        self.remote_grub_kernel = remote_boot_kernel
        self.remote_boot_kernel = remote_boot_kernel

    def set_tree_build_time(self, datestamp: float):
        """
        Sets the import time of the distro. If not imported, this field is not meaningful.

        :param datestamp: The datestamp to save the builddate. There is an attempt to convert it to a float, so please
                          make sure it is compatible to this.
        """
        self.tree_build_time = float(datestamp)

    def set_breed(self, breed):
        """
        Set the Operating system breed.

        :param breed: The new breed to set.
        """
        return utils.set_breed(self, breed)

    def set_os_version(self, os_version):
        """
        Set the Operating System Version.

        :param os_version: The new OS Version.
        """
        return utils.set_os_version(self, os_version)

    def set_initrd(self, initrd):
        """
        Specifies an initrd image. Path search works as in set_kernel. File must be named appropriately.

        :param initrd: The new path to the ``initrd``.
        """
        if initrd is None or initrd == "":
            raise CX("initrd not specified")
        if utils.find_initrd(initrd):
            self.initrd = initrd
            return
        raise CX("initrd not found")

    def set_remote_boot_initrd(self, remote_boot_initrd):
        """
        URL to a remote initrd. If the bootloader supports this feature,
        it directly tries to retrieve the initrd and boot it.
        (grub supports tftp and http protocol and server must be an IP).
        """
        if remote_boot_initrd:
            self.remote_grub_initrd = grub.parse_grub_remote_file(remote_boot_initrd)
            if not self.remote_grub_initrd:
                raise CX("Invalid URL for remote boot initrd: %s" % remote_boot_initrd)
            self.remote_boot_initrd = remote_boot_initrd
            return
        # Set to None or ""
        self.remote_grub_initrd = self.remote_boot_initrd = remote_boot_initrd

    def set_source_repos(self, repos):
        """
        A list of http:// URLs on the Cobbler server that point to yum configuration files that can be used to
        install core packages. Use by ``cobbler import`` only.

        :param repos: The list of URLs.
        """
        self.source_repos = repos

    def set_arch(self, arch):
        """
        The field is mainly relevant to PXE provisioning.

        Using an alternative distro type allows for dhcpd.conf templating to "do the right thing" with those
        systems -- this also relates to bootloader configuration files which have different syntax for different
        distro types (because of the bootloaders).

        This field is named "arch" because mainly on Linux, we only care about the architecture, though if (in the
        future) new provisioning types are added, an arch value might be something like "bsd_x86".

        :param arch: The architecture of the operating system distro.
        """
        return utils.set_arch(self, arch)

    def get_arch(self):
        """
        Return the architecture of the distribution

        :return: Return the current architecture.
        """
        return self.arch

    def set_supported_boot_loaders(self, supported_boot_loaders):
        """
        Some distributions, particularly on powerpc, can only be netbooted using specific bootloaders.

        :param supported_boot_loaders: The bootloaders which are available for being set.
        """
        if len(supported_boot_loaders) < 1:
            raise CX("No valid supported boot loaders specified for distro '%s'" % self.name)
        self.supported_boot_loaders = supported_boot_loaders
        self.boot_loader = supported_boot_loaders[0]

    def set_boot_loader(self, name):
        """
        Set the bootloader for the distro.

        :param name: The name of the bootloader. Must be one of the supported ones.
        """
        try:
            # If we have already loaded the supported boot loaders from
            # the signature, use that data
            supported_distro_boot_loaders = self.supported_boot_loaders
        except:
            # otherwise, refresh from the signatures / defaults
            self.supported_boot_loaders = utils.get_supported_distro_boot_loaders(self)
            supported_distro_boot_loaders = self.supported_boot_loaders
        if name not in supported_distro_boot_loaders:
            raise CX("Invalid boot loader name: %s. Supported boot loaders are: %s"
                     % (name, ' '.join(supported_distro_boot_loaders)))
        self.boot_loader = name

    def set_redhat_management_key(self, management_key):
        """
        Set the redhat management key. This is probably only needed if you have spacewalk, uyuni or SUSE Manager
        running.

        :param management_key: The redhat management key.
        """
        if management_key is None:
            self.redhat_management_key = ""
        self.redhat_management_key = management_key

    def get_redhat_management_key(self):
        """
        Get the redhat management key. This is probably only needed if you have spacewalk, uyuni or SUSE Manager
        running.

        :return: The key as a string.
        :rtype: str
        """
        return self.redhat_management_key
