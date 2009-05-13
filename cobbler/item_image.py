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

FIELDS = [
   [ 'name'            , '' ],
   [ 'uid'             , "" ],
   [ 'arch'            , 'i386' ],
   [ 'file'            , '' ],
   [ 'parent'          , '' ],
   [ 'depth'           , 0  ],
   [ 'virt_auto_boot'  , "SETTINGS:virt_auto_boot"   ],
   [ 'virt_ram'        , "SETTINGS:default_virt_ram" ],
   [ 'virt_file_size'  , "SETTINGS:default_virt_file_size" ],
   [ 'virt_path'       , '' ],
   [ 'virt_type'       , "SETTINGS:default_virt_type" ],
   [ 'virt_cpus'       , 1  ],
   [ 'network_count'   , 1  ],
   [ 'virt_bridge'     , "SETTINGS:default_virt_bridge" ],
   [ 'owners'          , "SETTINGS:default_ownership" ],
   [ 'image_type'      , "iso" ],
   [ 'breed'           , 'redhat' ],
   [ 'os_version'      , '' ],
   [ 'comment'         , '' ],
   [ 'ctime'           , 0  ],
   [ 'mtime'           , 0  ],
   [ 'kickstart'       , '' ]
]

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
        utils.clear_from_fields(self,FIELDS)
 
    def from_datastruct(self,seed_data):
        """
        Load this object's properties based on seed_data
        """
        return utils.from_datastruct_from_fields(self,seed_data,FIELDS)

    def set_arch(self,arch):
        """
        The field is mainly relevant to PXE provisioning.
        see comments for set_arch in item_distro.py, this works the same.
        """
        return utils.set_arch(self,arch)

    def set_kickstart(self,kickstart):
        """
        It may not make sense for images to have kickstarts.  It really doesn't.
        However if the image type is 'iso' koan can create a virtual floppy
        and shove an answer file on it, to script an installation.  This may
        not be a kickstart per se, it might be a windows answer file (SIF) etc.
        """
        if kickstart is None or kickstart == "" or kickstart == "delete":
            self.kickstart = ""
            return True
        if utils.find_kickstart(kickstart):
            self.kickstart = kickstart
            return True
        raise CX(_("kickstart not found"))


    def set_file(self,filename):
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
        if num is None or num == "":
            num = 1
        try:
            self.network_count = int(num)
        except:
            raise CX("invalid network count")
        return True

    def set_virt_auto_boot(self,num):
        return utils.set_virt_auto_boot(self,num)

    def set_virt_file_size(self,num):
        return utils.set_virt_file_size(self,num)

    def set_virt_ram(self,num):
        return utils.set_virt_ram(self,num)

    def set_virt_type(self,vtype):
        return utils.set_virt_type(self,vtype)

    def set_virt_bridge(self,vbridge):
        return utils.set_virt_bridge(self,vbridge)

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

    def to_datastruct(self):
        return utils.to_datastruct(self,FIELDS)

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
        buf = buf + _("kickstart       : %s\n") % self.kickstart
        buf = buf + _("modified        : %s\n") % time.ctime(self.mtime)
        buf = buf + _("os version      : %s\n") % self.os_version
        buf = buf + _("owners          : %s\n") % self.owners
        buf = buf + _("virt bridge     : %s\n") % self.virt_bridge
        buf = buf + _("virt cpus       : %s\n") % self.virt_cpus
        buf = buf + _("network count   : %s\n") % self.network_count
        buf = buf + _("virt auto boot  : %s\n") % self.virt_auto_boot
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
            'kickstart'       :  self.set_kickstart,
            'owners'          :  self.set_owners,
            'virt-cpus'       :  self.set_virt_cpus,
            'virt_cpus'       :  self.set_virt_cpus,            
            'network-count'   :  self.set_network_count,
            'network_count'   :  self.set_network_count,            
            'virt-auto-boot'  :  self.set_virt_auto_boot,
            'virt_auto_boot'  :  self.set_virt_auto_boot,            
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

