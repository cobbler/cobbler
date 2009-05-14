"""
Image CLI module.

Copyright 2007-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import distutils.sysconfig
import sys

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

import utils
import cobbler.item_image as item_image
import cobbler.commands as commands
import cexceptions


class ImageFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler image","<add|copy|edit|find|list|remove|rename|report> [ARGS]")

    def command_name(self):
        return "image"

    def subcommands(self):
        return [ "add", "copy", "dumpvars", "edit", "find", "list", "remove", "rename", "report" ]

    def add_options(self, p, args):
        return utils.add_options_from_fields(p, item_image.FIELDS, args)

    def run(self):

        if self.args and "find" in self.args:
            items = self.api.find_image(return_list=True, no_errors=True, **self.options.__dict__)
            for x in items:
                print x.name
            return True

        obj = self.object_manipulator_start(self.api.new_image,self.api.images)
        if obj is None:
            return True
        if self.matches_args(self.args,["dumpvars"]):
            return self.object_manipulator_finish(obj, self.api.images, self.options)

        if self.options.comment is not None: 
            obj.set_comment(self.options.comment)
        if self.options.file is not None:             
            obj.set_file(self.options.file)
        if self.options.image_type is not None:       
            obj.set_image_type(self.options.image_type)
        if self.options.owners is not None:           
            obj.set_owners(self.options.owners)
        if self.options.virt_bridge is not None:      
            obj.set_virt_bridge(self.options.virt_bridge)
        if self.options.virt_path is not None:        
            obj.set_virt_path(self.options.virt_path)
        if self.options.virt_file_size is not None:   
            obj.set_virt_file_size(self.options.virt_file_size)
        if self.options.virt_bridge is not None:      
            obj.set_virt_bridge(self.options.virt_bridge)
        if self.options.virt_cpus is not None:        
            obj.set_virt_cpus(self.options.virt_cpus)
        if self.options.virt_ram is not None:         
            obj.set_virt_ram(self.options.virt_ram)
        if self.options.virt_type is not None:        
            obj.set_virt_type(self.options.virt_type)
        if self.options.breed is not None:            
            obj.set_breed(self.options.breed)
        if self.options.arch is not None:             
            obj.set_arch(self.options.arch)
        if self.options.os_version is not None:       
            obj.set_os_version(self.options.os_version)
        if self.options.kickstart is not None:
            obj.set_kickstart(self.options.kickstart)
 
        return self.object_manipulator_finish(obj, self.api.images, self.options)



########################################################
# MODULE HOOKS

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "cli"

def cli_functions(api):
    return [
       ImageFunction(api)
    ]
    return []


