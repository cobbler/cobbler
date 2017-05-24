"""
This is some of the code behind 'cobbler sync'.

Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>
John Eckersberg <jeckersb@redhat.com>

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

import time

import cobbler.templar as templar
import cobbler.utils as utils

from cobbler.cexceptions import CX
from cobbler.utils import _


def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "manage"


class IscManager:

    def what(self):
        return "isc"

    def __init__(self, collection_mgr, logger):
        """
        Constructor
        """
        self.logger = logger
        self.collection_mgr = collection_mgr
        self.api = collection_mgr.api
        self.distros = collection_mgr.distros()
        self.profiles = collection_mgr.profiles()
        self.systems = collection_mgr.systems()
        self.settings = collection_mgr.settings()
        self.repos = collection_mgr.repos()
        self.templar = templar.Templar(collection_mgr)
        self.settings_file = utils.dhcpconf_location(self.api)

    def write_dhcp_file(self):
        """
        DHCP files are written when manage_dhcp is set in
        /etc/cobbler/settings.
        """

        template_file = "/etc/cobbler/dhcp.template"
        blender_cache = {}

        try:
            f2 = open(template_file, "r")
        except:
            raise CX(_("error reading template: %s") % template_file)
        template_data = ""
        template_data = f2.read()
        f2.close()

        # use a simple counter for generating generic names where a hostname
        # is not available
        counter = 0

        # we used to just loop through each system, but now we must loop
        # through each network interface of each system.
        dhcp_tags = {"default": {}}
        yaboot = "/yaboot"

        # FIXME: ding should evolve into the new dhcp_tags dict
        ding = {}
        ignore_macs = []

        for system in self.systems:
            if not system.is_management_supported(cidr_ok=False):
                continue

            profile = system.get_conceptual_parent()
            distro = profile.get_conceptual_parent()

            # if distro is None then the profile is really an image record
            for (name, interface) in system.interfaces.iteritems():

                # this is really not a per-interface setting
                # but we do this to make the templates work
                # without upgrade
                interface["gateway"] = system.gateway
                mac = interface["mac_address"]

                if interface["interface_type"] in ("bond_slave", "bridge_slave", "bonded_bridge_slave"):

                    if interface["interface_master"] not in system.interfaces:
                        # Can't write DHCP entry; master interface does not exist
                        continue

                    if system.name not in ding:
                        ding[system.name] = {interface["interface_master"]: []}

                    if len(ding[system.name][interface["interface_master"]]) == 0:
                        ding[system.name][interface["interface_master"]].append(mac)
                    else:
                        ignore_macs.append(mac)

                    ip = system.interfaces[interface["interface_master"]]["ip_address"]
                    netmask = system.interfaces[interface["interface_master"]]["netmask"]
                    dhcp_tag = system.interfaces[interface["interface_master"]]["dhcp_tag"]
                    host = system.interfaces[interface["interface_master"]]["dns_name"]

                    if ip is None or ip == "":
                        for (nam2, int2) in system.interfaces.iteritems():
                            if (nam2.startswith(interface["interface_master"] + ".") and int2["ip_address"] is not None and int2["ip_address"] != ""):
                                    ip = int2["ip_address"]
                                    break

                    interface["ip_address"] = ip
                    interface["netmask"] = netmask
                else:
                    ip = interface["ip_address"]
                    netmask = interface["netmask"]
                    dhcp_tag = interface["dhcp_tag"]
                    host = interface["dns_name"]

                if distro is not None:
                    interface["distro"] = distro.to_dict()

                if mac is None or mac == "":
                    # can't write a DHCP entry for this system
                    continue

                counter = counter + 1

                # the label the entry after the hostname if possible
                if host is not None and host != "":
                    if name != "eth0":
                        interface["name"] = "%s-%s" % (host, name)
                    else:
                        interface["name"] = "%s" % (host)
                else:
                    interface["name"] = "generic%d" % counter

                # add references to the system, profile, and distro
                # for use in the template
                if system.name in blender_cache:
                    blended_system = blender_cache[system.name]
                else:
                    blended_system = utils.blender(self.api, False, system)
                    blender_cache[system.name] = blended_system

                interface["next_server"] = blended_system["next_server"]
                interface["netboot_enabled"] = blended_system["netboot_enabled"]
                interface["hostname"] = blended_system["hostname"]
                interface["owner"] = blended_system["name"]
                interface["enable_gpxe"] = blended_system["enable_gpxe"]
                interface["name_servers"] = blended_system["name_servers"]

                if not self.settings.always_write_dhcp_entries:
                    if not interface["netboot_enabled"] and interface['static']:
                        continue

                if distro is not None:
                    if distro.arch.startswith("ppc"):
                        if blended_system["boot_loader"] == "pxelinux":
                            del interface["filename"]
                        elif distro.boot_loader == "grub2" or blended_system["boot_loader"] == "grub2":
                            interface["filename"] = "boot/grub/powerpc-ieee1275/core.elf"
                        else:
                            interface["filename"] = yaboot

                if dhcp_tag == "":
                    dhcp_tag = blended_system["dhcp_tag"]
                    if dhcp_tag == "":
                        dhcp_tag = "default"

                if dhcp_tag not in dhcp_tags:
                    dhcp_tags[dhcp_tag] = {
                        mac: interface
                    }
                else:
                    dhcp_tags[dhcp_tag][mac] = interface

        # remove macs from redundant slave interfaces from dhcp_tags
        # otherwise you get duplicate ip's in the installer
        for dt in dhcp_tags.keys():
            for m in dhcp_tags[dt].keys():
                if m in ignore_macs:
                    del dhcp_tags[dt][m]

        # we are now done with the looping through each interface of each system
        metadata = {
            "date": time.asctime(time.gmtime()),
            "cobbler_server": "%s:%s" % (self.settings.server, self.settings.http_port),
            "next_server": self.settings.next_server,
            "yaboot": yaboot,
            "dhcp_tags": dhcp_tags
        }

        if self.logger is not None:
            self.logger.info("generating %s" % self.settings_file)
        self.templar.render(template_data, metadata, self.settings_file, None)

    def regen_ethers(self):
        pass            # ISC/BIND do not use this

    def sync_dhcp(self):
        restart_dhcp = str(self.settings.restart_dhcp).lower()
        service_name = utils.dhcp_service_name(self.api)
        if restart_dhcp != "0":
            rc = utils.subprocess_call(self.logger, "dhcpd -t -q", shell=True)
            if rc != 0:
                error_msg = "dhcpd -t failed"
                self.logger.error(error_msg)
                raise CX(error_msg)
            service_restart = "service %s restart" % service_name
            rc = utils.subprocess_call(self.logger, service_restart, shell=True)
            if rc != 0:
                error_msg = "%s failed" % service_name
                self.logger.error(error_msg)
                raise CX(error_msg)


def get_manager(collection_mgr, logger):
    return IscManager(collection_mgr, logger)
