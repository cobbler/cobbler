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

from utils import _
import commands
import cexceptions


class RepoFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler repo","<add|copy|edit|find|list|remove|rename|report> [ARGS|--help]")

    def command_name(self):
        return "repo"

    def subcommands(self):
        return [ "add", "copy", "dumpvars", "edit", "find", "list", "remove", "rename", "report" ]

    def add_options(self, p, args):


        if not self.matches_args(args,["dumpvars","remove","report","list"]):
            p.add_option("--breed",             dest="breed",             help="sets the breed of the repo")
            p.add_option("--arch",             dest="arch",             help="overrides repo arch if required")
        if self.matches_args(args,["add"]):
            p.add_option("--clobber", dest="clobber", help="allow add to overwrite existing objects", action="store_true")
        if not self.matches_args(args,["dumpvars","remove","report","list"]):
            p.add_option("--createrepo-flags", dest="createrepo_flags", help="additional flags for createrepo")
            p.add_option("--keep-updated",     dest="keep_updated",     help="update on each reposync, yes/no")

        p.add_option("--name",                 dest="name",             help="ex: 'Fedora-8-updates-i386' (REQUIRED)")
        
        if not self.matches_args(args,["dumpvars","remove","report","list"]):
            p.add_option("--mirror",           dest="mirror",           help="source to mirror (REQUIRED)")
            p.add_option("--mirror-locally",   dest="mirror_locally",   help="mirror or use external directly? (default 1)")
            p.add_option("--priority",         dest="priority",         help="set priority") 
            p.add_option("--rpm-list",         dest="rpm_list",         help="just mirror these rpms")
            p.add_option("--yumopts",          dest="yumopts",          help="ex: pluginvar=abcd")

            if not self.matches_args(args, ["find"]):
                p.add_option("--in-place", action="store_true", default=False, dest="inplace", help="edit items in yumopts without clearing the other items")

        if self.matches_args(args,["copy","rename"]):
            p.add_option("--newname",          dest="newname",          help="used for copy/edit")

        if not self.matches_args(args,["dumpvars","find","remove","report","list"]):
            p.add_option("--no-sync",     action="store_true", dest="nosync", help="suppress sync for speed")
        if not self.matches_args(args,["dumpvars","find","report","list"]):
            p.add_option("--no-triggers", action="store_true", dest="notriggers", help="suppress trigger execution")
        if not self.matches_args(args,["dumpvars","remove","report","list"]):
            p.add_option("--owners", dest="owners", help="specify owners for authz_ownership module")


    def run(self):

        if self.args and "find" in self.args:
            items = self.api.find_system(return_list=True, no_errors=True, **self.options.__dict__)
            for x in items:
                print x.name
            return True

        obj = self.object_manipulator_start(self.api.new_repo,self.api.repos)
        if obj is None:
            return True
        if self.matches_args(self.args,["dumpvars"]):
            return self.object_manipulator_finish(obj, self.api.profiles, self.options)

        if self.options.breed:            obj.set_breed(self.options.breed)
        if self.options.arch:             obj.set_arch(self.options.arch)
        if self.options.createrepo_flags: obj.set_createrepo_flags(self.options.createrepo_flags)
        if self.options.rpm_list:         obj.set_rpm_list(self.options.rpm_list)
        if self.options.keep_updated:     obj.set_keep_updated(self.options.keep_updated)
        if self.options.priority:         obj.set_priority(self.options.priority)
        if self.options.mirror:           obj.set_mirror(self.options.mirror)
        if self.options.mirror_locally:   obj.set_mirror_locally(self.options.mirror_locally)
        if self.options.yumopts:          obj.set_yumopts(self.options.yumopts,self.options.inplace)

        if self.options.owners:
            obj.set_owners(self.options.owners)

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


