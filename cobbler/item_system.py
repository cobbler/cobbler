"""
A Cobbler System.

Copyright 2006-2009, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import utils
import item
import time
from cexceptions import *
from utils import _

# this datastructure is described in great detail in item_distro.py -- read the comments there.

FIELDS = [
  ["name","",0,"Name",True,"Ex: vanhalen.example.org",0,"str"],
  ["uid","",0,"",False,"",0,"str"],
  ["owners","SETTINGS:default_ownership",0,"Owners",True,"Owners list for authz_ownership (space delimited)",0,"list"],
  ["profile",None,0,"Profile",True,"Parent profile",[],"str"],
  ["image",None,0,"Image",True,"Parent image (if not a profile)",0,"str"],
  ["kernel_options",{},0,"Kernel Options",True,"Ex: selinux=permissive",0,"dict"],
  ["kernel_options_post",{},0,"Kernel Options (Post Install)",True,"Ex: clocksource=pit noapic",0,"dict"],
  ["ks_meta",{},0,"Kickstart Metadata",True,"Ex: dog=fang agent=86",0,"dict"],
  ["netboot_enabled",True,0,"Netboot Enabled",True,"PXE (re)install this machine at next boot?",0,"bool"],
  ["kickstart","<<inherit>>",0,"Kickstart",True,"Path to kickstart template",0,"str"],
  ["comment","",0,"Comment",True,"Free form text description",0,"str"],
  ["depth",2,0,"",False,"",0,"int"],
  ["server","<<inherit>>",0,"Server Override",True,"See manpage or leave blank",0,"str"],
  ["virt_path","<<inherit>>",0,"Virt Path",True,"Ex: /directory or VolGroup00",0,"str"],
  ["virt_type","<<inherit>>",0,"Virt Type",True,"Virtualization technology to use",["xenpv","xenfv","qemu","vmware"],"str"],
  ["virt_cpus","<<inherit>>",0,"Virt CPUs",True,"",0,"int"],
  ["virt_file_size","<<inherit>>",0,"Virt File Size(GB)",True,"",0,"float"],
  ["virt_ram","<<inherit>>",0,"Virt RAM (MB)",True,"",0,"int"],
  ["virt_auto_boot","<<inherit>>",0,"Virt Auto Boot",True,"Auto boot this VM?",0,"bool"],
  ["ctime",0,0,"",False,"",0,"float"],
  ["mtime",0,0,"",False,"",0,"float"],
  ["power_type","SETTINGS:power_management_default_type",0,"Power Management Type",True,"",utils.get_power_types(),"str"],
  ["power_address","",0,"Power Management Address",True,"Ex: power-device.example.org",0,"str"],
  ["power_user","",0,"Power Username ",True,"",0,"str"],
  ["power_pass","",0,"Power Password",True,"",0,"str"],
  ["power_id","",0,"Power ID",True,"Usually a plug number or blade name, if power type requires it",0,"str"],
  ["hostname","",0,"Hostname",True,"",0,"str"],
  ["gateway","",0,"Gateway",True,"",0,"str"],
  ["name_servers",[],0,"Name Servers",True,"space delimited",0,"list"],
  ["name_servers_search",[],0,"Name Servers Search Path",True,"space delimited",0,"list"],
  ["ipv6_default_device","",0,"IPv6 Default Device",True,"",0,"str"],
  ["ipv6_autoconfiguration",False,0,"IPv6 Autoconfiguration",True,"",0,"bool"],
  ["network_widget_a","",0,"Add Interface",True,"",0,"str"], # not a real field, a marker for the web app
  ["network_widget_b","",0,"Edit Interface",True,"",0,"str"], # not a real field, a marker for the web app
  ["*mac_address","",0,"MAC Address",True,"(Place \"random\" in this field for a random MAC Address.)",0,"str"],
  ["*mtu","",0,"MTU",True,"",0,"str"],
  ["*ip_address","",0,"IP Address",True,"",0,"str"],
  ["*bonding","na",0,"Bonding Mode",True,"",["na","master","slave"],"str"],
  ["*bonding_master","",0,"Bonding Master",True,"",0,"str"],
  ["*bonding_opts","",0,"Bonding Opts",True,"",0,"str"],
  ["*static",False,0,"Static",True,"Is this interface static?",0,"bool"],
  ["*subnet","",0,"Subnet",True,"",0,"str"],
  ["*dhcp_tag","",0,"DHCP Tag",True,"",0,"str"],
  ["*dns_name","",0,"DNS Name",True,"",0,"str"],
  ["*static_routes",[],0,"Static Routes",True,"",0,"list"],
  ["*virt_bridge","",0,"Virt Bridge",True,"",0,"str"],
  ["*ipv6_address","",0,"IPv6 Address",True,"",0,"str"],
  ["*ipv6_secondaries",[],0,"IPv6 Secondaries",True,"space delimited",0,"list"],
  ["*ipv6_mtu","",0,"IPv6 MTU",True,"",0,"str"],
  ["*ipv6_static_routes",[],0,"IPv6 Static Routes",True,"",0,"list"],
  ["*ipv6_default_gateway","",0,"IPv6 Default Gateway",True,"",0,"str"],
  ["mgmt_classes",[],0,"Management Classes",True,"For external config management",0,"list"],
  ["mgmt_parameters","<<inherit>>",0,"Management Parameters",True,"Parameters which will be handed to your management application (Must be valid YAML dictionary)", 0,"str"],
  ["fetchable_files",{},0,"Fetchable Files",True,"Templates for tftp or wget",0,"dict"],
  ["template_files",{},0,"Template Files",True,"File mappings for built-in configuration management",0,"dict"],
  ["redhat_management_key","<<inherit>>",0,"Red Hat Management Key",True,"Registration key for RHN, Satellite, or Spacewalk",0,"str"],
  ["redhat_management_server","<<inherit>>",0,"Red Hat Management Server",True,"Address of Satellite or Spacewalk Server",0,"str"],
  ["template_remote_kickstarts", "SETTINGS:template_remote_kickstarts", "SETTINGS:template_remote_kickstarts", "", False, "", 0, "bool"]
]

class System(item.Item):

    TYPE_NAME = _("system")
    COLLECTION_TYPE = "system"

    def get_fields(self):
        return FIELDS

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = System(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def delete_interface(self,name):
        """
        Used to remove an interface.
        """
        if self.interfaces.has_key(name) and len(self.interfaces) > 1:
            del self.interfaces[name]
        else:
            if not self.interfaces.has_key(name):
                # no interface here to delete
                pass
            else:
                raise CX(_("At least one interface needs to be defined."))

        return True
        

    def __get_interface(self,name):

        if not self.interfaces.has_key(name):
            self.interfaces[name] = {
                "mac_address"    : "",
                "mtu"            : "",
                "ip_address"     : "",
                "dhcp_tag"       : "",
                "subnet"         : "",
                "virt_bridge"    : "",
                "static"         : False,
                "bonding"        : "",
                "bonding_master" : "",
                "bonding_opts"   : "",
                "dns_name"       : "",
                "static_routes"  : [],
                "ipv6_address"   : "",
                "ipv6_secondaries"  : [],
                "ipv6_mtu"       : "",
                "ipv6_static_routes"  : [],
                "ipv6_default_gateway" : "",
            }

        return self.interfaces[name]


    def from_datastruct(self,seed_data):
        # FIXME: most definitely doesn't grok interfaces yet.
        return utils.from_datastruct_from_fields(self,seed_data,FIELDS)

    def get_parent(self):
        """
        Return object next highest up the tree.
        """
        if (self.parent is None or self.parent == '') and self.profile:
            return self.config.profiles().find(name=self.profile)
        elif (self.parent is None or self.parent == '') and self.image:
            return self.config.images().find(name=self.image)
        else:
            return self.config.systems().find(name=self.parent)

    def set_name(self,name):
        """
        Set the name.  If the name is a MAC or IP, and the first MAC and/or IP is not defined, go ahead
        and fill that value in.  
        """

        if self.name not in ["",None] and self.parent not in ["",None] and self.name == self.parent:
            raise CX(_("self parentage is weird"))
        if not isinstance(name, basestring):
            raise CX(_("name must be a string"))
        for x in name:
            if not x.isalnum() and not x in [ "_", "-", ".", ":", "+" ] :
                raise CX(_("invalid characters in name: %s") % x)

        # Stuff here defaults to eth0. Yes, it's ugly and hardcoded, but so was
        # the default interface behaviour that's now removed. ;)
        # --Jasper Capel
        if utils.is_mac(name):
           intf = self.__get_interface("eth0")
           if intf["mac_address"] == "":
               intf["mac_address"] = name
        elif utils.is_ip(name):
           intf = self.__get_interface("eth0")
           if intf["ip_address"] == "":
               intf["ip_address"] = name
        self.name = name 

        return True

    def set_redhat_management_key(self,key):
        return utils.set_redhat_management_key(self,key)

    def set_redhat_management_server(self,server):
        return utils.set_redhat_management_server(self,server)

    def set_server(self,server):
        """
        If a system can't reach the boot server at the value configured in settings
        because it doesn't have the same name on it's subnet this is there for an override.
        """
        if server is None or server == "":
            server = "<<inherit>>"
        self.server = server
        return True

    def get_mac_address(self,interface):
        """
        Get the mac address, which may be implicit in the object name or explicit with --mac-address.
        Use the explicit location first.
        """

        intf = self.__get_interface(interface)

        if intf["mac_address"] != "":
            return intf["mac_address"].strip()
        else:
            return None

    def get_ip_address(self,interface):
        """
        Get the IP address, which may be implicit in the object name or explict with --ip-address.
        Use the explicit location first.
        """

        intf = self.__get_interface(interface)

        if intf["ip_address"] != "": 
            return intf["ip_address"].strip()
        else:
            return ""

    def is_management_supported(self,cidr_ok=True):
        """
        Can only add system PXE records if a MAC or IP address is available, else it's a koan
        only record.  Actually Itanium goes beyond all this and needs the IP all of the time
        though this is enforced elsewhere (action_sync.py).
        """
        if self.name == "default":
           return True
        for (name,x) in self.interfaces.iteritems():
            mac = x.get("mac_address",None)
            ip  = x.get("ip_address",None)
            if ip is not None and not cidr_ok and ip.find("/") != -1:
                # ip is in CIDR notation
                return False
            if mac is not None or ip is not None:
                # has ip and/or mac
                return True
        return False

    def set_dhcp_tag(self,dhcp_tag,interface):
        intf = self.__get_interface(interface)
        intf["dhcp_tag"] = dhcp_tag
        return True

    def set_dns_name(self,dns_name,interface):
        intf = self.__get_interface(interface)
        # FIXME: move duplicate supression code to the object validation
        # functions to take a harder line on supression?
        if dns_name != "" and not str(self.config._settings.allow_duplicate_hostnames).lower() in [ "1", "y", "yes"]:
           matched = self.config.api.find_items("system", {"dns_name" : dns_name})
           for x in matched:
               if x.name != self.name:
                   raise CX("dns-name duplicated: %s" % dns_name)


        intf["dns_name"] = dns_name
        return True
 
    def set_static_routes(self,routes,interface):
        intf = self.__get_interface(interface)
        data = utils.input_string_or_list(routes)
        intf["static_routes"] = data
        return True

    def set_hostname(self,hostname):
        if hostname is None:
           hostname = ""
        self.hostname = hostname
        return True

    def set_static(self,truthiness,interface):
        intf = self.__get_interface(interface)
        intf["static"] = utils.input_boolean(truthiness)
        return True

    def set_ip_address(self,address,interface):
        """
        Assign a IP or hostname in DHCP when this MAC boots.
        Only works if manage_dhcp is set in /etc/cobbler/settings
        """
        intf = self.__get_interface(interface)

        # FIXME: move duplicate supression code to the object validation
        # functions to take a harder line on supression?
        if address != "" and not str(self.config._settings.allow_duplicate_ips).lower() in [ "1", "y", "yes"]:
           matched = self.config.api.find_items("system", {"ip_address" : address})
           for x in matched:
               if x.name != self.name:
                   raise CX("IP address duplicated: %s" % address)


        if address == "" or utils.is_ip(address):
           intf["ip_address"] = address.strip()
           return True
        raise CX(_("invalid format for IP address (%s)") % address)

    def set_mac_address(self,address,interface):
        if address == "random":
           address = utils.get_random_mac(self.config.api)

        # FIXME: move duplicate supression code to the object validation
        # functions to take a harder line on supression?
        if address != "" and not str(self.config._settings.allow_duplicate_macs).lower() in [ "1", "y", "yes"]:
           matched = self.config.api.find_items("system", {"mac_address" : address})
           for x in matched:
               if x.name != self.name:
                   raise CX("MAC address duplicated: %s" % address)

        intf = self.__get_interface(interface)
        if address == "" or utils.is_mac(address):
           intf["mac_address"] = address.strip()
           return True
        raise CX(_("invalid format for MAC address (%s)" % address))


    def set_gateway(self,gateway):
        if gateway is None:
           gateway = ""
        if utils.is_ip(gateway) or gateway == "":
           self.gateway = gateway
        else:
           raise CX(_("invalid format for gateway IP address (%s)") % gateway)
        return True
 
    def set_name_servers(self,data):
        if data == "<<inherit>>":
           data = []
        data = utils.input_string_or_list(data)
        self.name_servers = data
        return True

    def set_name_servers_search(self,data):
        if data == "<<inherit>>":
           data = []
        data = utils.input_string_or_list(data)
        self.name_servers_search = data
        return True

    def set_subnet(self,subnet,interface):
        intf = self.__get_interface(interface)
        intf["subnet"] = subnet
        return True
    
    def set_virt_bridge(self,bridge,interface):
        if bridge == "":
            bridge = self.settings.default_virt_bridge
        intf = self.__get_interface(interface)
        intf["virt_bridge"] = bridge
        return True

    def set_bonding(self,bonding,interface):
        if bonding not in ["master","slave","na",""] : 
            raise CX(_("bonding value must be one of: master, slave, na"))
        if bonding == "na":
            bonding = ""
        intf = self.__get_interface(interface)
        intf["bonding"] = bonding
        return True

    def set_bonding_master(self,bonding_master,interface):
        intf = self.__get_interface(interface)
        intf["bonding_master"] = bonding_master
        return True

    def set_bonding_opts(self,bonding_opts,interface):
        intf = self.__get_interface(interface)
        intf["bonding_opts"] = bonding_opts
        return True

    def set_ipv6_autoconfiguration(self,truthiness):
        self.ipv6_autoconfiguration = utils.input_boolean(truthiness)
        return True

    def set_ipv6_default_device(self,interface_name):
        if interface_name is None:
           interface_name = ""
        self.ipv6_default_device = interface_name
        return True

    def set_ipv6_address(self,address,interface):
        """
        Assign a IP or hostname in DHCP when this MAC boots.
        Only works if manage_dhcp is set in /etc/cobbler/settings
        """
        intf = self.__get_interface(interface)
        if address == "" or utils.is_ip(address):
           intf["ipv6_address"] = address.strip()
           return True
        raise CX(_("invalid format for IPv6 IP address (%s)") % address)

    def set_ipv6_secondaries(self,addresses,interface):
        intf = self.__get_interface(interface)
        data = utils.input_string_or_list(addresses)
        secondaries = []
        for address in data:
           if address == "" or utils.is_ip(address):
               secondaries.append(address)
           else:
               raise CX(_("invalid format for IPv6 IP address (%s)") % address)

        intf["ipv6_secondaries"] = secondaries
        return True

    def set_ipv6_default_gateway(self,address,interface):
        intf = self.__get_interface(interface)
        if address == "" or utils.is_ip(address):
           intf["ipv6_default_gateway"] = address.strip()
           return True
        raise CX(_("invalid format for IPv6 IP address (%s)") % address)

    def set_ipv6_static_routes(self,routes,interface):
        intf = self.__get_interface(interface)
        data = utils.input_string_or_list(routes)
        intf["ipv6_static_routes"] = data
        return True

    def set_ipv6_mtu(self,mtu,interface):
        intf = self.__get_interface(interface)
        intf["ipv6_mtu"] = mtu
        return True

    def set_mtu(self,mtu,interface):
        intf = self.__get_interface(interface)
        intf["mtu"] = mtu
        return True

    def set_profile(self,profile_name):
        """
        Set the system to use a certain named profile.  The profile
        must have already been loaded into the Profiles collection.
        """
        old_parent = self.get_parent()
        if profile_name in [ "delete", "None", "~", ""] or profile_name is None:
            self.profile = ""
            if isinstance(old_parent, item.Item):
                old_parent.children.pop(self.name, 'pass')
            return True

        self.image = "" # mutual exclusion rule

        p = self.config.profiles().find(name=profile_name)
        if p is not None:
            self.profile = profile_name
            self.depth = p.depth + 1 # subprofiles have varying depths.
            if isinstance(old_parent, item.Item):
                old_parent.children.pop(self.name, 'pass')
            new_parent = self.get_parent()
            if isinstance(new_parent, item.Item):
                new_parent.children[self.name] = self
            return True
        raise CX(_("invalid profile name: %s") % profile_name)

    def set_image(self,image_name):
        """
        Set the system to use a certain named image.  Works like set_profile
        but cannot be used at the same time.  It's one or the other.
        """
        old_parent = self.get_parent()
        if image_name in [ "delete", "None", "~", ""] or image_name is None:
            self.image = ""
            if isinstance(old_parent, item.Item):
                old_parent.children.pop(self.name, 'pass')
            return True

        self.profile = "" # mutual exclusion rule

        img = self.config.images().find(name=image_name)

        if img is not None:
            self.image = image_name
            self.depth = img.depth + 1
            if isinstance(old_parent, item.Item):
                old_parent.children.pop(self.name, 'pass')
            new_parent = self.get_parent()
            if isinstance(new_parent, item.Item):
                new_parent.children[self.name] = self
            return True
        raise CX(_("invalid image name (%s)") % image_name)

    def set_virt_cpus(self,num):
        return utils.set_virt_cpus(self,num)

    def set_virt_file_size(self,num):
        return utils.set_virt_file_size(self,num)
 
    def set_virt_auto_boot(self,num):
        return utils.set_virt_auto_boot(self,num)

    def set_virt_ram(self,num):
        return utils.set_virt_ram(self,num)

    def set_virt_type(self,vtype):
        return utils.set_virt_type(self,vtype)

    def set_virt_path(self,path):
        return utils.set_virt_path(self,path,for_system=True)

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
        self.netboot_enabled = utils.input_boolean(netboot_enabled)
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
        if kickstart is None or kickstart in [ "", "delete", "<<inherit>>" ]:
            self.kickstart = "<<inherit>>"
            return True
        if utils.find_kickstart(kickstart):
            self.kickstart = kickstart
            return True
        raise CX(_("kickstart not found: %s" % kickstart))


    def set_power_type(self, power_type):
        # FIXME: modularize this better
        if power_type is None:
            power_type = ""
        choices = utils.get_power_types()
        choices.sort()
        if power_type not in choices:
            raise CX("power type must be one of: %s" % ",".join(choices))
        self.power_type = power_type
        return True

    def set_power_user(self, power_user):
        if power_user is None:
           power_user = ""
        utils.safe_filter(power_user)
        self.power_user = power_user
        return True 

    def set_power_pass(self, power_pass):
        if power_pass is None:
           power_pass = ""
        utils.safe_filter(power_pass)
        self.power_pass = power_pass
        return True    

    def set_power_address(self, power_address):
        if power_address is None:
           power_address = ""
        utils.safe_filter(power_address)
        self.power_address = power_address
        return True

    def set_power_id(self, power_id):
        if power_id is None:
           power_id = ""
        utils.safe_filter(power_id)
        self.power_id = power_id
        return True

    def modify_interface(self, hash):
        """
        Used by the WUI to modify an interface more-efficiently
        """
        for (key,value) in hash.iteritems():
            (field,interface) = key.split("-")
            field = field.replace("_","").replace("-","")
            if field == "macaddress"          : self.set_mac_address(value, interface)
            if field == "mtu"                 : self.set_mtu(value, interface)
            if field == "ipaddress"           : self.set_ip_address(value, interface)
            if field == "dnsname"             : self.set_dns_name(value, interface)
            if field == "static"              : self.set_static(value, interface)
            if field == "dhcptag"             : self.set_dhcp_tag(value, interface)
            if field == "subnet"              : self.set_subnet(value, interface)
            if field == "virtbridge"          : self.set_virt_bridge(value, interface)
            if field == "bonding"             : self.set_bonding(value, interface)
            if field == "bondingmaster"       : self.set_bonding_master(value, interface)
            if field == "bondingopts"         : self.set_bonding_opts(value, interface)
            if field == "staticroutes"        : self.set_static_routes(value, interface)
            if field == "ipv6address"         : self.set_ipv6_address(value, interface)
            if field == "ipv6secondaries"     : self.set_ipv6_secondaries(value, interface)
            if field == "ipv6mtu"             : self.set_ipv6_mtu(value, interface)
            if field == "ipv6staticroutes"    : self.set_ipv6_static_routes(value, interface)
            if field == "ipv6defaultgateway"  : self.set_ipv6_default_gateway(value, interface)

        return True

    def check_if_valid(self):
        if self.name is None or self.name == "":
            raise CX("name is required")
        if self.profile is None or self.profile == "":
            if self.image is None or self.image == "":
                raise CX("Error with system %s - profile or image is required" % (self.name))
            
    def set_template_remote_kickstarts(self, template):
        """
        Sets whether or not the server is configured to template remote 
        kickstarts.
        """
        self.template_remote_kickstarts = utils.input_boolean(template)
        return True


