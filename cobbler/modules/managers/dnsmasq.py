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


def register() -> str:
    """
    The mandatory Cobbler modules registration hook.

    :return: Always "manage".
    """
    return "manage"


class DnsmasqManager:
    """
    Handles conversion of internal state to the tftpboot tree layout.
    """

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

    def what(self) -> str:
        """
        This identifies the module.

        :return: Will always return ``dnsmasq``.
        """
        return "dnsmasq"

    def write_dhcp_lease(self, port, host, ip, mac):
        """
        Not used

        :param port: Unused in this module implementation.
        :param host: Unused in this module implementation.
        :param ip: Unused in this module implementation.
        :param mac: Unused in this module implementation.
        """
        pass

    def remove_dhcp_lease(self, port, host):
        """
        Not used

        :param port: Unused in this module implementation.
        :param host: Unused in this module implementation.
        """
        pass

    def write_dhcp_file(self):
        """
        DHCP files are written when ``manage_dhcp`` is set in our settings.
        """

        settings_file = "/etc/dnsmasq.conf"
        template_file = "/etc/cobbler/dnsmasq.template"

        try:
            f2 = open(template_file, "r")
        except Exception:
            raise CX("error writing template to file: %s" % template_file)
        template_data = f2.read()
        f2.close()

        system_definitions = {}
        counter = 0

        # we used to just loop through each system, but now we must loop
        # through each network interface of each system.

        for system in self.systems:

            if not system.is_management_supported(cidr_ok=False):
                continue

            profile = system.get_conceptual_parent()
            distro = profile.get_conceptual_parent()
            for (name, interface) in list(system.interfaces.items()):

                mac = interface["mac_address"]
                ip = interface["ip_address"]
                host = interface["dns_name"]
                ipv6 = interface["ipv6_address"]

                if not mac:
                    # can't write a DHCP entry for this system
                    continue

                counter += 1

                # In many reallife situations there is a need to control the IP address and hostname for a specific
                # client when only the MAC address is available. In addition to that in some scenarios there is a need
                # to explicitly label a host with the applicable architecture in order to correctly handle situations
                # where we need something other than ``pxelinux.0``. So we always write a dhcp-host entry with as much
                # info as possible to allow maximum control and flexibility within the dnsmasq config.

                systxt = "dhcp-host=net:" + distro.arch.lower() + "," + mac

                if host is not None and host != "":
                    systxt += "," + host

                if ip is not None and ip != "":
                    systxt += "," + ip
                if ipv6 is not None and ipv6 != "":
                    systxt += ",[%s]" % ipv6

                systxt += "\n"

                dhcp_tag = interface["dhcp_tag"]
                if dhcp_tag == "":
                    dhcp_tag = "default"

                if dhcp_tag not in system_definitions:
                    system_definitions[dhcp_tag] = ""
                system_definitions[dhcp_tag] = system_definitions[dhcp_tag] + systxt

        # We are now done with the looping through each interface of each system.

        metadata = {
            "insert_cobbler_system_definitions": system_definitions.get("default", ""),
            "date": time.asctime(time.gmtime()),
            "cobbler_server": self.settings.server,
            "next_server": self.settings.next_server,
        }

        # now add in other DHCP expansions that are not tagged with "default"
        for x in list(system_definitions.keys()):
            if x == "default":
                continue
            metadata["insert_cobbler_system_definitions_%s" % x] = system_definitions[x]

        self.templar.render(template_data, metadata, settings_file)

    def regen_ethers(self):
        """
        This function regenerates the ethers file. To get more information please read ``man ethers``, the format is
        also in there described.
        """
        # dnsmasq knows how to read this database of MACs -> IPs, so we'll keep it up to date every time we add a
        # system.
        fh = open("/etc/ethers", "w+")
        for system in self.systems:
            if not system.is_management_supported(cidr_ok=False):
                continue
            for (name, interface) in list(system.interfaces.items()):
                mac = interface["mac_address"]
                ip = interface["ip_address"]
                if not mac:
                    # can't write this w/o a MAC address
                    continue
                if ip is not None and ip != "":
                    fh.write(mac.upper() + "\t" + ip + "\n")
        fh.close()

    def regen_hosts(self):
        """
        This rewrites the hosts file and thus also rewrites the dns config.
        """
        # dnsmasq knows how to read this database for host info (other things may also make use of this later)
        fh = open("/var/lib/cobbler/cobbler_hosts", "w+")
        for system in self.systems:
            if not system.is_management_supported(cidr_ok=False):
                continue
            for (name, interface) in list(system.interfaces.items()):
                mac = interface["mac_address"]
                host = interface["dns_name"]
                ip = interface["ip_address"]
                ipv6 = interface["ipv6_address"]
                if not mac:
                    continue
                if host is not None and host != "" and ipv6 is not None and ipv6 != "":
                    fh.write(ipv6 + "\t" + host + "\n")
                elif host is not None and host != "" and ip is not None and ip != "":
                    fh.write(ip + "\t" + host + "\n")
        fh.close()

    def write_dns_files(self):
        """
        Not used
        """
        # already taken care of by the regen_hosts()
        pass

    def sync_dhcp(self):
        """
        This restarts the dhcp server and thus applied the newly written config files.
        """
        if self.settings.restart_dhcp:
            rc = utils.subprocess_call(self.logger, "service dnsmasq restart")
            if rc != 0:
                error_msg = "service dnsmasq restart failed"
                self.logger.error(error_msg)
                raise CX(error_msg)


def get_manager(collection_mgr, logger):
    """
    Creates a manager object to manage a dnsmasq server.

    :param collection_mgr: The collection manager to resolve all information with.
    :param logger: The logger to audit all actions with.
    :return: The object generated from the class.
    """
    return DnsmasqManager(collection_mgr, logger)
