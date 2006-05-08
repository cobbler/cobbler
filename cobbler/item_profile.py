"""
A Cobbler Profile.  A profile is a reference to a distribution, possibly some kernel
options, possibly some Xen options, and some kickstart data.

Michael DeHaan <mdehaan@redhat.com>
"""

import utils
import item
from msg import *

class Profile(item.Item):

    def __init__(self,config):
        """
        Constructor.  Requires a backreference to Config.
        """
        self.config = config
        self.clear()

    def clear(self):
        """
        Reset this object.
        """
        self.name = None
        self.distro = None # a name, not a reference
        self.kickstart = None
        self.kernel_options = ''
        self.xen_name = 'xenguest'
        self.xen_file_size = 5 # GB
        self.xen_ram = 2048    # MB
        self.xen_mac = ''
        self.xen_paravirt = True

    def from_datastruct(self,seed_data):
        """
        Load this object's properties based on seed_data
        """
        self.name            = seed_data['name']
        self.distro          = seed_data['distro']
        self.kickstart       = seed_data['kickstart']
        self.kernel_options  = seed_data['kernel_options']
        self.xen_name        = seed_data['xen_name']
        if not self.xen_name or self.xen_name == '':
            self.xen_name    = self.name
        self.xen_ram         = seed_data['xen_ram']
        self.xen_file_size   = seed_data['xen_file_size']
        self.xen_mac         = seed_data['xen_mac']
        self.xen_paravirt    = seed_data['xen_paravirt']
        return self

    def set_distro(self,distro_name):
        """
	Sets the distro.  This must be the name of an existing
	Distro object in the Distros collection.
	"""
        if self.config.distros().find(distro_name):
            self.distro = distro_name
            return True
        utils.set_error("no_distro")
        return False

    def set_kickstart(self,kickstart):
        """
	Sets the kickstart.  This must be a NFS, HTTP, or FTP URL.
	Minor checking of the URL is performed here.
	"""
        if utils.find_kickstart(kickstart):
            self.kickstart = kickstart
            return True
        utils.set_error("no_kickstart")
        return False

    def set_xen_name(self,str):
        """
	For Xen only.
	Specifies what xenguest install should use for --name.
        xen-net-install may do conflict resolution, so this is mostly
        a hint...  To keep the shell happy, the 'str' cannot
	contain wildcards or slashes and may be subject to some other
        untainting later.
	"""
        # no slashes or wildcards
        for bad in [ '/', '*', '?' ]:
            if str.find(bad) != -1:
                return False
        self.xen_name = str
        return True

    def set_xen_file_size(self,num):
        """
	For Xen only.
	Specifies the size of the Xen image in gigabytes.  xen-net-install
	may contain some logic to ignore 'illogical' values of this size,
	though there are no guarantees.  0 tells koan to just
	let it pick a semi-reasonable size.  When in doubt, specify the
	size you want.
	"""
        # num is a non-negative integer (0 means default)
        try:
            inum = int(num)
            if inum != float(num):
                return False
            self.xen_file_size = inum
            if inum >= 0:
                return True
            return False
        except:
            return False

    def set_xen_mac(self,mac):
        """
	For Xen only.
	Specifies the mac address (or possibly later, a range) that
	xen-net-install should try to set on the domU.  Seeing these
	have a good chance of conflicting with other domU's, especially
	on a network, this setting is fairly experimental at this time.
	It's recommended that it *not* be used until we can get
	decent use cases for how this might work.
	"""
        # mac needs to be in mac format AA:BB:CC:DD:EE:FF or a range
        # ranges currently *not* supported, so we'll fail them
        if utils.is_mac(mac):
            self.xen_mac = mac
            return True
        else:
            return False

    def set_xen_paravirt(self,truthiness):
        """
	For Xen only.
	Specifies whether the system is a paravirtualized system or not.
	For ordinary computers, you want to pick 'true'.  Method accepts string
	'true'/'false' in all cases, or Python True/False.
	"""
        # truthiness needs to be True or False, or (lcased) string equivalents
        # yes, we *do* want to explicitly test against True/False
        # the string "foosball" is True, and that is not a valid argument for this function
        try:
            if (truthiness == False or truthiness.lower() == 'false'):
                self.xen_paravirt = False
            elif (truthiness == True or truthiness.lower() == 'true'):
                self.xen_paravirt = True
            else:
                return False
        except:
            return False
        return True

    def is_valid(self):
        """
	A profile only needs a name and a distro.  Kickstart info,
	as well as Xen info, are optional.  (Though I would say provisioning
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
            'name' : self.name,
            'distro' : self.distro,
            'kickstart' : self.kickstart,
            'kernel_options'  : self.kernel_options,
            'xen_name'        : self.xen_name,
            'xen_file_size'   : self.xen_file_size,
            'xen_ram'         : self.xen_ram,
            'xen_mac'         : self.xen_mac,
            'xen_paravirt'    : self.xen_paravirt
        }

    def printable(self):
        """
        A human readable representaton
        """
        buf = ""
        buf = buf + "profile         : %s\n" % self.name
        buf = buf + "distro          : %s\n" % self.distro
        buf = buf + "kickstart       : %s\n" % self.kickstart
        buf = buf + "kernel opts     : %s" % self.kernel_options
        buf = buf + "xen name        : %s" % self.xen_name
        buf = buf + "xen file size   : %s" % self.xen_file_size
        buf = buf + "xen ram         : %s" % self.xen_ram
        buf = buf + "xen mac         : %s" % self.xen_mac
        buf = buf + "xen paravirt    : %s" % self.xen_paravirt
        return buf

