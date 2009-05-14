"""
A Cobbler System.

Copyright 2006-2008, Red Hat, Inc
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

FIELDS = [
    [ "name"                      , None ],
    [ "uid"                       , "" ],
    [ "owners"                    , "SETTINGS:default_ownership" ],
    [ "profile"                   , None ],
    [ "image"                     , None ],
    [ "kernel_options"            , {} ],
    [ "kernel_options_post"       , {} ],
    [ "ks_meta"                   , {} ], 
    [ "interfaces"                , {} ],
    [ "netboot_enabled"           , True ],
    [ "depth"                     , 2 ],
    [ "mgmt_classes"              , [] ],             
    [ "template_files"            , {} ],
    [ "kickstart"                 , "<<inherit>>" ],  # use value in profile
    [ "server"                    , "<<inherit>>" ],  # "" (or settings)
    [ "virt_path"                 , "<<inherit>>" ],  # ""
    [ "virt_type"                 , "<<inherit>>" ],  # "" 
    [ "virt_cpus"                 , "<<inherit>>" ],  # ""
    [ "virt_file_size"            , "<<inherit>>" ],  # ""
    [ "virt_ram"                  , "<<inherit>>" ],  # ""
    [ "virt_auto_boot"            , "<<inherit>>" ],  # ""
    [ "virt_type"                 , "<<inherit>>" ],  # ""
    [ "virt_path"                 , "<<inherit>>" ],  # ""
#   [ "virt_bridge"               , "<<inherit>>" ],  # ""
    [ "virt_host"                 , ""            ],
    [ "virt_group"                , ""            ],  
    [ "virt_guests"               , []            ],
    [ "comment"                   , ""            ],
    [ "ctime"                     , 0             ],
    [ "mtime"                     , 0             ],
    [ "uid"                       , ""            ],
    [ "power_type"                , "SETTINGS:power_management_default_type" ],
    [ "power_address"             , ""            ],
    [ "power_user"                , ""            ],
    [ "power_pass"                , ""            ],
    [ "power_id"                  , ""            ],
    [ "hostname"                  , ""            ],
    [ "gateway"                   , ""            ],
    [ "name_servers"              , []            ],
    [ "name_servers_search"       , []            ],
#   [ "bonding"                   , ""            ],
#   [ "bonding_master"            , ""            ],
#   [ "bonding_opts"              , ""            ],
    [ "redhat_management_key"     , "<<inherit>>" ],
    [ "redhat_management_server"  , "<<inherit>>" ]
]

class System(item.Item):

    TYPE_NAME = _("system")
    COLLECTION_TYPE = "system"

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = System(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def clear(self,is_subobject=False):
        utils.clear_from_fields(self,FIELDS)

    def delete_interface(self,name):
        """
        Used to remove an interface.
        """
        if self.interfaces.has_key(name) and len(self.interfaces) > 1:
            del self.interfaces[name]
        else:
            if not self.interfaces.has_key(name):
                raise CX(_("Cannot delete interface that is not present: %s") % name)
            else:
                raise CX(_("At least one interface needs to be defined."))

        return True
        

    def __get_interface(self,name):

        if not self.interfaces.has_key(name):
            self.interfaces[name] = {
                "mac_address"    : "",
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
                "network"        : "",
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
        elif intf["network"] != "":
            net = self.config.networks().find(name=intf["network"])
            if net == None:
                raise CX(_("Network %s does not exist" % network))
            return net.get_assigned_address(self.name, interface)
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

    def set_network(self,network,interface):
        """
        Add an interface to a network object.  If network is empty,
        clear the network.
        """
        intf = self.__get_interface(interface)

        if network == intf['network']:
            # setting the existing network is no-op
            return

        if intf['network'] != '':
            # we are currently subscribed to a network, so to join
            # a different one we need to leave this one first.
            net = self.config.networks().find(name=intf['network'])
            if net == None:
                raise CX(_("Network %s does not exist" % network))
            net.unsubscribe_system(self.name, interface)
            intf['network'] = ''

        if network != '': # Join
            net  = self.config.networks().find(name=network)
            if net == None:
                raise CX(_("Network %s does not exist" % network))
            net.subscribe_system(self.name, interface, intf['ip_address'])
            intf['network'] = network

        # FIXME figure out why the network collection doesn't
        # serialize itself out to disk without this
        self.config.serialize()

    def set_ip_address(self,address,interface):
        """
        Assign a IP or hostname in DHCP when this MAC boots.
        Only works if manage_dhcp is set in /etc/cobbler/settings
        """
        intf = self.__get_interface(interface)
        if address == "" or utils.is_ip(address):
           intf["ip_address"] = address.strip()
           return True
        raise CX(_("invalid format for IP address (%s)") % address)

    def set_mac_address(self,address,interface):
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

    def set_profile(self,profile_name):
        """
        Set the system to use a certain named profile.  The profile
        must have already been loaded into the Profiles collection.
        """
        if profile_name in [ "delete", "None", "~", ""] or profile_name is None:
            self.profile = ""
            return True

        self.image = "" # mutual exclusion rule

        p = self.config.profiles().find(name=profile_name)
        if p is not None:
            self.profile = profile_name
            self.depth = p.depth + 1 # subprofiles have varying depths.
            return True
        raise CX(_("invalid profile name: %s") % profile_name)

    def set_image(self,image_name):
        """
        Set the system to use a certain named image.  Works like set_profile
        but cannot be used at the same time.  It's one or the other.
        """
        if image_name in [ "delete", "None", "~", ""] or image_name is None:
            self.image = ""
            return True

        self.profile = "" # mutual exclusion rule

        img = self.config.images().find(name=image_name)

        if img is not None:
            self.image = image_name
            self.depth = img.depth + 1
            return True
        raise CX(_("invalid image name (%s)") % image_name)

    def set_virt_cpus(self,num):
        return utils.set_virt_cpus(self,num)

    def set_virt_host(self,host):
        return utils.set_virt_host(self,host)

    def set_virt_group(self,group):
        return utils.set_virt_group(self,group)

    def set_virt_guests(self,guests):
        return utils.set_virt_guests(self,guests)

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


        #self.power_type           = self.settings.power_management_default_type
        #self.power_address        = ""
        #self.power_user           = ""
        #self.power_pass           = ""
        #self.power_id             = ""

    def set_power_type(self, power_type):
        if power_type is None:
            power_type = ""
        power_type = power_type.lower()
        valid = "bullpap wti apc_snmp ether-wake ipmilan drac ipmitool ilo rsa lpar bladecenter virsh integrity none"
        choices = valid.split(" ")
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

    def to_datastruct(self):
        return utils.to_datastruct_from_fields(self,FIELDS)

    def printable(self):
        return utils.printable_from_fields(self,FIELDS)

    def modify_interface(self, hash):
        """
        Used by the WUI to modify an interface more-efficiently
        """
        for (key,value) in hash.iteritems():
            (field,interface) = key.split("-")
            field = field.replace("_","").replace("-","")
            if field == "macaddress"    : self.set_mac_address(value, interface)
            if field == "ipaddress"     : self.set_ip_address(value, interface)
            if field == "dnsname"       : self.set_dns_name(value, interface)
            if field == "static"        : self.set_static(value, interface)
            if field == "dhcptag"       : self.set_dhcp_tag(value, interface)
            if field == "subnet"        : self.set_subnet(value, interface)
            if field == "virtbridge"    : self.set_virt_bridge(value, interface)
            if field == "bonding"       : self.set_bonding(value, interface)
            if field == "bondingmaster" : self.set_bonding_master(value, interface)
            if field == "bondingopts"   : self.set_bonding_opts(value, interface)
            if field == "staticroutes"  : self.set_static_routes(value, interface)
        return True
         

    def remote_methods(self):

        # WARNING: versions with hyphens are old and are in for backwards
        # compatibility.  At some point they may be removed.

        return {
           'name'                     : self.set_name,
           'profile'                  : self.set_profile,
           'image'                    : self.set_image,
           'kopts'                    : self.set_kernel_options,
           'kopts_post'               : self.set_kernel_options_post,           
           'kernel_options'           : self.set_kernel_options,
           'kernel_options_post'      : self.set_kernel_options_post,
           'ksmeta'                   : self.set_ksmeta,
           'ks_meta'                  : self.set_ksmeta,
           'kickstart'                : self.set_kickstart,
           'netboot_enabled'          : self.set_netboot_enabled,           
           'virt_path'                : self.set_virt_path,           
           'virt_type'                : self.set_virt_type,           
           'modify_interface'         : self.modify_interface,           
           'delete_interface'         : self.delete_interface,           
           'virt_path'                : self.set_virt_path,           
           'virt_auto_boot'           : self.set_virt_auto_boot,           
           'virt_ram'                 : self.set_virt_ram,           
           'virt_type'                : self.set_virt_type,           
           'virt_cpus'                : self.set_virt_cpus,           
           'virt-host'                : self.set_virt_host,
           'virt_host'                : self.set_virt_host,           
           'virt_group'               : self.set_virt_group,
           'virt_guests'              : self.set_virt_guests,           
           'virt_file_size'           : self.set_virt_file_size,           
           'server'                   : self.set_server,
           'owners'                   : self.set_owners,
           'mgmt_classes'             : self.set_mgmt_classes,           
           'template_files'           : self.set_template_files,           
           'comment'                  : self.set_comment,
           'power_type'               : self.set_power_type,
           'power_address'            : self.set_power_address,
           'power_user'               : self.set_power_user,
           'power_pass'               : self.set_power_pass,
           'power_id'                 : self.set_power_id,
           'hostname'                 : self.set_hostname,
           'gateway'                  : self.set_gateway,
           'name_servers'             : self.set_name_servers,
           'name_servers_search'      : self.set_name_servers_search,
           'redhat_management_key'    : self.set_redhat_management_key,
           'redhat_management_server' : self.set_redhat_management_server
        }
