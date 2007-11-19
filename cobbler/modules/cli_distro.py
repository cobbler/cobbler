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

from rhpl.translate import _, N_, textdomain, utf8
import commands
import cexceptions


class DistroFunction(commands.CobblerFunction):

    def command_name(self):
        return "distro"

    def subcommands(self):
        return [ "add", "edit", "copy", "rename", "delete" ]

    def add_options(self, p, args):
        p.add_option("--name",   dest="name")
        if not "delete" in args:
            p.add_option("--kernel", dest="kernel")
            p.add_option("--initrd", dest="initrd")
            p.add_option("--kopts",  dest="kopts")
            p.add_option("--ksmeta", dest="ksmeta")
            p.add_option("--arch",   dest="arch")
            p.add_option("--breed",  dest="breed")
        if "copy" in args or "rename" in args:
            p.add_option("--newname", dest="newname")

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

        return self.object_manipulator_finish(obj, self.api.distros)



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


