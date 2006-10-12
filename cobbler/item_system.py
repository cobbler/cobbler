"""
A Cobbler System.

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
import cexceptions

class System(item.Item):

    def __init__(self,config):
        self.config = config
        self.clear()

    def clear(self):
        self.name = None
        self.profile = None # a name, not a reference
        self.kernel_options = ""
        self.ks_meta = ""
        self.pxe_arch = "standard"
        self.pxe_address = ""

    def from_datastruct(self,seed_data):
        self.name = self.load_item(seed_data,'name')
        self.profile = self.load_item(seed_data,'profile')
        self.kernel_options = self.load_item(seed_data,'kernel_options')
        self.ks_meta = self.load_item(seed_data,'ks_meta')
        self.pxe_arch = self.load_item(seed_data,'pxe_arch')
        self.pxe_address = self.load_item(seed_data,'pxe_address')
        return self

    def set_name(self,name):
        """
        A name can be a resolvable hostname (it instantly resolved and replaced with the IP),
        any legal ipv4 address, or any legal mac address. ipv6 is not supported yet but _should_ be.
        See utils.py
        """
        if name == "default":
            self.name="default"
            return True
        new_name = utils.find_system_identifier(name)
        if not new_name:
            raise cexceptions.CobblerException("bad_sys_name")
        self.name = name  # we check it add time, but store the original value.
        return True

    def set_pxe_address(self,address):
        # restricting to address as IP only in dhcpd.conf is probably
        # incorrect ... some people may want to pin the hostname instead.
        # doing so, however, doesn't allow dhcpd.conf to be managed
        # by cobbler (since elilo can't do MAC addresses) -- this is 
        # covered in the man page.
        if not utils.is_ip(address) and not utils.is_mac(address):
            raise cexceptions.CobblerException("bad_ip")    
        self.pxe_address = address
        return True

    def set_profile(self,profile_name):
        """
	Set the system to use a certain named profile.  The profile
	must have already been loaded into the Profiles collection.
	"""
        if self.config.profiles().find(profile_name):
            self.profile = profile_name
            return True
        raise cexceptions.CobblerException("exc_profile")

    def set_pxe_arch(self,new_arch):
        """
        The PXE architecture field is naturally relevant to PXE only.
        Should someone have Itanium machines on a network, having 
        pxelinux.0 be the only option in the config file causes 
        problems.  Using an alternative architecture here allows
        for dhcpd.conf templating to "do the right thing" with
        those systems.  If manage_dhcp is off in /var/lib/cobbler/settings
        this parameter is meaningless.  It only has value when
        generating a dhcp file.
        """
        if new_arch == "standard" or new_arch == "ia64":
            self.pxe_arch = new_arch
            return True
        raise cexceptions.CobblerException("exc_pxe_arch")

    def is_valid(self):
        """
	A system is valid when it contains a valid name and a profile.
	"""
        if self.name is None:
            return False
        if self.profile is None:
            return False
        return True

    def to_datastruct(self):
        return {
           'name'     : self.name,
           'profile'  : self.profile,
           'kernel_options' : self.kernel_options,
           'ks_meta'  : self.ks_meta,
           'pxe_arch' : self.pxe_arch,
           'pxe_address' : self.pxe_address
        }

    def printable(self,id):
        buf =       "system %-4s     : %s\n" % (id, self.name)
        buf = buf + "profile         : %s\n" % self.profile
        buf = buf + "kernel options  : %s\n" % self.kernel_options
        buf = buf + "ks metadata     : %s\n" % self.ks_meta
        buf = buf + "pxe arch        : %s\n" % self.pxe_arch
        buf = buf + "pxe address     : %s\n" % self.pxe_address
        return buf

