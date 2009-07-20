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
        utils.add_options_from_fields(p, item_profile.FIELDS, args)
        p.add_option("--inherit",dest="inherit",help="parent for subprofile")
        return True 

    def run(self):

        if self.args and "find" in self.args:
            items = self.api.find_profile(return_list=True, no_errors=True, **self.options.__dict__)
            for x in items:
                print x.name
            return True

        if utils.matches_args(self.args,["report","getks","list","remove","dumpvars"]) or not self.options.inherit:
            obj = self.object_manipulator_start(self.api.new_profile,self.api.profiles,subobject=False)
        else:
            obj = self.object_manipulator_start(self.api.new_profile,self.api.profiles,subobject=True)

        if obj is None:
            return True

        if not utils.matches_args(self.args,["dumpvars","getks"]):
            utils.apply_options_from_fields(obj, item_profile.FIELDS, self.options)


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


