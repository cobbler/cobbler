"""
System CLI module.

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


class SystemFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler system","<add|edit|copy|list|rename|remove|report> [ARGS|--help]")

    def command_name(self):
        return "system"

    def subcommands(self):
        return [ "add", "edit", "copy", "rename", "remove", "report", "list" ]

    def add_options(self, p, args):

        if not self.matches_args(args,["remove","report","list"]):
            p.add_option("--dhcp-tag",        dest="dhcp_tag",    help="for use in advanced DHCP configurations")
            p.add_option("--gateway",         dest="gateway",     help="for static IP / templating usage")
            p.add_option("--hostname",        dest="hostname",    help="ex: server.example.org")
            p.add_option("--interface",       dest="interface",   help="edit this interface # (0-7, default 0)")
            p.add_option("--ip",              dest="ip",          help="ex: 192.168.1.55, (RECOMMENDED)")
            p.add_option("--kickstart",       dest="kickstart",   help="override profile kickstart template")
            p.add_option("--kopts",           dest="kopts",       help="ex: 'noipv6'")
            p.add_option("--ksmeta",          dest="ksmeta",      help="ex: 'blippy=7'")
            p.add_option("--mac",             dest="mac",         help="ex: 'AA:BB:CC:DD:EE:FF', (RECOMMENDED)")

        p.add_option("--name",   dest="name",                     help="a name for the system (REQUIRED)")

        if not self.matches_args(args,["remove","report","list"]):
            p.add_option("--netboot-enabled", dest="netboot_enabled", help="PXE on (1) or off (0)")

        if self.matches_args(args,["copy","rename"]):
            p.add_option("--newname", dest="newname",                 help="for use with copy/edit")

        if not self.matches_args(args,["remove","report","list"]):
            p.add_option("--no-sync",     action="store_true", dest="nosync", help="suppress sync for speed")
        if not self.matches_args(args,["report","list"]):
            p.add_option("--no-triggers", action="store_true", dest="notriggers", help="suppress trigger execution")


        if not self.matches_args(args,["remove","report","list"]):
            p.add_option("--owners",          dest="owners",          help="specify owners for authz_ownership module")
            p.add_option("--profile",         dest="profile",         help="name of cobbler profile (REQUIRED)")
            p.add_option("--server-override", dest="server_override", help="overrides server value in settings file")
            p.add_option("--subnet",          dest="subnet",          help="for static IP / templating usage")
            p.add_option("--virt-bridge",     dest="virt_bridge",     help="ex: virbr0")
            p.add_option("--virt-path",       dest="virt_path",       help="path, partition, or volume")
            p.add_option("--virt-type",       dest="virt_type",       help="ex: xenpv, qemu, xenfv")


    def run(self):

        obj = self.object_manipulator_start(self.api.new_system,self.api.systems)
        if obj is None:
            return True

        if self.options.profile:         obj.set_profile(self.options.profile)
        if self.options.kopts:           obj.set_kernel_options(self.options.kopts)
        if self.options.ksmeta:          obj.set_ksmeta(self.options.ksmeta)
        if self.options.kickstart:       obj.set_kickstart(self.options.kickstart)
        if self.options.netboot_enabled: obj.set_netboot_enabled(self.options.netboot_enabled)
        if self.options.server_override: obj.set_server(self.options.server_override)
        if self.options.virt_path:       obj.set_virt_path(self.options.virt_path)
        if self.options.virt_type:       obj.set_virt_type(self.options.virt_type)

        if self.options.interface:
            my_interface = "intf%s" % self.options.interface
        else:
            my_interface = "intf0"

        if self.options.hostname:    obj.set_hostname(self.options.hostname, my_interface)
        if self.options.mac:         obj.set_mac_address(self.options.mac,   my_interface)
        if self.options.ip:          obj.set_ip_address(self.options.ip,     my_interface)
        if self.options.subnet:      obj.set_subnet(self.options.subnet,     my_interface)
        if self.options.gateway:     obj.set_gateway(self.options.gateway,   my_interface)
        if self.options.dhcp_tag:    obj.set_dhcp_tag(self.options.dhcp_tag, my_interface)
        if self.options.virt_bridge: obj.set_virt_bridge(self.options.virt_bridge, my_interface)

        if self.options.owners:
            obj.set_owners(self.options.owners)

        rc = self.object_manipulator_finish(obj, self.api.systems, self.options)

        if ["copy"] in self.args:
           # run through and find conflicts       
           print _("WARNING: after copying systems, be sure that the ip/mac information is unique").

        return rc


########################################################
# MODULE HOOKS

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "cli"

def cli_functions(api):
    return [
       SystemFunction(api)
    ]