def get_fields():
   return {
     'name': {
       'type'    :'text',
       'valtype' :'str',
       'label'   :'Image Name',
       'example' :'Example: RHEL-5-i386',
       'size'    :'128',
       'width'   :'150px',
       'value'   :'',
       'default' :'',
       'opts'    :'',
       'setopts' :'disabled="true"',
       'order'   :0,
       'editable':True,
     },
     'ctime': {
       'type'    :'label',
       'valtype' :'str',
       'label'   :'Created',
       'value'   :'',
       'default' :'',
       'order'   :1,
       'editable':False,
     },
     'mtime': {
       'type'    :'label',
       'valtype' :'str',
       'label'   :'Last Modified',
       'value'   :'',
       'default' :'',
       'order'   :2,
       'editable':False,
     },
     'comment': {
       'type'    :'textarea',
       'valtype' :'str',
       'label'   :'Comment',
       'example' :'This is a free-form description field',
       'rows'    :'5',
       'cols'    :'30',
       'width'   :'400px',
       'value'   :'',
       'default' :'',
       'opts'    :'',
       'setopts' :'',
       'order'   :3,
       'editable':True,
        },
     'file': {
       'type'    :'text',
       'valtype' :'str',
       'label'   :'File',
       'example' :'Example: nfs://server/path/os-installer.iso',
       'size'    :'255',
       'width'   :'400px',
       'value'   :'',
       'default' :'',
       'opts'    :'',
       'setopts' :'',
       'order'   :4,
       'editable':True,
        },
     'arch': {
       'type'    :'radio',
       'valtype' :'str',
       'label'   :'Architecture',
       'example' :'What architecture is the image?',
       'value'   :'',
       'default' :'',
       'list'    :(('i386','i386'),('x86_64','x86_64')),
       'opts'    :'',
       'setopts' :'',
       'order'   :5,
       'editable':True,
     },
     'breed': {
       'type'    :'radio',
       'valtype' :'str',
       'label'   :'Breed',
       'example' :'What type of OS?',
       'value'   :'',
       'default' :'',
       'list'    :(('redhat','Red Hat Based'), ('debian','Debian'), ('ubuntu','Ubuntu'), ('suse','SuSE')),
       'opts'    :'',
       'setopts' :'',
       'order'   :6,
       'editable':True,
     },
     'virt_file_size': {
       'type'    :'text',
       'valtype' :'str',
       'label'   :'Virt Disk (GB)',
       'example' :'For virtual installs only, the virtual disk size in GB',
       'size'    :'5',
       'width'   :'150px',
       'value'   :'',
       'default' :'',
       'opts'    :'',
       'setopts' :'',
       'tdclass' :'virtedit',
       'order'   :7,
       'editable':True,
        },
     'virt_ram': {
       'type'    :'text',
       'valtype' :'str',
       'label'   :'Virt RAM (MB)',
       'example' :'For virtual installs only, the RAM size in MB',
       'size'    :'5',
       'width'   :'150px',
       'value'   :'',
       'default' :'',
       'opts'    :'',
       'setopts' :'',
       'tdclass' :'virtedit',
       'order'   :8,
       'editable':True,
        },
     'virt_auto_boot': {
       'type'    :'checkbox',
       'valtype' :'str',
       'label'   :'Virt Autoboot',
       'example' :'For virtual installs only, enable/disable VM auto start',
       'value'   :'',
       'default' :'',
       'list'    :[],
       'opts'    :'',
       'setopts' :'',
       'tdclass' :'virtedit',
       'order'   :9,
       'editable':True,
        },
     'virt_type': {
       'type'    :'radio',
       'valtype' :'str',
       'label'   :'Virt Type',
       'example' :'For virtual installs only, the virtualization technology koan should use',
       'value'   :'',
       'default' :'',
       'list'    :(['auto','Any'],['xenpv','Xen(pv)'],['xenfv','Xen(fv)'],['qemu','KVM/qemu'],['vmware','VMWare Server'],['vmwarew','VMWare WkStn']),
       'opts'    :'',
       'setopts' :'',
       'tdclass' :'virtedit',
       'order'   :10,
       'editable':True,
        },
     'virt_path': {
       'type'    :'text',
       'valtype' :'str',
       'label'   :'Virt Path',
       'example' :'For virtual installs only, sets koan\'s storage preferences, read manpage or leave blank',
       'size'    :'255',
       'width'   :'400px',
       'value'   :'',
       'default' :'',
       'opts'    :'',
       'setopts' :'',
       'tdclass' :'virtedit',
       'order'   :11,
       'editable':True,
        },
     'virt_cpus': {
       'type'    :'text',
       'valtype' :'str',
       'label'   :'Virt CPUs',
       'example' :'For virtual installs only, how many virtual CPUs?  This is an integer',
       'size'    :'255',
       'width'   :'150px',
       'value'   :'',
       'default' :'',
       'opts'    :'',
       'setopts' :'',
       'tdclass' :'virtedit',
       'order'   :12,
       'editable':True,
        },
     'network_count': {
       'type'    :'text',
       'valtype' :'str',
       'label'   :'NICs',
       'example' :'How many nics should be created This is an integer.',
       'size'    :'128',
       'width'   :'150px',
       'value'   :'',
       'default' :'',
       'opts'    :'',
       'setopts' :'',
       'tdclass' :'virtedit',
       'order'   :13,
       'editable':True,
     },
     'virt_bridge': {
       'type'    :'text',
       'valtype' :'str',
       'label'   :'Virt Bridge',
       'example' :'For virtual installs only, overrides the virtual networking bridge choice in settings',
       'size'    :'255',
       'width'   :'150px',
       'value'   :'',
       'default' :'',
       'opts'    :'',
       'setopts' :'',
       'tdclass' :'virtedit',
       'order'   :14,
       'editable':True,
     },
     'image_type': {
       'type'    :'radio',
       'valtype' :'str',
       'label'   :'Image Type',
       'example' :'What type of OS?',
       'value'   :'',
       'default' :'',
       'list'    :[['direct','direct'],['iso','iso'],['memdisk','memdisk'],['virt-clone','virt-clone']],
       'opts'    :'',
       'setopts' :'',
       'order'   :15,
       'editable':True,
     },
     'owners': {
       'type'    :'text',
       'valtype' :'list',
       'label'   :'Access Allowed For',
       'example' :'Applies only if using authz_ownership module, space delimited',
       'size'    :'255',
       'width'   :'400px',
       'value'   :'',
       'default' :'',
       'opts'    :'',
       'setopts' :'',
       'order'   :16,
       'editable':True,
     },
   }
