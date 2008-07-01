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
        self.name            = None
        self.file            = None

    def from_datastruct(self,seed_data):
        """
        Load this object's properties based on seed_data
        """

        self.parent          = self.load_item(seed_data,'parent','')
        self.file            = self.load_item(seed_data,'file','')

        return self

    def set_file(self,filename):
        """
        Stores the image location.  This should be accessible on all nodes
        that need to access it.
        """
        self.file = filename
        return True

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
            raise CX(_("no file specified"))
        if self.name is None or self.name == '':
            raise CX(_("no name specified"))
        return True

    # FIXME: add virt parameters here as needed

    def to_datastruct(self):
        """
        Return hash representation for the serializer
        """
        return {
            'name'             : self.name,
            'file'             : self.file,
            'depth'            : 0,
        }

    def printable(self):
        """
        A human readable representaton
        """
        buf =       _("image         : %s\n") % self.name
        buf = buf + _("file          : %s\n") % self.file
        return buf

  
    def remote_methods(self):
        return {           
            'name'            :  self.set_name,
            'file'            :  self.set_file,
            'owners'          :  self.set_owners
        }

