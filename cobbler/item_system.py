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

    TYPE_NAME = _("system")
    COLLECTION_TYPE = "system"

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = System(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def clear(self,is_subobject=False):
        self.name            = None
        self.profile         = (None,     '<<inherit>>')[is_subobject]
        self.kernel_options  = ({},       '<<inherit>>')[is_subobject]
        self.ks_meta         = ({},       '<<inherit>>')[is_subobject]
        self.ip_address      = ("",       '<<inherit>>')[is_subobject]
        self.mac_address     = ("",       '<<inherit>>')[is_subobject]  
        self.netboot_enabled = (1,        '<<inherit>>')[is_subobject] 
        self.hostname        = ("",       '<<inheirt>>')[is_subobject]
        self.depth           = 2
        self.dhcp_tag        = "default"
        self.kickstart       = "<<inherit>>"   # use value in profile
        self.virt_path       = "<<inherit>>"   # use value in profile
        self.virt_type       = "<<inherit>>"   # use value in profile 

    def from_datastruct(self,seed_data):

        self.parent          = self.load_item(seed_data, 'parent')
        self.name            = self.load_item(seed_data, 'name')
        self.profile         = self.load_item(seed_data, 'profile')
        self.kernel_options  = self.load_item(seed_data, 'kernel_options', {})
        self.ks_meta         = self.load_item(seed_data, 'ks_meta', {})
        self.depth           = self.load_item(seed_data, 'depth', 2)        
        self.kickstart       = self.load_item(seed_data, 'kickstart', '<<inherit>>')
        self.virt_path       = self.load_item(seed_data, 'virt_path', '<<inherit>>') 
        self.virt_type       = self.load_item(seed_data, 'virt_type', '<<inherit>>')
        self.dhcp_tag        = self.load_item(seed_data, 'dhcp_tag', 'default')

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

        if self.kernel_options != "<<inherit>>" and type(self.kernel_options) != dict:
            self.set_kernel_options(self.kernel_options)
        if self.ks_meta != "<<inherit>>" and type(self.ks_meta) != dict:
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

    def get_parent(self):
        """
        Return object next highest up the tree.
        """
        if self.parent is None or self.parent == '':
            return self.config.profiles().find(name=self.profile)
        else:
            return self.config.systems().find(name=self.parent)

    def set_name(self,name):
        """
        In Cobbler 0.4.9, any name given is legal, but if it's not an IP or MAC, --ip-address of --mac-address must
        be given for PXE options to work.
        """

        # set appropriate fields if the name implicitly is a MAC or IP.
        # if the name is a hostname though, don't intuit that, as that's hard to determine

        if utils.is_mac(name):
           self.mac_address = name
        elif utils.is_ip(name):
           self.ip_address = name
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
        if self.name == "default":
           return True
        mac = self.get_mac_address()
        ip  = self.get_ip_address()
        if mac is None and ip is None:
           return False
        return True

    def set_dhcp_tag(self,dhcp_tag):
        self.dhcp_tag = dhcp_tag
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

    def set_pxe_address(self,address):
        # backwards compatibility for API users:
        return self.set_ip_address(address)

    def set_profile(self,profile_name):
        """
        Set the system to use a certain named profile.  The profile
        must have already been loaded into the Profiles collection.
        """
        p = self.config.profiles().find(name=profile_name)
        if p is not None:
            self.profile = profile_name
            self.depth = p.depth + 1 # subprofiles have varying depths.
            return True
        raise CX(_("invalid profile name"))

    def set_virt_path(self,path):
        """
        Virtual storage location suggestion, can be overriden by koan.
        """
        self.virt_path = path
        return True

    def set_virt_type(self,vtype):
        """
        Virtualization preference, can be overridden by koan.
        """
        if vtype.lower() not in [ "qemu", "xenpv", "auto" ]:
            raise CX(_("invalid virt type"))
        self.virt_type = vtype
        return True

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
        if netboot_enabled in [ True, "True", "true", 1, "1", "on", "yes", "y", "ON", "YES", "Y" ]:
            # this is a bit lame, though we don't know what the user will enter YAML wise...
            self.netboot_enabled = 1
        else:
            self.netboot_enabled = 0
        return True

    def is_valid(self):
        """
        A system is valid when it contains a valid name and a profile.
        """
        # NOTE: this validation code does not support inheritable distros at this time.
        # this is by design as inheritable systems don't make sense.
        if self.name is None:
            raise CX(_("need to specify a name for this object"))
            return False
        if self.profile is None:
            raise CX(_("need to specify a profile for this system"))
            return False
        return True

    def set_kickstart(self,kickstart):
        """
        Sets the kickstart.  This must be a NFS, HTTP, or FTP URL.
        Or filesystem path. Minor checking of the URL is performed here.

        NOTE -- usage of the --kickstart parameter in the profile
        is STRONGLY encouraged.  This is only for exception cases
        where a user already has kickstarts made for each system
        and can't leverage templating.  Profiles provide an important
        abstraction layer -- assigning systems to defined and repeatable 
        roles.
        """
        if utils.find_kickstart(kickstart):
            self.kickstart = kickstart
            return True
        raise CX(_("kickstart not found"))


    def to_datastruct(self):
        return {
           'name'            : self.name,
           'profile'         : self.profile,
           'kernel_options'  : self.kernel_options,
           'ks_meta'         : self.ks_meta,
           'ip_address'      : self.ip_address,
           'netboot_enabled' : self.netboot_enabled,
           'hostname'        : self.hostname,
           'mac_address'     : self.mac_address,
           'parent'          : self.parent,
           'depth'           : self.depth,
           'kickstart'       : self.kickstart,
           'virt_type'       : self.virt_type,
           'virt_path'       : self.virt_path,
           'dhcp_tag'        : self.dhcp_tag
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
        buf = buf + _("kickstart        : %s\n") % self.kickstart
        buf = buf + _("virt type        : %s\n") % self.virt_type
        buf = buf + _("virt path        : %s\n") % self.virt_path
        buf = buf + _("dhcp tag         : %s\n") % self.dhcp_tag
        return buf

    def remote_methods(self):
        return {
           'name'            : self.set_name,
           'profile'         : self.set_profile,
           'kopts'           : self.set_kernel_options,
           'ksmeta'          : self.set_ksmeta,
           'hostname'        : self.set_hostname,
           'ip-address'      : self.set_ip_address,
           'ip'              : self.set_ip_address,  # alias
           'mac-address'     : self.set_mac_address,
           'mac'             : self.set_mac_address, # alias
           'kickstart'       : self.set_kickstart,
           'netboot-enabled' : self.set_netboot_enabled,
           'virt-path'       : self.set_virt_path,
           'virt-type'       : self.set_virt_type,
           'dhcp-tag'        : self.set_dhcp_tag
        }

