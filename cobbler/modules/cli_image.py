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
        if utils.matches_args(self.args,["dumpvars"]):
            return self.object_manipulator_finish(obj, self.api.images, self.options)

        utils.apply_options_from_fields(obj, item_image.FIELDS, self.options)

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


