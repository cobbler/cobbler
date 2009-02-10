"""
Distro CLI module.

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
import cobbler.commands as commands
import cexceptions


class DistroFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler distro", "<add|copy|edit|find|list|rename|remove|report> [ARGS]")

    def command_name(self):
        return "distro"

    def subcommands(self):
        return [ "add", "copy", "dumpvars", "edit", "find", "list", "remove", "rename", "report" ]

    def add_options(self, p, args):

        if not self.matches_args(args,["dumpvars","remove","report","list"]):
            p.add_option("--arch",     dest="arch",     help="ex: x86, x86_64, ia64")
            p.add_option("--breed",    dest="breed",    help="ex: redhat, debian, suse")
        if self.matches_args(args,["add"]):
            p.add_option("--clobber", dest="clobber", help="allow add to overwrite existing objects", action="store_true")
        if not self.matches_args(args,["dumpvars","remove","report","list"]):
            p.add_option("--comment",  dest="comment",  help="user field")
            p.add_option("--initrd",      dest="initrd",      help="absolute path to initrd.img (REQUIRED)")
            if not self.matches_args(args,["find"]): 
                p.add_option("--in-place", action="store_true", default=False, dest="inplace", help="edit items in kopts or ksmeta without clearing the other items")
            p.add_option("--kernel",       dest="kernel",      help="absolute path to vmlinuz (REQUIRED)")
            p.add_option("--kopts",        dest="kopts",       help="ex: 'noipv6'")
            p.add_option("--kopts-post",   dest="kopts_post",  help="ex: 'clocksource=pit'")
            p.add_option("--ksmeta",       dest="ksmeta",      help="ex: 'blippy=7'")
            p.add_option("--mgmt-classes", dest="mgmt_classes",  help="list of config management classes (for Puppet, etc)")
            p.add_option("--redhat-management-key", dest="redhat_management_key", help="authentication token for RHN/Spacewalk/Satellite")
            p.add_option("--template-files", dest="template_files", help="specify files to be generated from templates during a sync")

        p.add_option("--name",   dest="name", help="ex: 'RHEL-5-i386' (REQUIRED)")
        if not self.matches_args(args,["dumpvars","remove","report","list"]):
            p.add_option("--os-version",  dest="os_version",  help="ex: rhel4, fedora9")

        if self.matches_args(args,["copy","rename"]):
            p.add_option("--newname", dest="newname", help="for copy/rename commands")
        if not self.matches_args(args,["dumpvars","find","remove","report","list"]):
            p.add_option("--no-sync",     action="store_true", dest="nosync", help="suppress sync for speed")
        if not self.matches_args(args,["dumpvars","report","list"]):
            p.add_option("--no-triggers", action="store_true", dest="notriggers", help="suppress trigger execution")
        if not self.matches_args(args,["dumpvars","remove","report","list"]):
            p.add_option("--owners", dest="owners", help="specify owners for authz_ownership module")

        if self.matches_args(args,["remove"]):
            p.add_option("--recursive", action="store_true", dest="recursive", help="also delete child objects")

    def run(self):

        if self.args and "find" in self.args:
            items = self.api.find_distro(return_list=True, no_errors=True, **self.options.__dict__)
            for x in items:
                print x.name
            return True

        obj = self.object_manipulator_start(self.api.new_distro,self.api.distros)
        if obj is None:
            return True

        if not "dumpvars" in self.args:
            if self.options.comment is not None:
                obj.set_comment(self.options.comment)
            if self.options.arch is not None:
                obj.set_arch(self.options.arch)
            if self.options.kernel is not None:
                obj.set_kernel(self.options.kernel)
            if self.options.initrd is not None:
                obj.set_initrd(self.options.initrd)
            if self.options.kopts is not None:
                obj.set_kernel_options(self.options.kopts,self.options.inplace)
            if self.options.kopts_post is not None:
                obj.set_kernel_options_post(self.options.kopts_post,self.options.inplace)
            if self.options.ksmeta is not None:
                obj.set_ksmeta(self.options.ksmeta,self.options.inplace)
            if self.options.breed is not None:
                obj.set_breed(self.options.breed)
            if self.options.os_version is not None:
                obj.set_os_version(self.options.os_version)
            if self.options.owners is not None:
                obj.set_owners(self.options.owners)
            if self.options.mgmt_classes is not None:
                obj.set_mgmt_classes(self.options.mgmt_classes)
            if self.options.template_files is not None:
                obj.set_template_files(self.options.template_files,self.options.inplace)
            if self.options.redhat_management_key is not None:
                obj.set_redhat_management_key(self.options.redhat_management_key)

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


