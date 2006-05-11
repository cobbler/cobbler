"""
A cobbler distribution.  A distribution is a kernel, and initrd, and potentially
some kernel options.

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
import weakref
import os
import cexceptions

class Distro(item.Item):

    def __init__(self,config):
        """
        Constructor.  Requires a back reference to the Config management object.
        """
        self.config = config
        self.clear()

    def clear(self):
        """
        Reset this object.
        """
        self.name = None
        self.kernel = None
        self.initrd = None
        self.kernel_options = ""

    def from_datastruct(self,seed_data):
        """
        Modify this object to take on values in seed_data
        """
        self.name = seed_data['name']
        self.kernel = seed_data['kernel']
        self.initrd = seed_data['initrd']
        self.kernel_options = seed_data['kernel_options']
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
        raise cexceptions.CobblerException("no_kernel")

    def set_initrd(self,initrd):
        """
	Specifies an initrd image.  Path search works as in set_kernel.
	File must be named appropriately.
	"""
        if utils.find_initrd(initrd):
            self.initrd = initrd
            return True
        raise cexceptions.CobblerException("no_initrd")

    def is_valid(self):
        """
	A distro requires that the kernel and initrd be set.  All
	other variables are optional.
	"""
        for x in (self.name,self.kernel,self.initrd):
            if x is None: return False
        return True

    def to_datastruct(self):
        """
        Return a serializable datastructure representation of this object.
        """
        return {
           'name': self.name,
           'kernel': self.kernel,
           'initrd' : self.initrd,
           'kernel_options' : self.kernel_options
        }

    def printable(self, id):
        """
	Human-readable representation.
	"""
        kstr = utils.find_kernel(self.kernel)
        istr = utils.find_initrd(self.initrd)
        if kstr is None:
            kstr = "%s (NOT FOUND!)" % self.kernel
        elif os.path.isdir(self.kernel):
            kstr = "%s (FOUND BY SEARCH)" % kstr
        if istr is None:
            istr = "%s (NOT FOUND)" % self.initrd
        elif os.path.isdir(self.initrd):
            istr = "%s (FOUND BY SEARCH)" % istr
        buf =       "distro %-4s     : %s\n" % (id, self.name)
        buf = buf + "kernel          : %s\n" % kstr
        buf = buf + "initrd          : %s\n" % istr
        buf = buf + "kernel options  : %s\n" % self.kernel_options
        return buf

