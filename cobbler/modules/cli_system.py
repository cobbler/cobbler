"""
System CLI module.

Copyright 2007-2008, Red Hat, Inc
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

import distutils.sysconfig
import sys

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

import utils
import cobbler.item_system as item_system
import cobbler.commands as commands
from cexceptions import *


class SystemFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler system","<add|copy|edit|find|list|power[off|on]|reboot|rename|remove|report|getks> [ARGS]")

    def command_name(self):
        return "system"

    def subcommands(self):
        return ["add","copy","dumpvars","edit","find","getks","poweroff","poweron","list","reboot","remove","rename","report"]

    def add_options(self, p, args):
        # FIXME: must create per-interface fields also.  Do this manually?
        p.add_option("--interface",dest="interface",help="which interface to add/edit?")
        return utils.add_options_from_fields(p, item_system.FIELDS, args)

    def run(self):
        
        if self.args and "find" in self.args:
            items = self.api.find_system(return_list=True, no_errors=True, **self.options.__dict__)
            for x in items:
                print x.name
            return True

        obj = self.object_manipulator_start(self.api.new_system,self.api.systems)

        if obj is None:
            return True

        if utils.matches_args(self.args,["dumpvars"]):
            return self.object_manipulator_finish(obj, self.api.profiles, self.options)

        if utils.matches_args(self.args,["getks"]):
            return self.object_manipulator_finish(obj, self.api.profiles, self.options)

        # if we haven't said what interface we are editing, it's eth0.
        if self.options.interface:
            my_interface = self.options.interface
        else:
            my_interface = "eth0"
        utils.apply_options_from_fields(obj, item_system.FIELDS, self.options)

        # FIXME: have to handle interfaces too
        #if self.options.dns_name is not None:       
        #    obj.set_dns_name(self.options.dns_name, my_interface)
        #if self.options.mac is not None:
        #    if self.options.mac.lower() == 'random':
        #        obj.set_mac_address(get_random_mac(self.api), my_interface)
        #    else:
        #        obj.set_mac_address(self.options.mac,   my_interface)
        #if self.options.ip is not None:             
        #    obj.set_ip_address(self.options.ip,     my_interface)
        #if self.options.subnet is not None:         
        #    obj.set_subnet(self.options.subnet,     my_interface)
        #if self.options.dhcp_tag is not None:       
        #    obj.set_dhcp_tag(self.options.dhcp_tag, my_interface)
        #if self.options.virt_bridge is not None:    
        #    obj.set_virt_bridge(self.options.virt_bridge, my_interface)
        #if self.options.static is not None:         
        #    obj.set_static(self.options.static,     my_interface)
        #if self.options.bonding is not None:        
        #    obj.set_bonding(self.options.bonding,   my_interface)
        #if self.options.bonding_master is not None: 
        #    obj.set_bonding_master(self.options.bonding_master, my_interface)
        #if self.options.bonding_opts is not None:   
        #    obj.set_bonding_opts(self.options.bonding_opts, my_interface)
        #if self.options.static_routes is not None:  
        #    obj.set_static_routes(self.options.static_routes, my_interface)
        #if self.options.network is not None:
        #    obj.set_network(self.options.network, my_interface)
        
        # FIXME: delete is also special

        #if self.options.delete_interface is not None:
        #    success = obj.delete_interface(self.options.delete_interface)
        #    if not success:
        #        raise CX(_('interface does not exist or is the default interface (%s)') % self.options.delete_interface)

        #if self.options.hostname is not None:     
        #    obj.set_hostname(self.options.hostname)
        #if self.options.gateway is not None:      
        #    obj.set_gateway(self.options.gateway)
        #if self.options.owners is not None:       
        #    obj.set_owners(self.options.owners)
        #if self.options.mgmt_classes is not None: 
        #    obj.set_mgmt_classes(self.options.mgmt_classes)
        #if self.options.template_files is not None: 
        #    obj.set_template_files(self.options.template_files,self.options.inplace)
        #if self.options.name_servers is not None: 
        #    obj.set_name_servers(self.options.name_servers)
        #if self.options.name_servers_search is not None:
        #    obj.set_name_servers_search(self.options.name_servers_search)
        #if self.options.redhat_management_key is not None:
        #    obj.set_redhat_management_key(self.options.redhat_management_key)
        #if self.options.redhat_management_server is not None:
        #    obj.set_redhat_management_server(self.options.redhat_management_server)

        rc = self.object_manipulator_finish(obj, self.api.systems, self.options)

        return rc


########################################################
# MODULE HOOKS

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "cli"

def cli_functions(api):
    return [
       SystemFunction(api)
    ]


