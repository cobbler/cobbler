"""
Profile CLI module.

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


class ProfileFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler profile","<add|copy|edit|find|list|rename|remove|report> [ARGS|--help]")

    def command_name(self):
        return "profile"

    def subcommands(self):
        return [ "add", "copy", "dumpvars", "edit", "find", "list", "remove", "rename", "report" ]

    def add_options(self, p, args):

        if self.matches_args(args,["add"]):
            p.add_option("--clobber", dest="clobber", help="allow add to overwrite existing objects", action="store_true")


        if not self.matches_args(args,["dumpvars","remove","report","list"]):

            p.add_option("--distro",           dest="distro", help="ex: 'RHEL-5-i386' (REQUIRED)")
            p.add_option("--dhcp-tag",         dest="dhcp_tag", help="for use in advanced DHCP configuration")
            p.add_option("--inherit",          dest="inherit", help="inherit from this profile name, defaults to no")
            p.add_option("--kickstart",        dest="kickstart", help="absolute path to kickstart template (RECOMMENDED)")
            p.add_option("--ksmeta",           dest="ksmeta", help="ex: 'blippy=7'")
            p.add_option("--kopts",            dest="kopts", help="ex: 'noipv6'")
            if not self.matches_args(args,["find"]):
                p.add_option("--in-place",action="store_true", dest="inplace", default=False, help="edit items in kopts or ksmeta without clearing the other items")

        p.add_option("--name",   dest="name",  help="a name for the profile (REQUIRED)")


        if "copy" in args or "rename" in args:
            p.add_option("--newname", dest="newname")

        if not self.matches_args(args,["dumpvars","find","remove","report", "list"]):
            p.add_option("--no-sync",     action="store_true", dest="nosync", help="suppress sync for speed")
        if not self.matches_args(args,["dumpvars","find","report", "list"]):
            p.add_option("--no-triggers", action="store_true", dest="notriggers", help="suppress trigger execution")
        if not self.matches_args(args,["dumpvars","report", "list"]):
            p.add_option("--owners", dest="owners", help="specify owners for authz_ownership module")

        if self.matches_args(args,["remove"]):
            p.add_option("--recursive", action="store_true", dest="recursive", help="also delete child objects")

        if not self.matches_args(args,["dumpvars","remove","report","list"]):
            p.add_option("--repos",            dest="repos", help="names of cobbler repos")
            p.add_option("--server-override",  dest="server_override", help="overrides value in settings file")
            p.add_option("--virt-bridge",      dest="virt_bridge", help="ex: 'virbr0'")
            p.add_option("--virt-cpus",        dest="virt_cpus", help="integer (default: 1)")
            p.add_option("--virt-file-size",   dest="virt_file_size", help="size in GB")
            p.add_option("--virt-path",        dest="virt_path", help="path, partition, or volume")
            p.add_option("--virt-ram",         dest="virt_ram", help="size in MB")
            p.add_option("--virt-type",        dest="virt_type", help="ex: 'xenpv', 'qemu'")

    def run(self):

        if "find" in self.args:
            items = self.api.find_profile(return_list=True, no_errors=True, **self.options.__dict__)
            for x in items:
                print x.name
            return 0

        if self.matches_args(self.args,["report","list","remove","dumpvars"]) or not self.options.inherit:
            obj = self.object_manipulator_start(self.api.new_profile,self.api.profiles,subobject=False)
        else:
            obj = self.object_manipulator_start(self.api.new_profile,self.api.profiles,subobject=True)

        if obj is None:
            return True

        if not self.matches_args(self.args,["dumpvars"]):
            if self.options.inherit:         obj.set_parent(self.options.inherit)
            if self.options.distro:          obj.set_distro(self.options.distro)
            if self.options.kickstart:       obj.set_kickstart(self.options.kickstart)
            if self.options.kopts:           obj.set_kernel_options(self.options.kopts,self.options.inplace)
            if self.options.ksmeta:          obj.set_ksmeta(self.options.ksmeta,self.options.inplace)
            if self.options.virt_file_size:  obj.set_virt_file_size(self.options.virt_file_size)
            if self.options.virt_ram:        obj.set_virt_ram(self.options.virt_ram)
            if self.options.virt_bridge:     obj.set_virt_bridge(self.options.virt_bridge)
            if self.options.virt_type:       obj.set_virt_type(self.options.virt_type)
            if self.options.virt_cpus:       obj.set_virt_cpus(self.options.virt_cpus)
            if self.options.repos:           obj.set_repos(self.options.repos)
            if self.options.virt_path:       obj.set_virt_path(self.options.virt_path)
            if self.options.dhcp_tag:        obj.set_dhcp_tag(self.options.dhcp_tag)
            if self.options.server_override: obj.set_server(self.options.server)

            if self.options.owners:          obj.set_owners(self.options.owners)

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


