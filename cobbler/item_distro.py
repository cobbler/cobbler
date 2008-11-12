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

class Distro(item.Item):

    TYPE_NAME = _("distro")
    COLLECTION_TYPE = "distro"

    def clear(self,is_subobject=False):
        """
        Reset this object.
        """
        self.name                   = None
        self.owners                 = self.settings.default_ownership
        self.kernel                 = None
        self.initrd                 = None
        self.kernel_options         = {}
        self.kernel_options_post    = {}
        self.ks_meta                = {}
        self.arch                   = 'i386'
        self.breed                  = 'redhat'
        self.os_version             = ''
        self.source_repos           = []
        self.mgmt_classes           = []
        self.depth                  = 0
        self.template_files         = {}
	self.comment                = ""
        self.tree_build_time        = 0

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
        self.parent                 = self.load_item(seed_data,'parent')
        self.name                   = self.load_item(seed_data,'name')
        self.owners                 = self.load_item(seed_data,'owners',self.settings.default_ownership)
        self.kernel                 = self.load_item(seed_data,'kernel')
        self.initrd                 = self.load_item(seed_data,'initrd')
        self.kernel_options         = self.load_item(seed_data,'kernel_options')
        self.kernel_options_post    = self.load_item(seed_data,'kernel_options_post')
        self.ks_meta                = self.load_item(seed_data,'ks_meta')
        self.arch                   = self.load_item(seed_data,'arch','i386')
        self.breed                  = self.load_item(seed_data,'breed','redhat')
        self.os_version             = self.load_item(seed_data,'os_version','')
        self.source_repos           = self.load_item(seed_data,'source_repos',[])
        self.depth                  = self.load_item(seed_data,'depth',0)
        self.mgmt_classes           = self.load_item(seed_data,'mgmt_classes',[])
        self.template_files         = self.load_item(seed_data,'template_files',{})
	self.comment                = self.load_item(seed_data,'comment')

        # backwards compatibility enforcement
        self.set_arch(self.arch)
        if self.kernel_options != "<<inherit>>" and type(self.kernel_options) != dict:
            self.set_kernel_options(self.kernel_options)
        if self.kernel_options_post != "<<inherit>>" and type(self.kernel_options_post) != dict:
            self.set_kernel_options_post(self.kernel_options_post)
        if self.ks_meta != "<<inherit>>" and type(self.ks_meta) != dict:
            self.set_ksmeta(self.ks_meta)
        
        self.set_mgmt_classes(self.mgmt_classes)
        self.set_template_files(self.template_files)
        self.set_owners(self.owners)

        self.tree_build_time = self.load_item(seed_data, 'tree_build_time', -1)
        self.ctime = self.load_item(seed_data, 'ctime', 0)
        self.mtime = self.load_item(seed_data, 'mtime', 0)

        self.set_tree_build_time(self.tree_build_time)

        return self

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
        raise CX(_("kernel not found"))

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

    def is_valid(self):
        """
	A distro requires that the kernel and initrd be set.  All
	other variables are optional.
	"""
        # NOTE: this code does not support inheritable distros at this time.
        # this is by design because inheritable distros do not make sense.
        if self.name is None:
            raise CX(_("name is required"))
        if self.kernel is None:
            raise CX(_("kernel is required"))
        if self.initrd is None:
            raise CX(_("initrd is required"))
        return True

    def to_datastruct(self):
        """
        Return a serializable datastructure representation of this object.
        """
        return {
            'name'                   : self.name,
            'kernel'                 : self.kernel,
            'initrd'                 : self.initrd,
            'kernel_options'         : self.kernel_options,
            'kernel_options_post'    : self.kernel_options_post,
            'ks_meta'                : self.ks_meta,
            'mgmt_classes'           : self.mgmt_classes,
            'template_files'         : self.template_files,
            'arch'                   : self.arch,
            'breed'                  : self.breed,
            'os_version'             : self.os_version,
            'source_repos'           : self.source_repos,
            'parent'                 : self.parent,
            'depth'                  : self.depth,
            'owners'                 : self.owners,
            'comment'                : self.comment,
            'tree_build_time'        : self.tree_build_time,
            'ctime'                  : self.ctime,
            'mtime'                  : self.mtime,
        }

    def printable(self):
        """
	Human-readable representation.
	"""
        kstr = utils.find_kernel(self.kernel)
        istr = utils.find_initrd(self.initrd)
        buf =       _("distro               : %s\n") % self.name
        buf = buf + _("architecture         : %s\n") % self.arch
        buf = buf + _("breed                : %s\n") % self.breed
        buf = buf + _("created              : %s\n") % time.ctime(self.ctime)
        buf = buf + _("comment              : %s\n") % self.comment
        buf = buf + _("initrd               : %s\n") % istr
        buf = buf + _("kernel               : %s\n") % kstr
        buf = buf + _("kernel options       : %s\n") % self.kernel_options
        buf = buf + _("ks metadata          : %s\n") % self.ks_meta
        if self.tree_build_time != -1:
            buf = buf + _("tree build time      : %s\n") % time.ctime(self.tree_build_time)
        else:
            buf = buf + _("tree build time      : %s\n") % "N/A"
        buf = buf + _("modified             : %s\n") % time.ctime(self.mtime)
        buf = buf + _("mgmt classes         : %s\n") % self.mgmt_classes 
        buf = buf + _("os version           : %s\n") % self.os_version
        buf = buf + _("owners               : %s\n") % self.owners
        buf = buf + _("post kernel options  : %s\n") % self.kernel_options_post
        buf = buf + _("template files       : %s\n") % self.template_files
        return buf

    def remote_methods(self):
        return {
            'name'          : self.set_name,
            'kernel'        : self.set_kernel,
            'initrd'        : self.set_initrd,
            'kopts'         : self.set_kernel_options,
            'kopts-post'    : self.set_kernel_options_post,
            'kopts_post'    : self.set_kernel_options_post,            
            'arch'          : self.set_arch,
            'ksmeta'        : self.set_ksmeta,
            'breed'         : self.set_breed,
            'os-version'    : self.set_os_version,
            'os_version'    : self.set_os_version,            
            'owners'        : self.set_owners,
            'mgmt-classes'  : self.set_mgmt_classes,
            'mgmt_classes'  : self.set_mgmt_classes,            
            'template-files': self.set_template_files,
            'template_files': self.set_template_files,            
            'comment'       : self.set_comment
        }

