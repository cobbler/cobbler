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
from typing import List

from cobbler import autoinstall_manager
from cobbler.items import item
from cobbler import utils
from cobbler.cexceptions import CX


# this data structure is described in item.py
FIELDS = [
    # non-editable in UI (internal)
    ['ctime', 0, 0, "", False, "", 0, "float"],
    ['depth', 0, 0, "", False, "", 0, "int"],
    ['mtime', 0, 0, "", False, "", 0, "float"],
    ['parent', '', 0, "", False, "", 0, "str"],
    ['uid', "", 0, "", False, "", 0, "str"],

    # editable in UI
    ['arch', 'x86_64', 0, "Architecture", True, "", utils.get_valid_archs(), "str"],
    ['autoinstall', '', 0, "Automatic installation file", True, "Path to autoinst/answer file template", 0, "str"],
    ['breed', 'redhat', 0, "Breed", True, "", utils.get_valid_breeds(), "str"],
    ['comment', '', 0, "Comment", True, "Free form text description", 0, "str"],
    ['file', '', 0, "File", True, "Path to local file or nfs://user@host:path", 0, "str"],
    ['image_type', "iso", 0, "Image Type", True, "", ["iso", "direct", "memdisk", "virt-image"], "str"],
    ['name', '', 0, "Name", True, "", 0, "str"],
    ['network_count', 1, 0, "Virt NICs", True, "", 0, "int"],
    ['os_version', '', 0, "OS Version", True, "ex: rhel4", utils.get_valid_os_versions(), "str"],
    ['owners', "SETTINGS:default_ownership", 0, "Owners", True, "Owners list for authz_ownership (space delimited)", [], "list"],
    ['virt_auto_boot', "SETTINGS:virt_auto_boot", 0, "Virt Auto Boot", True, "Auto boot this VM?", 0, "bool"],
    ['virt_bridge', "SETTINGS:default_virt_bridge", 0, "Virt Bridge", True, "", 0, "str"],
    ['virt_cpus', 1, 0, "Virt CPUs", True, "", 0, "int"],
    ["virt_disk_driver", "SETTINGS:default_virt_disk_driver", 0, "Virt Disk Driver Type", True, "The on-disk format for the virtualization disk", "raw", "str"],
    ['virt_file_size', "SETTINGS:default_virt_file_size", 0, "Virt File Size (GB)", True, "", 0, "float"],
    ['virt_path', '', 0, "Virt Path", True, "Ex: /directory or VolGroup00", 0, "str"],
    ['virt_ram', "SETTINGS:default_virt_ram", 0, "Virt RAM (MB)", True, "", 0, "int"],
    ['virt_type', "SETTINGS:default_virt_type", 0, "Virt Type", True, "", ["xenpv", "xenfv", "qemu", "kvm", "vmware"], "str"],
]


