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

import string

from cobbler import item
from cobbler import utils
from cobbler import validate
from cobbler.cexceptions import CX
from cobbler.utils import _


# this datastructure is described in great detail in item_distro.py -- read the comments there.
FIELDS = [
    ['name', '', 0, "Name", True, "", 0, "str"],
    ['arch', 'x86_64', 0, "Architecture", True, "", utils.get_valid_archs(), "str"],
    ['breed', 'redhat', 0, "Breed", True, "", utils.get_valid_breeds(), "str"],
    ['comment', '', 0, "Comment", True, "Free form text description", 0, "str"],
    ['ctime', 0, 0, "", False, "", 0, "float"],
    ['mtime', 0, 0, "", False, "", 0, "float"],
    ['file', '', 0, "File", True, "Path to local file or nfs://user@host:path", 0, "str"],
    ['depth', 0, 0, "", False, "", 0, "int"],
    ['image_type', "iso", 0, "Image Type", True, "", ["iso", "direct", "memdisk", "virt-image"], "str"],
    ['network_count', 1, 0, "Virt NICs", True, "", 0, "int"],
    ['os_version', '', 0, "OS Version", True, "ex: rhel4", utils.get_valid_os_versions(), "str"],
    ['owners', "SETTINGS:default_ownership", 0, "Owners", True, "Owners list for authz_ownership (space delimited)", [], "list"],
    ['parent', '', 0, "", False, "", 0, "str"],
    ['autoinstall', '', 0, "Automatic installation file", True, "Path to autoinst/answer file template", 0, "str"],
    ['virt_auto_boot', "SETTINGS:virt_auto_boot", 0, "Virt Auto Boot", True, "Auto boot this VM?", 0, "bool"],
    ['virt_bridge', "SETTINGS:default_virt_bridge", 0, "Virt Bridge", True, "", 0, "str"],
    ['virt_cpus', 1, 0, "Virt CPUs", True, "", 0, "int"],
    ['virt_file_size', "SETTINGS:default_virt_file_size", 0, "Virt File Size (GB)", True, "", 0, "float"],
    ["virt_disk_driver", "SETTINGS:default_virt_disk_driver", 0, "Virt Disk Driver Type", True, "The on-disk format for the virtualization disk", "raw", "str"],
    ['virt_path', '', 0, "Virt Path", True, "Ex: /directory or VolGroup00", 0, "str"],
    ['virt_ram', "SETTINGS:default_virt_ram", 0, "Virt RAM (MB)", True, "", 0, "int"],
    ['virt_type', "SETTINGS:default_virt_type", 0, "Virt Type", True, "", ["xenpv", "xenfv", "qemu", "kvm", "vmware"], "str"],
    ['uid', "", 0, "", False, "", 0, "str"]
]


class Image(item.Item):
    """
    A Cobbler Image.  Tracks a virtual or physical image, as opposed to a answer
    file (autoinst) led installation.
    """

    TYPE_NAME = _("image")
    COLLECTION_TYPE = "image"

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):

        _dict = self.to_dict()
        cloned = Image(self.collection_mgr)
        cloned.from_dict(_dict)
        return cloned


    def get_fields(self):
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
        see comments for set_arch in item_distro.py, this works the same.
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

        @param: str local automatic installation file path
        @returns: True or CX
        """
        self.autoinstall = validate.autoinstall_template_file_path(autoinstall)


    def set_file(self, filename):
        """
        Stores the image location.  This should be accessible on all nodes
        that need to access it.  Format: can be one of the following:
        * username:password@hostname:/path/to/the/filename.ext
        * username@hostname:/path/to/the/filename.ext
        * hostname:/path/to/the/filename.ext
        * /path/to/the/filename.ext
        """
        uri = ""
        scheme = auth = hostname = path = ""
        # we'll discard the protocol if it's supplied, for legacy support
        if filename.find("://") != -1:
            scheme, uri = filename.split("://")
            filename = uri
        else:
            uri = filename

        if filename.find("@") != -1:
            auth, filename = filename.split("@")
        # extract the hostname
        # 1. if we have a colon, then everything before it is a hostname
        # 2. if we don't have a colon, then check if we had a scheme; if
        #    we did, then grab all before the first forward slash as the
        #    hostname; otherwise, we've got a bad file
        if filename.find(":") != -1:
            hostname, filename = filename.split(":")
        elif filename[0] != '/':
            if len(scheme) > 0:
                index = filename.find("/")
                hostname = filename[:index]
                filename = filename[index:]
            else:
                raise CX(_("invalid file: %s" % filename))
        # raise an exception if we don't have a valid path
        if len(filename) > 0 and filename[0] != '/':
            raise CX(_("file contains an invalid path: %s" % filename))
        if filename.find("/") != -1:
            path, filename = filename.rsplit("/", 1)

        if len(filename) == 0:
            raise CX(_("missing filename"))
        if len(auth) > 0 and len(hostname) == 0:
            raise CX(_("a hostname must be specified with authentication details"))

        self.file = uri


    def set_os_version(self, os_version):
        return utils.set_os_version(self, os_version)


    def set_breed(self, breed):
        return utils.set_breed(self, breed)


    def set_image_type(self, image_type):
        """
        Indicates what type of image this is.
        direct     = something like "memdisk", physical only
        iso        = a bootable ISO that pxe's or can be used for virt installs, virtual only
        virt-clone = a cloned virtual disk (FIXME: not yet supported), virtual only
        memdisk    = hdd image (physical only)
        """
        if image_type not in self.get_valid_image_types():
            raise CX(_("image type must be on of the following: %s") % string.join(self.get_valid_image_types(), ", "))
        self.image_type = image_type


    def set_virt_cpus(self, num):
        return utils.set_virt_cpus(self, num)


    def set_network_count(self, num):
        if num is None or num == "":
            num = 1
        try:
            self.network_count = int(num)
        except:
            raise CX("invalid network count (%s)" % num)


    def set_virt_auto_boot(self, num):
        return utils.set_virt_auto_boot(self, num)


    def set_virt_file_size(self, num):
        return utils.set_virt_file_size(self, num)


    def set_virt_disk_driver(self, driver):
        return utils.set_virt_disk_driver(self, driver)


    def set_virt_ram(self, num):
        return utils.set_virt_ram(self, num)


    def set_virt_type(self, vtype):
        return utils.set_virt_type(self, vtype)


    def set_virt_bridge(self, vbridge):
        return utils.set_virt_bridge(self, vbridge)


    def set_virt_path(self, path):
        return utils.set_virt_path(self, path)


    def get_valid_image_types(self):
        return ["direct", "iso", "memdisk", "virt-clone"]

# EOF
