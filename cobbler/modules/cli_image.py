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

from utils import _
import commands
import cexceptions


class ImageFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler image","<add|copy|edit|find|list|remove|rename|report> [ARGS|--help]")

    def command_name(self):
        return "image"

    def subcommands(self):
        return [ "add", "copy", "dumpvars", "edit", "find", "list", "remove", "rename", "report" ]

    def add_options(self, p, args):


        if self.matches_args(args,["add"]):
            p.add_option("--clobber", dest="clobber", help="allow add to overwrite existing objects", action="store_true")

        p.add_option("--name",                 dest="name",             help="ex: 'LemurSoft-v3000' (REQUIRED)")
        
        if not self.matches_args(args,["dumpvars","remove","report","list"]):
            p.add_option("--file",             dest="file",             help="common filesystem path to image for all hosts (nfs is good)")

        if self.matches_args(args,["copy","rename"]):

            p.add_option("--newname",          dest="newname",          help="used for copy/edit")

        if not self.matches_args(args,["dumpvars","find","remove","report","list"]):
            # FIXME: there's really nothing to sync here.  Remove?
            p.add_option("--no-sync",     action="store_true", dest="nosync", help="suppress sync for speed")

        if not self.matches_args(args,["dumpvars","find","report","list"]):
            p.add_option("--no-triggers", action="store_true", dest="notriggers", help="suppress trigger execution")
        if not self.matches_args(args,["dumpvars","remove","report","list"]):
            p.add_option("--owners", dest="owners", help="specify owners for authz_ownership module")


    def run(self):

        if "find" in self.args:
            items = self.api.find_image(return_list=True, no_errors=True, **self.options.__dict__)
            for x in items:
                print x.name
            return 0

        obj = self.object_manipulator_start(self.api.new_image,self.api.images)
        if obj is None:
            return True
        if self.matches_args(self.args,["dumpvars"]):
            return self.object_manipulator_finish(obj, self.api.images, self.options)

        if self.options.file:             obj.set_file(self.options.file)

        if self.options.owners:
            obj.set_owners(self.options.owners)

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