class Image(item.Item):
    """
    A Cobbler Image.  Tracks a virtual or physical image, as opposed to a answer
    file (autoinst) led installation.
    """

    TYPE_NAME = "image"
    COLLECTION_TYPE = "image"

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
        cloned = Image(self.collection_mgr)
        cloned.from_dict(_dict)
        return cloned

    def get_fields(self):
        """
        Return all fields which this class has with its current values.

        :return: This is a list with lists.
        """
        return FIELDS

    def get_parent(self):
        """
        Images have no parent object.
        """
        return None

    #
    # specific methods for item.Image
    #

    def set_arch(self, arch):
        """
        The field is mainly relevant to PXE provisioning.
        See comments for set_arch in item_distro.py, this works the same.

        :param arch: The new architecture to set.
        """
        return utils.set_arch(self, arch)

    def set_autoinstall(self, autoinstall):
        """
        Set the automatic installation file path, this must be a local file.

        It may not make sense for images to have automatic installation templates.
        It really doesn't. However if the image type is 'iso' koan can create a virtual
        floppy and shove an answer file on it, to script an installation.  This may
        not be a automatic installation template per se, it might be a Windows answer
        file (SIF) etc.

        :param autoinstall: local automatic installation template file path
        :type autoinstall: str
        """

        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(self.collection_mgr)
        self.autoinstall = autoinstall_mgr.validate_autoinstall_template_file_path(autoinstall)

    def set_file(self, filename):
        """
        Stores the image location. This should be accessible on all nodes that need to access it.

        Format: can be one of the following:
        * username:password@hostname:/path/to/the/filename.ext
        * username@hostname:/path/to/the/filename.ext
        * hostname:/path/to/the/filename.ext
        * /path/to/the/filename.ext

        :param filename: The location where the image is stored.
        """
        uri = ""
        auth = hostname = path = ""
        # validate file location format
        if filename.find("://") != -1:
            raise CX("Invalid image file path location, it should not contain a protocol")
        uri = filename

        if filename.find("@") != -1:
            auth, filename = filename.split("@")
        # extract the hostname
        # 1. if we have a colon, then everything before it is a hostname
        # 2. if we don't have a colon, there is no hostname
        if filename.find(":") != -1:
            hostname, filename = filename.split(":")
        elif filename[0] != '/':
            raise CX("invalid file: %s" % filename)
        # raise an exception if we don't have a valid path
        if len(filename) > 0 and filename[0] != '/':
            raise CX("file contains an invalid path: %s" % filename)
        if filename.find("/") != -1:
            path, filename = filename.rsplit("/", 1)

        if len(filename) == 0:
            raise CX("missing filename")
        if len(auth) > 0 and len(hostname) == 0:
            raise CX("a hostname must be specified with authentication details")

        self.file = uri

    def set_os_version(self, os_version):
        """
        Set the operating system version with this setter.

        :param os_version: This must be a valid OS-Version.
        """
        return utils.set_os_version(self, os_version)

    def set_breed(self, breed):
        """
        Set the operating system breed with this setter.

        :param breed: The breed of the operating system which is available in the image.
        """
        return utils.set_breed(self, breed)

    def set_image_type(self, image_type):
        """
        Indicates what type of image this is.
        direct     = something like "memdisk", physical only
        iso        = a bootable ISO that pxe's or can be used for virt installs, virtual only
        virt-clone = a cloned virtual disk (FIXME: not yet supported), virtual only
        memdisk    = hdd image (physical only)

        :param image_type: One of the four options from above.
        """
        if image_type not in self.get_valid_image_types():
            raise CX("image type must be on of the following: %s" % ", ".join(self.get_valid_image_types()))
        self.image_type = image_type

    def set_virt_cpus(self, num):
        """
        Setter for the number of virtual cpus.

        :param num: The number of virtual cpu cores.
        """
        return utils.set_virt_cpus(self, num)

    def set_network_count(self, num: int):
        """
        Setter for the number of networks.

        :param num: If None or emtpy will be set to one. Otherwise will be cast to int and then set.
        """
        if num is None or num == "":
            num = 1
        try:
            self.network_count = int(num)
        except:
            raise CX("invalid network count (%s)" % num)

    def set_virt_auto_boot(self, num):
        """
        Setter for the virtual automatic boot option.

        :param num: May be "0" (disabled) or "1" (enabled)
        """
        return utils.set_virt_auto_boot(self, num)

    def set_virt_file_size(self, num):
        """
        Setter for the virtual file size of the image.

        :param num: Is a non-negative integer (0 means default). Can also be a comma seperated list -- for usage with
                    multiple disks
        """
        return utils.set_virt_file_size(self, num)

    def set_virt_disk_driver(self, driver):
        """
        Setter for the virtual disk driver.

        :param driver: The virtual disk driver which will be set.
        """
        return utils.set_virt_disk_driver(self, driver)

    def set_virt_ram(self, num):
        """
        Setter for the amount of virtual RAM the machine will have.

        :param num: 0 tells Koan to just choose a reasonable default.
        """
        return utils.set_virt_ram(self, num)

    def set_virt_type(self, vtype: str):
        """
        Setter for the virtual type

        :param vtype: May be one of "qemu", "kvm", "xenpv", "xenfv", "vmware", "vmwarew", "openvz" or "auto".
        """
        return utils.set_virt_type(self, vtype)

    def set_virt_bridge(self, vbridge):
        """
        Setter for the virtual bridge which is used.

        :param vbridge: The name of the virtual bridge to use.
        """
        return utils.set_virt_bridge(self, vbridge)

    def set_virt_path(self, path):
        """
        Setter for the virtual path which is used.

        :param path: The path to where the virtual image is stored.
        """
        return utils.set_virt_path(self, path)

    def get_valid_image_types(self) -> List[str]:
        """
        Get all valid image types.

        :return: A list currently with the values: "direct", "iso", "memdisk", "virt-clone"
        """
        return ["direct", "iso", "memdisk", "virt-clone"]
