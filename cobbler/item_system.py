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
        self.profile         = None
        self.kernel_options  = {}
        self.ks_meta         = {}    
        self.interfaces      = {}
        self.netboot_enabled = True
        self.depth           = 2
        self.kickstart       = "<<inherit>>"   # use value in profile
        self.virt_path       = "<<inherit>>"   # ""
        self.virt_type       = "<<inherit>>"   # "" 
        self.server          = "<<inherit>>"   # "" (or settings)

    def delete_interface(self,name):
        """
        Used to remove an interface.  Not valid for intf0.
        """
        if name == "intf0":
            raise CX(_("the first interface cannot be deleted"))
        if self.interfaces.has_key(name):
            del self.interfaces[name]
        else:
            # NOTE: raising an exception here would break the WebUI as currently implemented
            return False
        return True
        

    def __get_interface(self,name):

        if name not in [ "intf0", "intf1", "intf2", "intf3", "intf4", "intf5", "intf6", "intf7" ]:
            raise CX(_("internal error: invalid key for interface lookup or storage, must be 'intfX' where x is 0..7"))

        if not self.interfaces.has_key(name):
            self.interfaces[name] = {
                "mac_address" : "",
                "ip_address"  : "",
                "dhcp_tag"    : "",
                "subnet"      : "",
                "gateway"     : "",
                "hostname"    : "",
                "virt_bridge" : ""
            }
        return self.interfaces[name]

    def from_datastruct(self,seed_data):

        # load datastructures from previous and current versions of cobbler
        # and store (in-memory) in the new format.
        # (the main complexity here is the migration to NIC data structures)

        self.parent          = self.load_item(seed_data, 'parent')
        self.name            = self.load_item(seed_data, 'name')
        self.profile         = self.load_item(seed_data, 'profile')
        self.kernel_options  = self.load_item(seed_data, 'kernel_options', {})
        self.ks_meta         = self.load_item(seed_data, 'ks_meta', {})
        self.depth           = self.load_item(seed_data, 'depth', 2)        
        self.kickstart       = self.load_item(seed_data, 'kickstart', '<<inherit>>')
        self.virt_path       = self.load_item(seed_data, 'virt_path', '<<inherit>>') 
        self.virt_type       = self.load_item(seed_data, 'virt_type', '<<inherit>>')
        self.netboot_enabled = self.load_item(seed_data, 'netboot_enabled', True)
        self.server          = self.load_item(seed_data, 'server', '<<inherit>>')

        # backwards compat, these settings are now part of the interfaces data structure
        # and will contain data only in upgrade scenarios.

        __ip_address      = self.load_item(seed_data, 'ip_address',  "")
        __dhcp_tag        = self.load_item(seed_data, 'dhcp_tag',    "")
        __hostname        = self.load_item(seed_data, 'hostname',    "")
        __mac_address     = self.load_item(seed_data, 'mac_address', "")

        # now load the new-style interface definition data structure

        self.interfaces      = self.load_item(seed_data, 'interfaces', {})

        # now backfill the interface structure with any old values from
        # before the upgrade

        if not self.interfaces.has_key("intf0"):
            if __hostname != "":
                self.set_hostname(__hostname, "intf0")
            if __mac_address != "":
                self.set_mac_address(__mac_address, "intf0")
            if __ip_address != "":
                self.set_ip_address(__ip_address, "intf0")
            if __dhcp_tag != "":
                self.set_dhcp_tag(__dhcp_tag, "intf0")

        # backwards compatibility -- convert string entries to dicts for storage
        # this allows for better usage from the API.

        if self.kernel_options != "<<inherit>>" and type(self.kernel_options) != dict:
            self.set_kernel_options(self.kernel_options)
        if self.ks_meta != "<<inherit>>" and type(self.ks_meta) != dict:
            self.set_ksmeta(self.ks_meta)

        # explicitly re-call the set_name function to possibily populate MAC/IP.
        self.set_name(self.name)

        # coerce this into a boolean
        self.set_netboot_enabled(self.netboot_enabled)

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
        Set the name.  If the name is a MAC or IP, and the first MAC and/or IP is not defined, go ahead
        and fill that value in.  
        """
        intf = self.__get_interface("intf0")


        if self.name not in ["",None] and self.parent not in ["",None] and self.name == self.parent:
            raise CX(_("self parentage is weird"))
        if type(name) != type(""):
            raise CX(_("name must be a string"))
        for x in name:
            if not x.isalnum() and not x in [ "-", ".", ":", "+" ] :
                raise CX(_("invalid characters in name"))

        if utils.is_mac(name):
           if intf["mac_address"] == "":
               intf["mac_address"] = name
        elif utils.is_ip(name):
           if intf["ip_address"] == "":
               intf["ip_address"] = name
        self.name = name 

        return True

    def set_server(self,server):
        """
        If a system can't reach the boot server at the value configured in settings
        because it doesn't have the same name on it's subnet this is there for an override.
        """
        self.server = server
        return True

    def get_mac_address(self,interface="intf0"):
        """
        Get the mac address, which may be implicit in the object name or explicit with --mac-address.
        Use the explicit location first.
        """


        intf = self.__get_interface(interface)
        if intf["mac_address"] != "":
            return intf["mac_address"]
        # obsolete, because we should have updated the mac field already with set_name (?)
        # elif utils.is_mac(self.name) and interface == "intf0":
        #    return self.name
        else:
            return None

    def get_ip_address(self,interface="intf0"):
        """
        Get the IP address, which may be implicit in the object name or explict with --ip-address.
        Use the explicit location first.
        """

        intf = self.__get_interface(interface)
        if intf["ip_address"] != "": 
            return intf["ip_address"]
        #elif utils.is_ip(self.name) and interface == "intf0":
        #    return self.name
        else:
            return None

    def is_pxe_supported(self,interface="intf0"):
        """
        Can only add system PXE records if a MAC or IP address is available, else it's a koan
        only record.  Actually Itanium goes beyond all this and needs the IP all of the time
        though this is enforced elsewhere (action_sync.py).
        """
        if self.name == "default":
           return True
        mac = self.get_mac_address(interface)
        ip  = self.get_ip_address(interface)
        if mac is None and ip is None:
           return False
        return True

    def set_dhcp_tag(self,dhcp_tag,interface="intf0"):
        intf = self.__get_interface(interface)
        intf["dhcp_tag"] = dhcp_tag
        return True

    def set_hostname(self,hostname,interface="intf0"):
        intf = self.__get_interface(interface)
        intf["hostname"] = hostname
        return True

    def set_ip_address(self,address,interface="intf0"):
        """
        Assign a IP or hostname in DHCP when this MAC boots.
        Only works if manage_dhcp is set in /var/lib/cobbler/settings
        """
        intf = self.__get_interface(interface)
        if address == "" or utils.is_ip(address):
           intf["ip_address"] = address
           return True
        raise CX(_("invalid format for IP address (%s)") % address)

    def set_mac_address(self,address,interface="intf0"):
        intf = self.__get_interface(interface)
        if address == "" or utils.is_mac(address):
           intf["mac_address"] = address
           return True
        raise CX(_("invalid format for MAC address (%s)" % address))

    def set_gateway(self,gateway,interface="intf0"):
        intf = self.__get_interface(interface)
        intf["gateway"] = gateway
        return True

    def set_subnet(self,subnet,interface="intf0"):
        intf = self.__get_interface(interface)
        intf["subnet"] = subnet
        return True
    
    def set_virt_bridge(self,bridge,interface="intf0"):
        intf = self.__get_interface(interface)
        intf["virt_bridge"] = bridge
        return True

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
        if vtype.lower() not in [ "qemu", "xenpv", "xenfv", "vmware", "auto" ]:
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
        if str(netboot_enabled).lower() in [ "true", "1", "on", "yes", "y" ]:
            # this is a bit lame, though we don't know what the user will enter YAML wise...
            self.netboot_enabled = True 
        else:
            self.netboot_enabled = False
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
           'netboot_enabled' : self.netboot_enabled,
           'parent'          : self.parent,
           'depth'           : self.depth,
           'kickstart'       : self.kickstart,
           'virt_type'       : self.virt_type,
           'virt_path'       : self.virt_path,
           'interfaces'      : self.interfaces,
           'server'          : self.server
        }

    def printable(self):
        buf =       _("system           : %s\n") % self.name
        buf = buf + _("profile          : %s\n") % self.profile
        buf = buf + _("kernel options   : %s\n") % self.kernel_options
        buf = buf + _("ks metadata      : %s\n") % self.ks_meta
        
        buf = buf + _("netboot enabled? : %s\n") % self.netboot_enabled 
        buf = buf + _("kickstart        : %s\n") % self.kickstart
        buf = buf + _("virt type        : %s\n") % self.virt_type
        buf = buf + _("virt path        : %s\n") % self.virt_path
        buf = buf + _("server           : %s\n") % self.server

        counter = 0
        for (name,x) in self.interfaces.iteritems():
            buf = buf + _("interface        : %s\n") % (name)
            buf = buf + _("  mac address    : %s\n") % x.get("mac_address","")
            buf = buf + _("  ip address     : %s\n") % x.get("ip_address","")
            buf = buf + _("  hostname       : %s\n") % x.get("hostname","")
            buf = buf + _("  gateway        : %s\n") % x.get("gateway","")
            buf = buf + _("  subnet         : %s\n") % x.get("subnet","")
            buf = buf + _("  virt bridge    : %s\n") % x.get("virt_bridge","")
            buf = buf + _("  dhcp tag       : %s\n") % x.get("dhcp_tag","")
            counter = counter + 1
         

        return buf

    def modify_interface(self, hash):
        """
        Used by the WUI to modify an interface more-efficiently
        """
        for (key,value) in hash.iteritems():
            (field,interface) = key.split("-")
            if field == "macaddress" : self.set_mac_address(value, interface)
            if field == "ipaddress"  : self.set_ip_address(value, interface)
            if field == "hostname"   : self.set_hostname(value, interface)
            if field == "dhcptag"    : self.set_dhcp_tag(value, interface)
            if field == "subnet"     : self.set_subnet(value, interface)
            if field == "gateway"    : self.set_gateway(value, interface)
            if field == "virtbridge" : self.set_virt_bridge(value, interface)
        return True
         

    def remote_methods(self):
        return {
           'name'             : self.set_name,
           'profile'          : self.set_profile,
           'kopts'            : self.set_kernel_options,
           'ksmeta'           : self.set_ksmeta,
           'hostname'         : self.set_hostname,
           'kickstart'        : self.set_kickstart,
           'netboot-enabled'  : self.set_netboot_enabled,
           'virt-path'        : self.set_virt_path,
           'virt-type'        : self.set_virt_type,
           'modify-interface' : self.modify_interface,
           'delete-interface' : self.delete_interface,
           'server'           : self.set_server
        }

