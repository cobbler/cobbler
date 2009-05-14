"""
Profile CLI module.

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
import cobbler.item_profile as item_profile
import cobbler.commands as commands
import cexceptions



class ProfileFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler profile","<add|copy|edit|find|getks|list|rename|remove|report> [ARGS]")

    def command_name(self):
        return "profile"

    def subcommands(self):
        return ["add","copy","dumpvars","edit","find","getks","list","remove","rename","report"]

    def add_options(self, p, args):
        return utils.add_options_from_fields(p, item_profile.FIELDS, args)

    def run(self):

        if self.args and "find" in self.args:
            items = self.api.find_profile(return_list=True, no_errors=True, **self.options.__dict__)
            for x in items:
                print x.name
            return True

        if self.matches_args(self.args,["report","getks","list","remove","dumpvars"]) or not self.options.inherit:
            obj = self.object_manipulator_start(self.api.new_profile,self.api.profiles,subobject=False)
        else:
            obj = self.object_manipulator_start(self.api.new_profile,self.api.profiles,subobject=True)

        if obj is None:
            return True

        if not self.matches_args(self.args,["dumpvars","getks"]):
            if self.options.comment is not None:         
                obj.set_comment(self.options.comment)
            if self.options.inherit is not None:         
                obj.set_parent(self.options.inherit)
            if self.options.distro is not None:          
                obj.set_distro(self.options.distro)
            if self.options.enable_menu is not None:
                obj.set_enable_menu(self.options.enable_menu)
            if self.options.kickstart is not None:       
                obj.set_kickstart(self.options.kickstart)
            if self.options.kopts is not None:           
                obj.set_kernel_options(self.options.kopts,self.options.inplace)
            if self.options.kopts_post is not None:      
                obj.set_kernel_options_post(self.options.kopts_post,self.options.inplace)
            if self.options.ksmeta is not None:          
                obj.set_ks_meta(self.options.ksmeta,self.options.inplace)
            if self.options.virt_auto_boot is not None:
                obj.set_virt_auto_boot(self.options.virt_auto_boot)
            if self.options.virt_file_size is not None:  
                obj.set_virt_file_size(self.options.virt_file_size)
            if self.options.virt_ram is not None:        
                obj.set_virt_ram(self.options.virt_ram)
            if self.options.virt_bridge is not None:     
                obj.set_virt_bridge(self.options.virt_bridge)
            if self.options.virt_type is not None:       
                obj.set_virt_type(self.options.virt_type)
            if self.options.virt_cpus is not None:       
                obj.set_virt_cpus(self.options.virt_cpus)
            if self.options.repos is not None:           
                obj.set_repos(self.options.repos)
            if self.options.virt_path is not None:       
                obj.set_virt_path(self.options.virt_path)
            if self.options.dhcp_tag is not None:        
                obj.set_dhcp_tag(self.options.dhcp_tag)
            if self.options.server_override is not None: 
                obj.set_server(self.options.server_overide)

            if self.options.owners is not None:          
                obj.set_owners(self.options.owners)
            if self.options.mgmt_classes is not None:    
                obj.set_mgmt_classes(self.options.mgmt_classes)
            if self.options.template_files is not None:  
                obj.set_template_files(self.options.template_files,self.options.inplace)
            if self.options.name_servers is not None:    
                obj.set_name_servers(self.options.name_servers)
            if self.options.name_servers_search is not None:
                obj.set_name_servers_search(self.options.name_servers_search)
            if self.options.redhat_management_key is not None:
                obj.set_redhat_management_key(self.options.redhat_management_key)
            if self.options.redhat_management_server is not None:
                obj.set_redhat_management_server(self.options.redhat_management_server)


        return self.object_manipulator_finish(obj, self.api.profiles, self.options)



########################################################
# MODULE HOOKS

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "cli"

def cli_functions(api):
    return [
       ProfileFunction(api)
    ]


