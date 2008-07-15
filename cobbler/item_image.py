"""
A Cobbler Image.  Tracks a virtual or physical image, as opposed to a answer
file (kickstart) led installation.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import utils
import item
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
        self.file            = ''
        self.xml_file        = ''
        self.parent          = ''
        self.depth           = 0
        self.virt_ram        = self.settings.default_virt_ram
        self.virt_file_size  = self.settings.default_virt_file_size
        self.virt_path       = ''
        self.virt_type       = self.settings.default_virt_type
        self.virt_cpus       = 1
        self.virt_bridge     = self.settings.default_virt_bridge
        self.owners          = self.settings.default_ownership

    def from_datastruct(self,seed_data):
        """
        Load this object's properties based on seed_data
        """

        self.name            = self.load_item(seed_data,'name','')
        self.parent          = self.load_item(seed_data,'parent','')
        self.file            = self.load_item(seed_data,'file','')
        self.file            = self.load_item(seed_data,'xml_file','')
        self.depth           = self.load_item(seed_data,'depth',0)
        self.owners          = self.load_item(seed_data,'owners',self.settings.default_ownership)

        self.virt_ram        = self.load_item(seed_data, 'virt_ram', self.settings.default_virt_ram)
        self.virt_file_size  = self.load_item(seed_data, 'virt_file_size', self.settings.default_virt_file_size)
        self.virt_path       = self.load_item(seed_data, 'virt_path')
        self.virt_type       = self.load_item(seed_data, 'virt_type', self.settings.default_virt_type)
        self.virt_cpus       = self.load_item(seed_data, 'virt_cpus')
        self.virt_bridge     = self.load_item(seed_data, 'virt_bridge', self.settings.default_virt_bridge)

        self.set_owners(self.owners)

        return self

    def set_file(self,filename):
        """
        Stores the image location.  This should be accessible on all nodes
        that need to access it.  Format: either /mnt/commonpath/foo.iso or 
        nfs://host/path/foo.iso
        """
        # FIXME: this should accept NFS paths or filesystem paths
        self.file = filename
        return True

    def set_xml_file(self,filename):
        """
        Stores an xmlfile for virt-image.   This should be accessible
        on all nodes that need to access it also.  See set_file.
        """
        self.xml_file = filename
        return True

    def set_virt_cpus(self,num):
        return utils.set_virt_cpus(self,num)

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
        """
	A profile only needs a name and a distro.  Kickstart info,
	as well as Virt info, are optional.  (Though I would say provisioning
	without a kickstart is *usually* not a good idea).
	"""
        if self.file is None or self.file == '':
            raise CX(_("image has file specified"))
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
            'file'             : self.file,
            'xml_file'         : self.xml_file,
            'depth'            : 0,
            'parent'           : '',
            'owners'           : self.owners,
            'virt_ram'         : self.virt_ram,
            'virt_path'        : self.virt_path,
            'virt_cpus'        : self.virt_cpus,
            'virt_bridge'      : self.virt_bridge,
            'virt_file_size'   : self.virt_file_size
        }

    def printable(self):
        """
        A human readable representaton
        """
        buf =       _("image           : %s\n") % self.name
        buf = buf + _("file (image)    : %s\n") % self.file
        buf = buf + _("xml file        : %s\n") % self.xml_file
        buf = buf + _("owners          : %s\n") % self.owners
        buf = buf + _("virt bridge     : %s\n") % self.virt_bridge
        buf = buf + _("virt cpus       : %s\n") % self.virt_cpus
        buf = buf + _("virt file size  : %s\n") % self.virt_file_size
        buf = buf + _("virt path       : %s\n") % self.virt_path
        buf = buf + _("virt ram        : %s\n") % self.virt_ram
        buf = buf + _("virt type       : %s\n") % self.virt_type
        return buf

  
    def remote_methods(self):
        return {           
            'name'            :  self.set_name,
            'file'            :  self.set_file,
            'xml_file'        :  self.set_xml_file,
            'owners'          :  self.set_owners,
            'virt-cpus'       :  self.set_virt_cpus,
            'virt-file-size'  :  self.set_virt_file_size,
            'virt-path'       :  self.set_virt_path,
            'virt-ram'        :  self.set_virt_ram,
            'virt-type'       :  self.set_virt_type
        }

