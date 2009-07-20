"""
Distro CLI module.

Copyright 2007-2009, Red Hat, Inc
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

import cobbler.commands as commands
import cexceptions
import cobbler.item_distro as item_distro
import utils

class DistroFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler distro", "<add|copy|edit|find|list|rename|remove|report> [ARGS]")

    def command_name(self):
        return "distro"

    def subcommands(self):
        return [ "add", "copy", "dumpvars", "edit", "find", "list", "remove", "rename", "report" ]

    def add_options(self, p, args):
        utils.add_options_from_fields(p, item_distro.FIELDS, args)
        return True

    def run(self):

        if self.args and "find" in self.args:
            items = utils.cli_find_via_xmlrpc(self.remote, "distro", self.options)
            for x in items:
                print x.name
            return True

        obj = self.object_manipulator_start(self.api.new_distro,self.api.distros)
        if obj is None:
            return True

        # FIXME: inplace is not handled.  Do we need to retain this?

        if not "dumpvars" in self.args:
            utils.apply_options_from_fields(obj, item_distro.FIELDS, self.options)

            #if self.options.comment is not None:
            #    obj.set_comment(self.options.comment)
            #if self.options.arch is not None:
            #    obj.set_arch(self.options.arch)
            #if self.options.kernel is not None:
            #    obj.set_kernel(self.options.kernel)
            #if self.options.initrd is not None:
            #    obj.set_initrd(self.options.initrd)
            #if self.options.kopts is not None:
            #    obj.set_kernel_options(self.options.kopts,self.options.inplace)
            #if self.options.kopts_post is not None:
            #    obj.set_kernel_options_post(self.options.kopts_post,self.options.inplace)
            #if self.options.ksmeta is not None:
            #    obj.set_ks_meta(self.options.ksmeta,self.options.inplace)
            #if self.options.breed is not None:
            #    obj.set_breed(self.options.breed)
            #if self.options.os_version is not None:
            #    obj.set_os_version(self.options.os_version)
            #if self.options.owners is not None:
            #    obj.set_owners(self.options.owners)
            #if self.options.mgmt_classes is not None:
            #    obj.set_mgmt_classes(self.options.mgmt_classes)
            #if self.options.template_files is not None:
            #    obj.set_template_files(self.options.template_files,self.options.inplace)
            #if self.options.redhat_management_key is not None:
            #    obj.set_redhat_management_key(self.options.redhat_management_key)
            #if self.options.redhat_management_server is not None:
            #    obj.set_redhat_management_server(self.options.redhat_management_server)

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


