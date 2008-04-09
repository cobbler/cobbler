"""
Distro CLI module.

Copyright 2007, Red Hat, Inc
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


class DistroFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler distro", "<add|edit|copy|list|rename|remove|report> [ARGS|--help]")

    def command_name(self):
        return "distro"

    def subcommands(self):
        return [ "add", "edit", "copy", "rename", "remove", "list", "report" ]

    def add_options(self, p, args):

        if not self.matches_args(args,["remove","report","list"]):
            p.add_option("--arch",   dest="arch",   help="ex: x86, x86_64, ia64")
            p.add_option("--breed",  dest="breed",  help="ex: redhat, debian, suse")
        if self.matches_args(args,["add"]):
            p.add_option("--clobber", dest="clobber", help="allow add to overwrite existing objects", action="store_true")
        if not self.matches_args(args,["remove","report","list"]):
            p.add_option("--initrd", dest="initrd", help="absolute path to initrd.img (REQUIRED)")
            p.add_option("--kernel", dest="kernel", help="absolute path to vmlinuz (REQUIRED)")
            p.add_option("--kopts",  dest="kopts",  help="ex: 'noipv6'")
            p.add_option("--ksmeta", dest="ksmeta", help="ex: 'blippy=7'")

        p.add_option("--name",   dest="name", help="ex: 'RHEL-5-i386' (REQUIRED)")



        if self.matches_args(args,["copy","rename"]):
            p.add_option("--newname", dest="newname", help="for copy/rename commands")
        if not self.matches_args(args,["remove","report","list"]):
            p.add_option("--no-sync",     action="store_true", dest="nosync", help="suppress sync for speed")
        if not self.matches_args(args,["report","list"]):
            p.add_option("--no-triggers", action="store_true", dest="notriggers", help="suppress trigger execution")
        if not self.matches_args(args,["remove","report","list"]):
            p.add_option("--owners", dest="owners", help="specify owners for authz_ownership module")

        if self.matches_args(args,["remove"]):
            p.add_option("--recursive", action="store_true", dest="recursive", help="also delete child objects")

    def run(self):

        obj = self.object_manipulator_start(self.api.new_distro,self.api.distros)
        if obj is None:
            return True

        if self.options.kernel:
            obj.set_kernel(self.options.kernel)
        if self.options.initrd:
            obj.set_initrd(self.options.initrd)
        if self.options.kopts:
            obj.set_kernel_options(self.options.kopts)
        if self.options.ksmeta:
            obj.set_ksmeta(self.options.ksmeta)
        if self.options.breed:
            obj.set_breed(self.options.breed)
        if self.options.owners:
            obj.set_owners(self.options.owners)

        return self.object_manipulator_finish(obj, self.api.distros, self.options)



########################################################
# MODULE HOOKS

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "cli"

def cli_functions(api):
    return [
       DistroFunction(api)
    ]


