"""
System CLI module.

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

from utils import _, get_random_mac
import commands
from cexceptions import *


class SystemFunction(commands.CobblerFunction):

    def help_me(self):
        return commands.HELP_FORMAT % ("cobbler system","<add|copy|edit|find|list|poweroff|poweron|reboot|rename|remove|report|getks> [ARGS|--help]")

    def command_name(self):
        return "system"

    def subcommands(self):
        return ["add","copy","dumpvars","edit","find","poweroff","poweron","list","reboot""remove","rename","report","getks"]

    def add_options(self, p, args):

        if not self.matches_args(args,["dumpvars","poweron","poweroff","reboot","remove","report","getks","list"]):
            p.add_option("--bonding",         dest="bonding",       help="NIC bonding, ex: master, slave, none (default)")
            p.add_option("--bonding-master",  dest="bonding_master",metavar="INTERFACE", help="master interface for this slave, ex: bond0")
            p.add_option("--bonding-opts",    dest="bonding_opts",  help="ex: 'miimon=100'")
            p.add_option("--comment", dest="comment", help="user field")

        if self.matches_args(args,["add"]):
            p.add_option("--clobber", dest="clobber", help="allow add to overwrite existing objects", action="store_true")

        if not self.matches_args(args,["dumpvars","poweron","poweroff","reboot","remove","report","getks","list"]):
            p.add_option("--dhcp-tag",        dest="dhcp_tag",      help="for use in advanced DHCP configurations")
            p.add_option("--gateway",         dest="gateway",       help="for static IP / templating usage")
            p.add_option("--hostname",        dest="hostname",      help="ex: server.example.org")

            if not self.matches_args(args,["find"]):
                p.add_option("--interface",       dest="interface",  default="eth0", help="edit this interface")
                # FIXME: not alphabetized!
                p.add_option("--delete-interface", dest="delete_interface", metavar="INTERFACE", help="delete the selected interface")
            p.add_option("--image",           dest="image",         help="inherit values from this image, not compatible with --profile")
            p.add_option("--ip",              dest="ip",            help="ex: 192.168.1.55, (RECOMMENDED)")
            p.add_option("--kickstart",       dest="kickstart",     help="override profile kickstart template")
            p.add_option("--kopts",           dest="kopts",         help="ex: 'noipv6'")
            p.add_option("--kopts-post",      dest="kopts_post",    help="ex: 'clocksource=pit'")
            p.add_option("--ksmeta",          dest="ksmeta",        help="ex: 'blippy=7'")
            p.add_option("--mac",             dest="mac",           help="ex: 'AA:BB:CC:DD:EE:FF', (RECOMMENDED)")
            p.add_option("--mgmt-classes",    dest="mgmt_classes",  help="list of config management classes (for Puppet, etc)")
            p.add_option("--template-files",  dest="template_files",help="specify files to be generated from templates during a sync")

            if not self.matches_args(args, ["find"]):
                p.add_option("--in-place", action="store_true", default=False, dest="inplace", help="edit items in kopts, kopts_post or ksmeta without clearing the other items")

        p.add_option("--name",   dest="name",                     help="a name for the system (REQUIRED)")

        if not self.matches_args(args,["dumpvars","poweron","poweroff","reboot","remove","report","getks","list"]):
            p.add_option("--netboot-enabled", dest="netboot_enabled", help="PXE on (1) or off (0)")

        if self.matches_args(args,["copy","rename"]):
            p.add_option("--newname", dest="newname",                 help="for use with copy/edit")

        if not self.matches_args(args,["dumpvars","find","poweron","poweroff","reboot","remove","report","getks","list"]):
            p.add_option("--no-sync",     action="store_true", dest="nosync", help="suppress sync for speed")
        if not self.matches_args(args,["dumpvars","find","poweron","poweroff","reboot","report","getks","list"]):
            p.add_option("--no-triggers", action="store_true", dest="notriggers", help="suppress trigger execution")

        if not self.matches_args(args,["dumpvars","poweron","poweroff","reboot","remove","report","getks","list"]):
            p.add_option("--owners",          dest="owners",          help="specify owners for authz_ownership module")

            p.add_option("--power-address",   dest="power_address",   help="address of power mgmt device, if required")
            p.add_option("--power-id",        dest="power_id",        help="plug-number or blade name, if required")
            p.add_option("--power-pass",      dest="power_pass",      help="password for power management interface")

            p.add_option("--power-type",      dest="power_type",      help="one of: none, bullpap, wti, apc_snmp, ether-wake, ipmilan, drac, ipmitool, ilo")

            p.add_option("--power-user",      dest="power_user",      help="username for power management interface, if required")

            p.add_option("--profile",         dest="profile",         help="name of cobbler profile (REQUIRED)")
            p.add_option("--server-override", dest="server_override", help="overrides server value in settings file")
            p.add_option("--static",          dest="static",          help="specifies this interface does (0) or does not use DHCP (1), default 0")
            p.add_option("--subnet",          dest="subnet",          help="for static IP usage only")

            p.add_option("--virt-bridge",      dest="virt_bridge", help="ex: 'virbr0'")
            p.add_option("--virt-cpus",        dest="virt_cpus", help="integer (default: 1)")
            p.add_option("--virt-file-size",   dest="virt_file_size", help="size in GB")
            p.add_option("--virt-path",        dest="virt_path", help="path, partition, or volume")
            p.add_option("--virt-ram",         dest="virt_ram", help="size in MB")
            p.add_option("--virt-type",        dest="virt_type", help="ex: 'xenpv', 'qemu'")


    def run(self):
        
        if self.args and "find" in self.args:
            items = self.api.find_system(return_list=True, no_errors=True, **self.options.__dict__)
            for x in items:
                print x.name
            return True

        obj = self.object_manipulator_start(self.api.new_system,self.api.systems)

        if obj is None:
            return True

        if self.matches_args(self.args,["dumpvars"]):
            return self.object_manipulator_finish(obj, self.api.profiles, self.options)

        if self.matches_args(self.args,["getks"]):
            return self.object_manipulator_finish(obj, self.api.profiles, self.options)

        if self.options.comment:         obj.set_comment(self.options.comment)
        if self.options.profile:         obj.set_profile(self.options.profile)
        if self.options.image:           obj.set_image(self.options.image)
        if self.options.kopts:           obj.set_kernel_options(self.options.kopts,self.options.inplace)
        if self.options.kopts_post:      obj.set_kernel_options_post(self.options.kopts_post,self.options.inplace)
        if self.options.ksmeta:          obj.set_ksmeta(self.options.ksmeta,self.options.inplace)
        if self.options.kickstart:       obj.set_kickstart(self.options.kickstart)
        if self.options.netboot_enabled: obj.set_netboot_enabled(self.options.netboot_enabled)
        if self.options.server_override: obj.set_server(self.options.server_override)

        if self.options.virt_file_size:  obj.set_virt_file_size(self.options.virt_file_size)
        if self.options.virt_ram:        obj.set_virt_ram(self.options.virt_ram)

        if self.options.power_address:   obj.set_power_address(self.options.power_address)
        if self.options.power_pass:      obj.set_power_pass(self.options.power_pass)
        if self.options.power_id:        obj.set_power_pass(self.options.power_id)
        if self.options.power_type:      obj.set_power_type(self.options.power_type)
        if self.options.power_user:      obj.set_power_user(self.options.power_user)

        if self.options.virt_type:       obj.set_virt_type(self.options.virt_type)
        if self.options.virt_cpus:       obj.set_virt_cpus(self.options.virt_cpus)
        if self.options.virt_path:       obj.set_virt_path(self.options.virt_path)



        # if we haven't said what interface we are editing, it's eth0.

        if self.options.interface:
            my_interface = self.options.interface
        else:
            my_interface = "eth0"

        # if the interface is an integer stick "eth" in front of it as that's likely what
        # the user means.
 
        remap = False
        try:
            int(my_interface)
            remap = True
        except:
            pass

        if remap:
            my_interface = "eth%s" % my_interface


        if self.options.hostname:    obj.set_hostname(self.options.hostname, my_interface)
        if self.options.mac:
            if self.options.mac.lower() == 'random':
                obj.set_mac_address(get_random_mac(self.api), my_interface)
            else:
                obj.set_mac_address(self.options.mac,   my_interface)
        if self.options.ip:          obj.set_ip_address(self.options.ip,     my_interface)
        if self.options.subnet:      obj.set_subnet(self.options.subnet,     my_interface)
        if self.options.gateway:     obj.set_gateway(self.options.gateway,   my_interface)
        if self.options.dhcp_tag:    obj.set_dhcp_tag(self.options.dhcp_tag, my_interface)
        if self.options.virt_bridge: obj.set_virt_bridge(self.options.virt_bridge, my_interface)
        if self.options.static:      obj.set_static(self.options.static,     my_interface)
        if self.options.bonding:     obj.set_bonding(self.options.bonding,   my_interface)
        if self.options.bonding_master: obj.set_bonding_master(self.options.bonding_master, my_interface)
        if self.options.bonding_opts: obj.set_bonding_opts(self.options.bonding_opts, my_interface)

        if self.options.delete_interface:
            success = obj.delete_interface(self.options.delete_interface)
            if not success:
                raise CX(_('interface does not exist or is the default interface (%s)') % self.options.delete_interface)

        if self.options.owners:       obj.set_owners(self.options.owners)
        if self.options.mgmt_classes: obj.set_mgmt_classes(self.options.mgmt_classes)
        if self.options.template_files: obj.set_template_files(self.options.template_files,self.options.inplace)


        rc = self.object_manipulator_finish(obj, self.api.systems, self.options)

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


