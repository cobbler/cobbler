"""
A Cobbler Profile.  A profile is a reference to a distribution, possibly some kernel options, possibly some Virt options, and some kickstart data.

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

from rhpl.translate import _, N_, textdomain, utf8

class Profile(item.Item):

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Profile(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def clear(self):
        """
        Reset this object.
        """
        self.name = None
        self.distro = None # a name, not a reference
        self.kickstart = self.settings.default_kickstart
        self.kernel_options = {}
        self.ks_meta = {} 
        self.virt_file_size = 5    # GB.  5 = Decent _minimum_ default for FC5.
        self.virt_ram = 512        # MB.  Install with 256 not likely to pass
        self.repos = ""            # names of cobbler repo definitions

    def from_datastruct(self,seed_data):
        """
        Load this object's properties based on seed_data
        """

        self.name            = self.load_item(seed_data,'name')
        self.distro          = self.load_item(seed_data,'distro')
        self.kickstart       = self.load_item(seed_data,'kickstart')
        self.kernel_options  = self.load_item(seed_data,'kernel_options')
        self.ks_meta         = self.load_item(seed_data,'ks_meta')
        self.repos           = self.load_item(seed_data,'repos', [])
      
        # backwards compatibility
        if type(self.repos) != list:
            self.set_repos(self.repos)

        # virt specific 
        self.virt_ram        = self.load_item(seed_data,'virt_ram')
        self.virt_file_size  = self.load_item(seed_data,'virt_file_size')

        # backwards compatibility -- convert string entries to dicts for storage
        if type(self.kernel_options) != dict:
            self.set_kernel_options(self.kernel_options)
        if type(self.ks_meta) != dict:
            self.set_ksmeta(self.ks_meta)

        return self

    def set_distro(self,distro_name):
        """
	Sets the distro.  This must be the name of an existing
	Distro object in the Distros collection.
	"""
        if self.config.distros().find(distro_name):
            self.distro = distro_name
            return True
        raise CX(_("distribution not found"))

    def set_repos(self,repos):
        if type(repos) != list:
            # allow backwards compatibility support of string input
            repolist = repos.split(None)
        else:
            repolist = repos
        ok = True
        try:
	    repolist.remove('')
        except:
            pass
        for r in repolist:
            if not self.config.repos().find(r):
                ok = False 
                break
        if ok:
            self.repos = repolist
        else:
            raise CX(_("repository not found"))

    def set_kickstart(self,kickstart):
        """
	Sets the kickstart.  This must be a NFS, HTTP, or FTP URL.
	Minor checking of the URL is performed here.
	"""
        if utils.find_kickstart(kickstart):
            self.kickstart = kickstart
            return True
        raise CX(_("kickstart not found"))

    def set_virt_file_size(self,num):
        """
	For Virt only.
	Specifies the size of the virt image in gigabytes.  koan
	may contain some logic to ignore 'illogical' values of this size,
	though there are no guarantees.  0 tells koan to just
	let it pick a semi-reasonable size.  When in doubt, specify the
	size you want.
	"""
        # num is a non-negative integer (0 means default)
        try:
            inum = int(num)
            if inum != float(num):
                return CX(_("invalid virt file size"))
            if inum >= 0:
                self.virt_file_size = inum
                return True
            raise CX(_("invalid virt file size"))
        except:
            raise CX(_("invalid virt file size"))

    def set_virt_ram(self,num):
        """
        For Virt only.
        Specifies the size of the Virt RAM in MB.
        0 tells Koan to just choose a reasonable default.
        """
        # num is a non-negative integer (0 means default)
        try:
            inum = int(num)
            if inum != float(num):
                return CX(_("invalid virt ram size"))
            if inum >= 0:
                self.virt_ram = inum
                return True
            return CX(_("invalid virt ram size"))
        except:
            return CX(_("invalid virt ram size"))

    def is_valid(self):
        """
	A profile only needs a name and a distro.  Kickstart info,
	as well as Virt info, are optional.  (Though I would say provisioning
	without a kickstart is *usually* not a good idea).
	"""
        for x in (self.name, self.distro):
            if x is None:
                return False
        return True

    def to_datastruct(self):
        """
        Return hash representation for the serializer
        """
        return {
            'name'             : self.name,
            'distro'           : self.distro,
            'kickstart'        : self.kickstart,
            'kernel_options'   : self.kernel_options,
            'virt_file_size'   : self.virt_file_size,
            'virt_ram'         : self.virt_ram,
            'ks_meta'          : self.ks_meta,
            'repos'            : self.repos
        }

    def printable(self):
        """
        A human readable representaton
        """
        buf =       _("profile         : %s\n") % self.name
        buf = buf + _("distro          : %s\n") % self.distro
        buf = buf + _("kickstart       : %s\n") % self.kickstart
        buf = buf + _("kernel options  : %s\n") % self.kernel_options
        buf = buf + _("ks metadata     : %s\n") % self.ks_meta
        buf = buf + _("virt file size  : %s\n") % self.virt_file_size
        buf = buf + _("virt ram        : %s\n") % self.virt_ram
        buf = buf + _("repos           : %s\n") % self.repos
        return buf

