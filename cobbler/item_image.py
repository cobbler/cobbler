"""
A Cobbler Image.  Tracks a virtual or physical image, as opposed to a answer
file (kickstart) led installation.

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
import time
from cexceptions import *

from utils import _

class Image(item.Item):

    TYPE_NAME = _("image")
    COLLECTION_TYPE = "image"
 
    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Image(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def clear(self,is_subobject=False):
        """
        Reset this object.
        """
        self.name            = ''
        self.arch            = 'i386'
        self.file            = ''
        self.parent          = ''
        self.depth           = 0
        self.virt_ram        = self.settings.default_virt_ram
        self.virt_file_size  = self.settings.default_virt_file_size
        self.virt_path       = ''
        self.virt_type       = self.settings.default_virt_type
        self.virt_cpus       = 1
        self.network_count   = 1
        self.virt_bridge     = self.settings.default_virt_bridge
        self.owners          = self.settings.default_ownership
        self.image_type      = "iso" # direct, iso, memdisk, virt-clone
        self.breed           = 'redhat'
        self.os_version      = ''
        self.comment         = ''
        self.ctime           = 0
        self.mtime           = 0

    def from_datastruct(self,seed_data):
        """
        Load this object's properties based on seed_data
        """

        self.name            = self.load_item(seed_data,'name','')
        self.parent          = self.load_item(seed_data,'parent','')
        self.file            = self.load_item(seed_data,'file','')
        self.depth           = self.load_item(seed_data,'depth',0)
        self.owners          = self.load_item(seed_data,'owners',self.settings.default_ownership)

        self.virt_ram        = self.load_item(seed_data, 'virt_ram', self.settings.default_virt_ram)
        self.virt_file_size  = self.load_item(seed_data, 'virt_file_size', self.settings.default_virt_file_size)
        self.virt_path       = self.load_item(seed_data, 'virt_path')
        self.virt_type       = self.load_item(seed_data, 'virt_type', self.settings.default_virt_type)
        self.virt_cpus       = self.load_item(seed_data, 'virt_cpus')
        self.network_count   = self.load_item(seed_data, 'network_count')
        self.virt_bridge     = self.load_item(seed_data, 'virt_bridge')
        self.arch            = self.load_item(seed_data,'arch','i386')

        self.image_type      = self.load_item(seed_data, 'image_type', 'iso')

        self.breed           = self.load_item(seed_data, 'breed', 'redhat')
        self.os_version      = self.load_item(seed_data, 'os_version', '')

        self.comment         = self.load_item(seed_data, 'comment', '')

        self.set_owners(self.owners)
        self.set_arch(self.arch)

        self.ctime           = self.load_item(seed_data, 'ctime', 0)
        self.mtime           = self.load_item(seed_data, 'mtime', 0)

        return self

    def set_arch(self,arch):
        """
        The field is mainly relevant to PXE provisioning.
        see comments for set_arch in item_distro.py, this works the same.
        """
        return utils.set_arch(self,arch)

    def set_file(self,filename):
        """
        Stores the image location.  This should be accessible on all nodes
        that need to access it.  Format: either /mnt/commonpath/foo.iso or 
        nfs://host/path/foo.iso
        """
        # FIXME: this should accept NFS paths or filesystem paths
        self.file = filename
        return True

    def set_os_version(self,os_version):
        return utils.set_os_version(self,os_version)

    def set_breed(self,breed):
        return utils.set_breed(self,breed)

    def set_image_type(self,image_type):
        """
        Indicates what type of image this is.
        direct     = something like "memdisk", physical only
        iso        = a bootable ISO that pxe's or can be used for virt installs, virtual only
        virt-clone = a cloned virtual disk (FIXME: not yet supported), virtual only
        memdisk    = hdd image (physical only)
        """
        if not image_type in [ "direct", "iso", "memdisk", "virt-clone" ]:
           raise CX(_("image type must be 'direct', 'iso', or 'virt-clone'"))
        self.image_type = image_type
        return True

    def set_virt_cpus(self,num):
        return utils.set_virt_cpus(self,num)
        
    def set_network_count(self, num):
        self.network_count = num
        return True

    def set_virt_file_size(self,num):
        return utils.set_virt_file_size(self,num)

    def set_virt_ram(self,num):
        return utils.set_virt_ram(self,num)

    def set_virt_type(self,vtype):
        return utils.set_virt_type(self,vtype)

    def set_virt_bridge(self,vbridge):
        self.virt_bridge = vbridge
        return True

    def set_virt_path(self,path):
        return utils.set_virt_path(self,path)

    def get_parent(self):
        """
        Return object next highest up the tree.
        """
        return None  # no parent

    def is_valid(self):
        if self.file is None or self.file == '':
            raise CX(_("image has no file specified"))
        if self.name is None or self.name == '':
            raise CX(_("image has no name specified"))
        return True

    # FIXME: add virt parameters here as needed

    def to_datastruct(self):
        """
        Return hash representation for the serializer
        """
        return {
            'name'             : self.name,
            'arch'             : self.arch,
            'image_type'       : self.image_type,
            'file'             : self.file,
            'depth'            : 0,
            'parent'           : '',
            'owners'           : self.owners,
            'virt_ram'         : self.virt_ram,
            'virt_path'        : self.virt_path,
            'virt_type'        : self.virt_type,
            'virt_cpus'        : self.virt_cpus,
            'network_count'    : self.network_count,
            'virt_bridge'      : self.virt_bridge,
            'virt_file_size'   : self.virt_file_size,
            'breed'            : self.breed,
            'os_version'       : self.os_version,
            'comment'          : self.comment,
            'ctime'            : self.ctime,
            'mtime'            : self.mtime
        }

    def printable(self):
        """
        A human readable representaton
        """
        buf =       _("image           : %s\n") % self.name
        buf = buf + _("arch            : %s\n") % self.arch
        buf = buf + _("breed           : %s\n") % self.breed
        buf = buf + _("comment         : %s\n") % self.comment
        buf = buf + _("created         : %s\n") % time.ctime(self.ctime)
        buf = buf + _("file            : %s\n") % self.file
        buf = buf + _("image type      : %s\n") % self.image_type
        buf = buf + _("modified        : %s\n") % time.ctime(self.mtime)
        buf = buf + _("os version      : %s\n") % self.os_version
        buf = buf + _("owners          : %s\n") % self.owners
        buf = buf + _("virt bridge     : %s\n") % self.virt_bridge
        buf = buf + _("virt cpus       : %s\n") % self.virt_cpus
        buf = buf + _("network count   : %s\n") % self.network_count
        buf = buf + _("virt file size  : %s\n") % self.virt_file_size
        buf = buf + _("virt path       : %s\n") % self.virt_path
        buf = buf + _("virt ram        : %s\n") % self.virt_ram
        buf = buf + _("virt type       : %s\n") % self.virt_type
        return buf

  
    def remote_methods(self):
        return {           
            'name'            :  self.set_name,
            'image-type'      :  self.set_image_type,
            'image_type'      :  self.set_image_type,            
            'breed'           :  self.set_breed,
            'os-version'      :  self.set_os_version,
            'os_version'      :  self.set_os_version,            
            'arch'            :  self.set_arch,
            'file'            :  self.set_file,
            'owners'          :  self.set_owners,
            'virt-cpus'       :  self.set_virt_cpus,
            'virt_cpus'       :  self.set_virt_cpus,            
            'network-count'   :  self.set_network_count,
            'network_count'   :  self.set_network_count,            
            'virt-file-size'  :  self.set_virt_file_size,
            'virt_file_size'  :  self.set_virt_file_size,            
            'virt-bridge'     :  self.set_virt_bridge,
            'virt_bridge'     :  self.set_virt_bridge,            
            'virt-path'       :  self.set_virt_path,
            'virt_path'       :  self.set_virt_path,            
            'virt-ram'        :  self.set_virt_ram,
            'virt_ram'        :  self.set_virt_ram,            
            'virt-type'       :  self.set_virt_type,
            'virt_type'       :  self.set_virt_type,            
            'comment'         :  self.set_comment
        }

