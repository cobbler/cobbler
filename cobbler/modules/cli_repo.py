"""
Repo CLI module.

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


class RepoFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler repo","<add|edit|copy|list|rename|remove|report> [ARGS|--help]")

    def command_name(self):
        return "repo"

    def subcommands(self):
        return [ "add", "edit", "copy", "rename", "remove", "list", "report" ]

    def add_options(self, p, args):

        if not self.matches_args(args,["remove","report","list"]):

            p.add_option("--arch",             dest="arch",             help="overrides repo arch if required")
            p.add_option("--createrepo-flags", dest="createrepo_flags", help="additional flags for createrepo")
            p.add_option("--rpm-list",         dest="rpm_list",         help="just mirror these rpms")
            p.add_option("--keep-updated",     dest="keep_updated",     help="update on each reposync, yes/no")
            p.add_option("--priority",         dest="priority",         help="set priority") 
            p.add_option("--mirror",           dest="mirror",           help="source to mirror (REQUIRED)")

        p.add_option("--name",                 dest="name",             help="ex: 'Fedora-8-updates-i386' (REQUIRED)")

        if self.matches_args(args,["copy","rename"]):

            p.add_option("--newname",          dest="newname",          help="used for copy/edit")

    def run(self):

        obj = self.object_manipulator_start(self.api.new_repo,self.api.repos)
        if obj is None:
            return True

        if self.options.arch:             obj.set_arch(self.options.arch)
        if self.options.createrepo_flags: obj.set_createrepo_flags(self.options.createrepo_flags)
        if self.options.rpm_list:         obj.set_rpm_list(self.options.rpm_list)
        if self.options.keep_updated:     obj.set_keep_updated(self.options.keep_updated)
        if self.options.priority:         obj.set_priority(self.options.priority)
        if self.options.mirror:           obj.set_mirror(self.options.mirror)

        return self.object_manipulator_finish(obj, self.api.repos)



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


