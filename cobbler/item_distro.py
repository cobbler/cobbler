"""
A cobbler distribution.  A distribution is a kernel, and initrd, and potentially
some kernel options.

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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


import utils
import item
import weakref
import os
import codes
import time
from cexceptions import *

from utils import _

# name | default | subobject default | tooltip | editable?

FIELDS = [
   [ "name",                     None                         ,0, "Name"                                , True    ],
   [ "uid",                      ""                           ,0, ""                                    , False        ],
   [ "owners",                   "SETTINGS:default_ownership" ,0, "Owners list for authz_ownership"     , True  ],
   [ "kernel",                   None                         ,0, "Path to kernel file"                 , True ],
   [ "initrd",                   None                         ,0, "Path to initrd file"                 , True ],
   [ "kernel_options",           {}                           ,0, "List of install time kernel options" , True ],
   [ "kernel_options_post",      {}                           ,0, "List of post install kernel options" , True  ],
   [ "ks_meta",                  {}                           ,0, "Kickstart templating variables"      , True],
   [ "arch",                     'i386'                       ,0, "Architecture"                        , True],
   [ "breed",                    'redhat'                     ,0, "Breed"                               , True],
   [ "os_version",               ''                           ,0, "OS Version"                          , True],
   [ "source_repos",             []                           ,0, "Source Repos"                        , False],
   [ "mgmt_classes",             []                           ,0, "Management classes"                  , True],
   [ "depth",                    0                            ,0, ""                                   , False],
   [ "template_files",           {}                           ,0, "Template files"                      , True],
   [ "comment",                  ""                           ,0, "Free form text description"          , True],
   [ "tree_build_time",          0                            ,0, ""                                    , False ],
   [ "redhat_management_key",    "<<inherit>>"                ,0, "Registration key if needed"          , True],
   [ "redhat_management_server", "<<inherit>>"                ,0, "Management server if needed"         , True]
]

class Distro(item.Item):

    TYPE_NAME = _("distro")
    COLLECTION_TYPE = "distro"

    def clear(self,is_subobject=False):
        """
        Reset this object.
        """
        utils.clear_from_fields(self,FIELDS,is_subobject=is_subobject)

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Distro(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def get_parent(self):
        """
        Return object next highest up the tree.
        NOTE: conceptually there is no need for subdistros
        """
        return None

    def from_datastruct(self,seed_data):
        """
        Modify this object to take on values in seed_data
        """
        return utils.from_datastruct_from_fields(self,seed_data,FIELDS)

    def set_kernel(self,kernel):
        """
	Specifies a kernel.  The kernel parameter is a full path, a filename
	in the configured kernel directory (set in /etc/cobbler.conf) or a
	directory path that would contain a selectable kernel.  Kernel
	naming conventions are checked, see docs in the utils module
	for find_kernel.
	"""
        if utils.find_kernel(kernel):
            self.kernel = kernel
            return True
        raise CX("kernel not found: %s" % kernel)

    def set_tree_build_time(self, datestamp):
        """
        Sets the import time of the distro, for use by action_import.py.
        If not imported, this field is not meaningful.
        """
        self.tree_build_time = float(datestamp)
        return True

    def set_breed(self, breed):
        return utils.set_breed(self,breed)

    def set_os_version(self, os_version):
        return utils.set_os_version(self,os_version)

    def set_initrd(self,initrd):
        """
	Specifies an initrd image.  Path search works as in set_kernel.
	File must be named appropriately.
	"""
        if utils.find_initrd(initrd):
            self.initrd = initrd
            return True
        raise CX(_("initrd not found"))

    def set_redhat_management_key(self,key):
        return utils.set_redhat_management_key(self,key)

    def set_redhat_management_server(self,server):
        return utils.set_redhat_management_server(self,server)
 
    def set_source_repos(self, repos):
        """
        A list of http:// URLs on the cobbler server that point to
        yum configuration files that can be used to
        install core packages.  Use by cobbler import only.
        """
        self.source_repos = repos

    def set_arch(self,arch):
        """
        The field is mainly relevant to PXE provisioning.

        Should someone have Itanium machines on a network, having
        syslinux (pxelinux.0) be the only option in the config file causes
        problems.

        Using an alternative distro type allows for dhcpd.conf templating
        to "do the right thing" with those systems -- this also relates to
        bootloader configuration files which have different syntax for different
        distro types (because of the bootloaders).

        This field is named "arch" because mainly on Linux, we only care about
        the architecture, though if (in the future) new provisioning types
        are added, an arch value might be something like "bsd_x86".

        Update: (7/2008) this is now used to build fake PXE trees for s390x also
        """
        return utils.set_arch(self,arch)

    def to_datastruct(self):
        return utils.to_datastruct_from_fields(self,FIELDS)

    def printable(self):
        return utils.printable_from_fields(self,FIELDS)

    def remote_methods(self):
        return utils.get_remote_methods_from_fields(self,FIELDS)

