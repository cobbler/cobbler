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
import copy

from cobbler import templar
from cobbler import utils

from cobbler.cexceptions import CX


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "manage"


class IscManager:

    def what(self) -> str:
        """
        Static method to identify the manager.

        :return: Always "isc".
        """
        return "isc"

    def __init__(self, collection_mgr, logger):
        """
        Constructor

        :param collection_mgr: The collection manager to resolve all information with.
        :param logger: The logger to audit all actions with.
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
        self.settings_file = utils.dhcpconf_location()

    def write_dhcp_file(self):
        """
        DHCP files are written when ``manage_dhcp`` is set in our settings.
        """

        template_file = "/etc/cobbler/dhcp.template"
        blender_cache = {}

        try:
            f2 = open(template_file, "r")
        except:
            raise CX("error reading template: %s" % template_file)
        template_data = ""
        template_data = f2.read()
        f2.close()

        # Use a simple counter for generating generic names where a hostname is not available.
        counter = 0

        # We used to just loop through each system, but now we must loop through each network interface of each system.
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
            for (name, system_interface) in list(system.interfaces.items()):

                # We make a copy because we may modify it before adding it to the dhcp_tags and we don't want to affect
                # the master copy.
                interface = copy.deepcopy(system_interface)

                if interface["if_gateway"]:
                    interface["gateway"] = interface["if_gateway"]
                else:
                    interface["gateway"] = system.gateway

                mac = interface["mac_address"]

                if interface["interface_type"] in ("bond_slave", "bridge_slave", "bonded_bridge_slave"):

                    if interface["interface_master"] not in system.interfaces:
                        # Can't write DHCP entry; master interface does not exist
                        continue

                    # We may have multiple bonded interfaces, so we need a composite index into ding.
                    name_master = "%s-%s" % (system.name, interface["interface_master"])
                    if name_master not in ding:
                        ding[name_master] = {interface["interface_master"]: []}

                    if len(ding[name_master][interface["interface_master"]]) == 0:
                        ding[name_master][interface["interface_master"]].append(mac)
                    else:
                        ignore_macs.append(mac)

                    ip = system.interfaces[interface["interface_master"]]["ip_address"]
                    netmask = system.interfaces[interface["interface_master"]]["netmask"]
                    dhcp_tag = system.interfaces[interface["interface_master"]]["dhcp_tag"]
                    host = system.interfaces[interface["interface_master"]]["dns_name"]

                    if ip is None or ip == "":
                        for (nam2, int2) in list(system.interfaces.items()):
                            if nam2.startswith(interface["interface_master"] + ".") \
                                    and int2["ip_address"] is not None \
                                    and int2["ip_address"] != "":
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
                interface["filename"] = blended_system.get("filename")
                interface["netboot_enabled"] = blended_system["netboot_enabled"]
                interface["hostname"] = blended_system["hostname"]
                interface["owner"] = blended_system["name"]
                interface["enable_gpxe"] = blended_system["enable_gpxe"]
                interface["name_servers"] = blended_system["name_servers"]
                interface["mgmt_parameters"] = blended_system["mgmt_parameters"]

                # Explicitly declare filename for other (non x86) archs as in DHCP discover package mostly the
                # architecture cannot be differed due to missing bits...
                if distro is not None and not interface.get("filename"):
                    if distro.arch == "ppc" or distro.arch == "ppc64":
                        interface["filename"] = yaboot
                    elif distro.arch == "ppc64le":
                        interface["filename"] = "grub/grub.ppc64le"
                    elif distro.arch == "aarch64":
                        interface["filename"] = "grub/grubaa64.efi"

                if not self.settings.always_write_dhcp_entries:
                    if not interface["netboot_enabled"] and interface['static']:
                        continue

                if dhcp_tag == "":
                    dhcp_tag = blended_system.get("dhcp_tag", "")
                    if dhcp_tag == "":
                        dhcp_tag = "default"

                if dhcp_tag not in dhcp_tags:
                    dhcp_tags[dhcp_tag] = {
                        mac: interface
                    }
                else:
                    dhcp_tags[dhcp_tag][mac] = interface

        # Remove macs from redundant slave interfaces from dhcp_tags otherwise you get duplicate ip's in the installer.
        for dt in list(dhcp_tags.keys()):
            for m in list(dhcp_tags[dt].keys()):
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
        self.templar.render(template_data, metadata, self.settings_file)

    def regen_ethers(self):
        """
        ISC/BIND doesn't use this. It is there for compability reasons with other managers.
        """
        pass

    def sync_dhcp(self):
        """
        This syncs the dhcp server with it's new config files. Basically this restarts the service to apply the changes.
        """
        service_name = utils.dhcp_service_name()
        if self.settings.restart_dhcp:
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
    """
    Creates a manager object to manage an isc dhcp server.

    :param collection_mgr: The collection manager which holds all information in the current Cobbler instance.
    :param logger: The logger to audit all actions with.
    :return: The object to manage the server with.
    """
    return IscManager(collection_mgr, logger)
