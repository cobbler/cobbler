"""
This is some of the code behind 'cobbler sync'.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>
# SPDX-FileCopyrightText: John Eckersberg <jeckersb@redhat.com>

import time

from cobbler.utils import process_management
from cobbler.manager import ManagerModule

MANAGER = None


def register() -> str:
    """
    The mandatory Cobbler modules registration hook.

    :return: Always "manage".
    """
    return "manage"


class _DnsmasqManager(ManagerModule):
    """
    Handles conversion of internal state to the tftpboot tree layout.
    """

    @staticmethod
    def what() -> str:
        """
        This identifies the module.

        :return: Will always return ``dnsmasq``.
        """
        return "dnsmasq"

    def write_configs(self):
        """
        DHCP files are written when ``manage_dhcp`` is set in our settings.

        :raises OSError
        """

        settings_file = "/etc/dnsmasq.conf"
        template_file = "/etc/cobbler/dnsmasq.template"

        try:
            with open(template_file, "r", encoding="UTF-8") as template_file_fd:
                template_data = template_file_fd.read()
        except Exception as error:
            raise OSError(f"error writing template to file: {template_file}") from error

        system_definitions = {}

        # we used to just loop through each system, but now we must loop
        # through each network interface of each system.

        for system in self.systems:

            if not system.is_management_supported(cidr_ok=False):
                continue

            profile = system.get_conceptual_parent()
            distro = profile.get_conceptual_parent()
            for interface in system.interfaces.values():

                mac = interface.mac_address
                ip_address = interface.ip_address
                host = interface.dns_name
                ipv6 = interface.ipv6_address

                if not mac:
                    # can't write a DHCP entry for this system
                    continue

                # In many reallife situations there is a need to control the IP address and hostname for a specific
                # client when only the MAC address is available. In addition to that in some scenarios there is a need
                # to explicitly label a host with the applicable architecture in order to correctly handle situations
                # where we need something other than ``pxelinux.0``. So we always write a dhcp-host entry with as much
                # info as possible to allow maximum control and flexibility within the dnsmasq config.

                systxt = "dhcp-host=net:" + distro.arch.value.lower() + "," + mac

                if host != "":
                    systxt += "," + host

                if ip_address != "":
                    systxt += "," + ip_address
                if ipv6 != "":
                    systxt += f",[{ipv6}]"

                systxt += "\n"

                dhcp_tag = interface.dhcp_tag
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
            "next_server_v4": self.settings.next_server_v4,
            "next_server_v6": self.settings.next_server_v6,
        }

        # now add in other DHCP expansions that are not tagged with "default"
        for system in list(system_definitions.keys()):
            if system == "default":
                continue
            metadata[
                f"insert_cobbler_system_definitions_{system}"
            ] = system_definitions[system]

        self.api.templar.render(template_data, metadata, settings_file)

    def regen_ethers(self):
        """
        This function regenerates the ethers file. To get more information please read ``man ethers``, the format is
        also in there described.
        """
        # dnsmasq knows how to read this database of MACs -> IPs, so we'll keep it up to date every time we add a
        # system.
        with open("/etc/ethers", "w+", encoding="UTF-8") as ethers_fh:
            for system in self.systems:
                if not system.is_management_supported(cidr_ok=False):
                    continue
                for interface in system.interfaces.values():
                    mac = interface.mac_address
                    ip_address = interface.ip_address
                    if not mac:
                        # can't write this w/o a MAC address
                        continue
                    if ip_address is not None and ip_address != "":
                        ethers_fh.write(mac.upper() + "\t" + ip_address + "\n")

    def regen_hosts(self):
        """
        This rewrites the hosts file and thus also rewrites the dns config.
        """
        # dnsmasq knows how to read this database for host info (other things may also make use of this later)
        with open(
            "/var/lib/cobbler/cobbler_hosts", "w+", encoding="UTF-8"
        ) as regen_hosts_fd:
            for system in self.systems:
                if not system.is_management_supported(cidr_ok=False):
                    continue
                for (_, interface) in system.interfaces.items():
                    mac = interface.mac_address
                    host = interface.dns_name
                    ipv4 = interface.ip_address
                    ipv6 = interface.ipv6_address
                    if not mac:
                        continue
                    if (
                        host is not None
                        and host != ""
                        and ipv6 is not None
                        and ipv6 != ""
                    ):
                        regen_hosts_fd.write(ipv6 + "\t" + host + "\n")
                    elif (
                        host is not None
                        and host != ""
                        and ipv4 is not None
                        and ipv4 != ""
                    ):
                        regen_hosts_fd.write(ipv4 + "\t" + host + "\n")

    def restart_service(self):
        """
        This restarts the dhcp server and thus applied the newly written config files.
        """
        service_name = "dnsmasq"
        if self.settings.restart_dhcp:
            return_code_service_restart = process_management.service_restart(
                service_name
            )
            if return_code_service_restart != 0:
                self.logger.error("%s service failed", service_name)
            return return_code_service_restart


def get_manager(api):
    """
    Creates a manager object to manage a dnsmasq server.

    :param api: The API to resolve all information with.
    :return: The object generated from the class.
    """
    # Singleton used, therefore ignoring 'global'
    global MANAGER  # pylint: disable=global-statement

    if not MANAGER:
        MANAGER = _DnsmasqManager(api)
    return MANAGER
