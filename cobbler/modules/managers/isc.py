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
import shutil
import time

from cobbler import utils
from cobbler.enums import Archs
from cobbler.manager import ManagerModule

MANAGER = None


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "manage"


class _IscManager(ManagerModule):

    @staticmethod
    def what() -> str:
        """
        Static method to identify the manager.

        :return: Always "isc".
        """
        return "isc"

    def __init__(self, api):
        super().__init__(api)

        self.settings_file_v4 = utils.dhcpconf_location(utils.DHCP.V4)
        self.settings_file_v6 = utils.dhcpconf_location(utils.DHCP.V6)

    def write_v4_config(self, template_file="/etc/cobbler/dhcp.template"):
        """
        DHCPv4 files are written when ``manage_dhcp_v4`` is set in our settings.

        :param template_file: The location of the DHCP template.
        """

        blender_cache = {}

        with open(template_file, "r") as f2:
            template_data = f2.read()

        # Use a simple counter for generating generic names where a hostname is not available.
        counter = 0

        # We used to just loop through each system, but now we must loop through each network interface of each system.
        dhcp_tags = {"default": {}}

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
                interface = system_interface.to_dict()

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
                        for (interface_name, interface_object) in list(system.interfaces.items()):
                            if interface_name.startswith(interface["interface_master"] + ".") \
                                    and interface_object.ip_address is not None \
                                    and interface_object.ip_address != "":
                                ip = interface_object.ip_address
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
                        interface["name"] = "%s" % host
                else:
                    interface["name"] = "generic%d" % counter

                # add references to the system, profile, and distro for use in the template
                if system.name in blender_cache:
                    blended_system = blender_cache[system.name]
                else:
                    blended_system = utils.blender(self.api, False, system)
                    blender_cache[system.name] = blended_system

                interface["next_server_v4"] = blended_system["next_server_v4"]
                interface["filename"] = blended_system.get("filename")
                interface["netboot_enabled"] = blended_system["netboot_enabled"]
                interface["hostname"] = blended_system["hostname"]
                interface["owner"] = blended_system["name"]
                interface["enable_ipxe"] = blended_system["enable_ipxe"]
                interface["name_servers"] = blended_system["name_servers"]
                interface["mgmt_parameters"] = blended_system["mgmt_parameters"]

                # Explicitly declare filename for other (non x86) archs as in DHCP discover package mostly the
                # architecture cannot be differed due to missing bits...
                if distro is not None and not interface.get("filename"):
                    if distro.arch in [Archs.PPC, Archs.PPC64, Archs.PPC64LE, Archs.PPC64EL]:
                        interface["filename"] = "grub/grub.ppc64le"
                    elif distro.arch == Archs.AARCH64:
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
            "next_server_v4": self.settings.next_server_v4,
            "dhcp_tags": dhcp_tags
        }

        self.logger.info("generating %s", self.settings_file_v4)
        self.templar.render(template_data, metadata, self.settings_file_v4)

    def write_v6_config(self, template_file="/etc/cobbler/dhcp6.template"):
        """
        DHCPv6 files are written when ``manage_dhcp_v6`` is set in our settings.

        :param template_file: The location of the DHCP template.
        """

        blender_cache = {}

        with open(template_file, "r") as f2:
            template_data = f2.read()

        # Use a simple counter for generating generic names where a hostname is not available.
        counter = 0

        # We used to just loop through each system, but now we must loop through each network interface of each system.
        dhcp_tags = {"default": {}}

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
                interface = system_interface.to_dict()

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

                    ip_v6 = system.interfaces[interface["interface_master"]]["ipv6_address"]
                    dhcp_tag = system.interfaces[interface["interface_master"]]["dhcp_tag"]
                    host = system.interfaces[interface["interface_master"]]["dns_name"]

                    if not ip_v6:
                        for (interface_name, interface_object) in list(system.interfaces.items()):
                            if interface_name.startswith(interface["interface_master"] + ".") \
                                    and interface_object.ipv6_address is not None \
                                    and interface_object.ipv6_address != "":
                                ip_v6 = interface_object.ipv6_address
                                break

                    interface["ipv6_address"] = ip_v6
                else:
                    ip_v6 = interface["ipv6_address"]
                    dhcp_tag = interface["dhcp_tag"]
                    host = interface["dns_name"]

                if distro is not None:
                    interface["distro"] = distro.to_dict()

                if not mac or not ip_v6:
                    # can't write a DHCP entry for this system
                    self.logger.warning("%s has no IPv6 or MAC address", system.name)
                    continue
                counter = counter + 1

                # the label the entry after the hostname if possible
                if host:
                    if name != "eth0":
                        interface["name"] = "%s-%s" % (host, name)
                    else:
                        interface["name"] = "%s" % host
                else:
                    interface["name"] = "generic%d" % counter

                # add references to the system, profile, and distro for use in the template
                if system.name in blender_cache:
                    blended_system = blender_cache[system.name]
                else:
                    blended_system = utils.blender(self.api, False, system)
                    blender_cache[system.name] = blended_system

                interface["next_server_v6"] = blended_system["next_server_v6"]
                interface["filename"] = blended_system.get("filename")
                interface["netboot_enabled"] = blended_system["netboot_enabled"]
                interface["hostname"] = blended_system["hostname"]
                interface["owner"] = blended_system["name"]
                interface["name_servers"] = blended_system["name_servers"]
                interface["mgmt_parameters"] = blended_system["mgmt_parameters"]

                # Explicitly declare filename for other (non x86) archs as in DHCP discover package mostly the
                # architecture cannot be differed due to missing bits...
                if distro is not None and not interface.get("filename"):
                    if distro.arch == Archs.PPC:
                        interface["filename"] = "grub/grub.ppc"
                    elif distro.arch == Archs.PPC64:
                        interface["filename"] = "grub/grub.ppc64"
                    elif distro.arch == Archs.PPC64LE:
                        interface["filename"] = "grub/grub.ppc64le"
                    elif distro.arch == Archs.AARCH64:
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
            "next_server_v6": self.settings.next_server_v6,
            "dhcp_tags": dhcp_tags
        }

        if self.logger is not None:
            self.logger.info("generating %s" % self.settings_file_v6)
        self.templar.render(template_data, metadata, self.settings_file_v6)

    def restart_dhcp(self, service_name: str) -> int:
        """
        This syncs the dhcp server with it's new config files.
        Basically this restarts the service to apply the changes.

        :param service_name: The name of the DHCP service.
        """
        dhcpd_path = shutil.which(service_name)
        return_code_service_restart = utils.subprocess_call([dhcpd_path, "-t", "-q"], shell=False)
        if return_code_service_restart != 0:
            self.logger.error("Testing config - {} -t failed".format(service_name))
        return_code_service_restart = utils.service_restart(service_name)
        if return_code_service_restart != 0:
            self.logger.error("{} service failed".format(service_name))
        return return_code_service_restart

    def write_configs(self):
        if self.settings.manage_dhcp_v4:
            self.write_v4_config()
        if self.settings.manage_dhcp_v6:
            self.write_v6_config()

    def restart_service(self) -> int:
        if not self.settings.restart_dhcp:
            return 0

        # Even if one fails, try both and return an error
        ret = 0
        if self.settings.manage_dhcp_v4:
            service_v4 = utils.dhcp_service_name()
            ret |= self.restart_dhcp(service_v4)
        if self.settings.manage_dhcp_v6:
            # TODO: Fix hard coded string
            ret |= self.restart_dhcp("dhcpd6")
        return ret


def get_manager(api):
    """
    Creates a manager object to manage an isc dhcp server.

    :param api: The API which holds all information in the current Cobbler instance.
    :return: The object to manage the server with.
    """
    # Singleton used, therefore ignoring 'global'
    global MANAGER  # pylint: disable=global-statement

    if not MANAGER:
        MANAGER = _IscManager(api)
    return MANAGER
