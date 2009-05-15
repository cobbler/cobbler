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
  ['name','',0,"Name",True,""],
  ['uid',"",0,"",False,""],
  ['arch','i386',0,"Architecture",True,""],
  ['file','',0,"File",True,""],
  ['parent','',0,"",False,""],
  ['depth',0,0,"",False,""],
  ['virt_auto_boot',"SETTINGS:virt_auto_boot",0,"Virt Auto Boot",True,""],
  ['virt_ram',"SETTINGS:default_virt_ram",0,"Virt RAM (MB)",True,""],
  ['virt_file_size',"SETTINGS:default_virt_file_size",0,"Virt File Size (GB)",True,""],
  ['virt_path','',0,"Virt Path",True,""],
  ['virt_type',"SETTINGS:default_virt_type",0,"Virt Type",True,""],
  ['virt_cpus',1,0,"Virt CPUs",True,""],
  ['network_count',1,0,"Virt NICs",True,""],
  ['virt_bridge',"SETTINGS:default_virt_bridge",0,"Virt Bridge",True,""],
  ['owners',"SETTINGS:default_ownership",0,"Owners",True,""],
  ['image_type',"iso",0,"Image Type",True,""],
  ['breed','redhat',0,"Breed",True,""],
  ['os_version','',0,"OS Version",True,""],
  ['comment','',0,"Comment",True,""],
  ['ctime',0,0,"",False,""],
  ['mtime',0,0,"",False,""],
  ['kickstart','',0,"Kickstart",True,""]
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
        raise CX(_("kickstart not found for image"))


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

    def to_datastruct(self):
        return utils.to_datastruct_from_fields(self,FIELDS)

    def printable(self):
        """
        A human readable representaton
        """
        return utils.printable_from_fields(self,FIELDS)
  
    def remote_methods(self):
        return utils.get_remote_methods_from_fields(self,FIELDS)


