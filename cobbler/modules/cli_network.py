"""
Network CLI module.

Copyright 2009, Red Hat, Inc
John Eckersberg <jeckersb@redhat.com>

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

from utils import _, _IP, _CIDR
import utils
import cobbler.commands as commands
from cexceptions import *
import cobbler.item_network as item_network

class NetworkFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler network","<add|copy|edit|find|list|remove|rename|report> [ARGS]")

    def command_name(self):
        return "network"

    def subcommands(self):
        return [ "add", "copy", "dumpvars", "edit", "find", "list", "remove", "rename", "report" ]

    def add_options(self, p, args):
        return utils.add_options_from_fields(p, item_network.FIELDS, args)

    def run(self):
        if self.args and "find" in self.args:
            items = self.api.find_network(return_list=True, no_errors=True, **self.options.__dict__)
            for x in items:
                print x.name
            return True

        obj = self.object_manipulator_start(self.api.new_network,self.api.networks)
        if obj is None:
            return True
        if utils.matches_args(self.args,["dumpvars"]):
            return self.object_manipulator_finish(obj, self.api.profiles, self.options)

        # FIXME: for all objects, ensure that the objects we save are completed
        # given that we no longer use is_valid

        utils.apply_options_from_fields(obj, item_network.FIELDS, self.options)

        return self.object_manipulator_finish(obj, self.api.networks, self.options)



########################################################
# MODULE HOOKS

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "cli"

def cli_functions(api):
    return [
       NetworkFunction(api)
    ]
    return []
