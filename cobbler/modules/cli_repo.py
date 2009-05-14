"""
Repo CLI module.

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

import cobbler.commands as commands
import cexceptions
import utils
import cobbler.item_repo as item_repo

class RepoFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler repo","<add|copy|edit|find|list|remove|rename|report> [ARGS]")

    def command_name(self):
        return "repo"

    def subcommands(self):
        return [ "add", "copy", "dumpvars", "edit", "find", "list", "remove", "rename", "report" ]

    def add_options(self, p, args):
        return utils.add_options_from_fields(p, item_repo.FIELDS, args)

    def run(self):

        if self.args and "find" in self.args:
            items = self.api.find_repo(return_list=True, no_errors=True, **self.options.__dict__)
            for x in items:
                print x.name
            return True

        obj = self.object_manipulator_start(self.api.new_repo,self.api.repos)
        if obj is None:
            return True
        if self.matches_args(self.args,["dumpvars"]):
            return self.object_manipulator_finish(obj, self.api.profiles, self.options)

        if self.options.breed is not None:            
            obj.set_breed(self.options.breed)
        if self.options.os_version is not None:            
            obj.set_os_version(self.options.os_version)
        if self.options.arch is not None:             
            obj.set_arch(self.options.arch)
        if self.options.createrepo_flags is not None: 
            obj.set_createrepo_flags(self.options.createrepo_flags)
        if self.options.environment is not None:      
            obj.set_environment(self.options.environment)
        if self.options.rpm_list is not None:         
            obj.set_rpm_list(self.options.rpm_list)
        if self.options.keep_updated is not None:     
            obj.set_keep_updated(self.options.keep_updated)
        if self.options.priority is not None:         
            obj.set_priority(self.options.priority)
        if self.options.mirror is not None:           
            obj.set_mirror(self.options.mirror)
        if self.options.mirror_locally is not None:   
            obj.set_mirror_locally(self.options.mirror_locally)
        if self.options.yumopts is not None:          
            obj.set_yumopts(self.options.yumopts,self.options.inplace)
        if self.options.owners is not None:           
            obj.set_owners(self.options.owners)
        if self.options.comment is not None:          
            obj.set_comment(self.options.comment)

        return self.object_manipulator_finish(obj, self.api.repos, self.options)



########################################################
# MODULE HOOKS

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "cli"

def cli_functions(api):
    return [
       RepoFunction(api)
    ]
    return []


