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
from rhpl.translate import _, N_, textdomain, utf8


class System(item.Item):

    #def __init__(self,config):
    #    self.config = config
    #    self.clear()

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = System(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def clear(self):
        self.name = None
        self.profile = None # a name, not a reference
        self.kernel_options = {}
        self.ks_meta = {}
        self.pxe_address = ""
        self.netboot_enabled = 1 
        self.hostname = ""

    def from_datastruct(self,seed_data):
        self.name            = self.load_item(seed_data, 'name')
        self.profile         = self.load_item(seed_data, 'profile')
        self.kernel_options  = self.load_item(seed_data, 'kernel_options')
        self.ks_meta         = self.load_item(seed_data, 'ks_meta')
        self.pxe_address     = self.load_item(seed_data, 'pxe_address')
        self.netboot_enabled = self.load_item(seed_data, 'netboot_enabled', 1)
        self.hostname        = self.load_item(seed_data, 'hostname')

        # backwards compatibility -- convert string entries to dicts for storage
        if type(self.kernel_options) != dict:
            self.set_kernel_options(self.kernel_options)
        if type(self.ks_meta) != dict:
            self.set_ksmeta(self.ks_meta)

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

    def set_hostname(self,hostname):
        self.hostname = hostname
        return True

    def set_ip_address(self,address):
        # allow function to use more sensical name
        return self.set_pxe_address(address)

    def set_pxe_address(self,address):
        """
        Assign a IP or hostname in DHCP when this MAC boots.
        Only works if manage_dhcp is set in /var/lib/cobbler/settings
        """
        # restricting to address as IP only in dhcpd.conf is probably
        # incorrect ... some people may want to pin the hostname instead.
        # doing so, however, doesn't allow dhcpd.conf to be managed
        # by cobbler (since elilo can't do MAC addresses) -- this is
        # covered in the man page.
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

    def set_netboot_enabled(self,netboot_enabled):
        """
        If true, allows per-system PXE files to be generated on sync (or add).  If false,
        these files are not generated, thus eliminating the potential for an infinite install
        loop when systems are set to PXE boot first in the boot order.  In general, users
        who are PXE booting first in the boot order won't create system definitions, so this
        feature primarily comes into play for programmatic users of the API, who want to
        initially create a system with netboot enabled and then disable it after the system installs, 
        as triggered by some action in kickstart %post.   For this reason, this option is not
        surfaced in the CLI, output, or documentation (yet).

        Use of this option does not affect the ability to use PXE menus.  If an admin has machines 
        set up to PXE only after local boot fails, this option isn't even relevant.
        """
        if netboot_enabled in [ True, "True", "true", 1, "on", "yes", "y", "ON", "YES", "Y" ]:
            # this is a bit lame, though we don't know what the user will enter YAML wise...
            self.netboot_enabled = 1
        else:
            self.netboot_enabled = 0
        return True

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
           'name'            : self.name,
           'profile'         : self.profile,
           'kernel_options'  : self.kernel_options,
           'ks_meta'         : self.ks_meta,
           'pxe_address'     : self.pxe_address,
           'netboot_enabled' : self.netboot_enabled,
           'hostname'        : self.hostname,
        }

    def printable(self):
        buf =       "system          : %s\n" % self.name
        buf = buf + "profile         : %s\n" % self.profile
        buf = buf + "kernel options  : %s\n" % self.kernel_options
        buf = buf + "ks metadata     : %s\n" % self.ks_meta
        buf = buf + "ip address      : %s\n" % self.pxe_address
        buf = buf + "hostname        : %s\n" % self.hostname
        return buf

