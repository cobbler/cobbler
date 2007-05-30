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
from cexceptions import *
from rhpl.translate import _, N_, textdomain, utf8


class System(item.Item):

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
        self.ip_address = ""  # bad naming here, to the UI, this is usually 'ip-address'
        self.mac_address = ""  
        self.netboot_enabled = 1 
        self.hostname = ""

    def from_datastruct(self,seed_data):
        self.name            = self.load_item(seed_data, 'name')
        self.profile         = self.load_item(seed_data, 'profile')
        self.kernel_options  = self.load_item(seed_data, 'kernel_options')
        self.ks_meta         = self.load_item(seed_data, 'ks_meta')
        
        # backwards compat, load --ip-address from two possible sources.
        # the old --pxe-address was a bit of a misnomer, new value is --ip-address

        oldvar  = self.load_item(seed_data, 'pxe_address')
        if oldvar == "": # newer version, yay
            self.ip_address = self.load_item(seed_data, 'ip_address')
        else:
            self.ip_address = oldvar

        self.netboot_enabled = self.load_item(seed_data, 'netboot_enabled', 1)
        self.hostname        = self.load_item(seed_data, 'hostname')
        self.mac_address     = self.load_item(seed_data, 'mac_address')

        # backwards compatibility -- convert string entries to dicts for storage
        # this allows for better usage from the API.

        if type(self.kernel_options) != dict:
            self.set_kernel_options(self.kernel_options)
        if type(self.ks_meta) != dict:
            self.set_ksmeta(self.ks_meta)

        # backwards compatibility -- if name is an IP or a MAC, set appropriate fields
        # this will only happen once, as part of an upgrade path ... 
        # Explanation -- older cobbler's figured out the MAC and IP
        # from the system name, newer cobblers allow arbitrary naming but can tell when the
        # name is an IP or a MAC and use that if that info is not supplied.

        if self.mac_address == "" and utils.is_mac(self.name):
            self.mac_address = self.name
        elif self.ip_address == "" and utils.is_ip(self.name):
            self.ip_address = self.name

        return self

    def set_name(self,name):
        """
        In Cobbler 0.4.9, any name given is legal, but if it's not an IP or MAC, --ip-address of --mac-address must
        be given for PXE options to work.
        """

        # set appropriate fields if the name implicitly is a MAC or IP.
        # if the name is a hostname though, don't intuit that, as that's hard to determine

        if utils.is_mac(self.name):
           self.mac_address = self.name
        elif utils.is_ip(self.name):
           self.ip_address = self.name
        self.name = name 

        return True

    def get_mac_address(self):
        """
        Get the mac address, which may be implicit in the object name or explicit with --mac-address.
        Use the explicit location first.
        """
        if self.mac_address != "":
            return self.mac_address
        elif utils.is_mac(self.name):
            return self.name
        else:
            # no one ever set it, but that might be ok depending on usage.
            return None

    def get_ip_address(self):
        """
        Get the IP address, which may be implicit in the object name or explict with --ip-address.
        Use the explicit location first.
        """
        if self.ip_address != "": 
            return self.ip_address
        elif utils.is_ip(self.name):
            return self.name
        else:
            # no one ever set it, but that might be ok depending on usage.
            return None

    def is_pxe_supported(self):
        """
        Can only add system PXE records if a MAC or IP address is available, else it's a koan
        only record.  Actually Itanium goes beyond all this and needs the IP all of the time
        though this is enforced elsewhere (action_sync.py).
        """
        mac = self.get_mac_address()
        ip  = self.get_ip_address()
        if mac is None or ip is None:
           return False
        return True

    def set_hostname(self,hostname):
        self.hostname = hostname
        return True

    def set_ip_address(self,address):
        """
        Assign a IP or hostname in DHCP when this MAC boots.
        Only works if manage_dhcp is set in /var/lib/cobbler/settings
        """
        if utils.is_ip(address):
           self.ip_address = address
           return True
        raise CX(_("invalid format for IP address"))

    def set_mac_address(self,address):
        if utils.is_mac(address):
           self.mac_address = address
           return True
        raise CX(_("invalid format for MAC address"))

    def set_ip_address(self,address):
        # backwards compatibility for API users:
        return self.set_ip_address(address)

    def set_profile(self,profile_name):
        """
	Set the system to use a certain named profile.  The profile
	must have already been loaded into the Profiles collection.
	"""
        if self.config.profiles().find(profile_name):
            self.profile = profile_name
            return True
        raise CX(_("invalid profile name"))

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
           'ip_address'      : self.ip_address,
           'netboot_enabled' : self.netboot_enabled,
           'hostname'        : self.hostname,
           'mac_address'     : self.mac_address
        }

    def printable(self):
        buf =       _("system           : %s\n") % self.name
        buf = buf + _("profile          : %s\n") % self.profile
        buf = buf + _("kernel options   : %s\n") % self.kernel_options
        buf = buf + _("ks metadata      : %s\n") % self.ks_meta
        buf = buf + _("ip address       : %s\n") % self.get_ip_address()
        buf = buf + _("mac address      : %s\n") % self.get_mac_address()
        buf = buf + _("hostname         : %s\n") % self.hostname
        buf = buf + _("pxe info set?    : %s\n") % self.is_pxe_supported()
        buf = buf + _("config id        : %s\n") % utils.get_config_filename(self)
        buf = buf + _("netboot enabled? : %s\n") % self.netboot_enabled 
        return buf

