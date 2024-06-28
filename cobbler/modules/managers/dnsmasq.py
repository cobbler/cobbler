"""
This is some of the code behind 'cobbler sync'.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>
# SPDX-FileCopyrightText: John Eckersberg <jeckersb@redhat.com>

import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from cobbler import utils
from cobbler.modules.managers import DhcpManagerModule, DnsManagerModule

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.distro import Distro
    from cobbler.items.system import System


MANAGER = None


def register() -> str:
    """
    The mandatory Cobbler modules registration hook.

    :return: Always "manage".
    """
    return "manage"


class _DnsmasqManager(DnsManagerModule, DhcpManagerModule):
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

    def __init__(self, api: "CobblerAPI"):
        super().__init__(api)
        self.config: Dict[str, Any] = {}
        self.cobbler_hosts_file = self.api.settings().dnsmasq_hosts_file
        self.ethers_file = self.api.settings().dnsmasq_ethers_file

        utils.create_files_if_not_existing([self.cobbler_hosts_file, self.ethers_file])

    def write_configs(self) -> None:
        """
        DHCP files are written when ``manage_dhcp`` is set in our settings.

        :raises OSError
        :raises ValueError
        """
        self.config = self.gen_full_config()
        self._write_configs(self.config)

    def _write_configs(self, config_data: Optional[Dict[Any, Any]] = None) -> None:
        """
        Internal function to write DHCP files.

        :raises OSError
        :raises ValueError
        """
        if not config_data:
            raise ValueError("No config to write.")

        settings_file = "/etc/dnsmasq.conf"
        template_file = "/etc/cobbler/dnsmasq.template"

        try:
            with open(template_file, "r", encoding="UTF-8") as template_file_fd:
                template_data = template_file_fd.read()
        except Exception as error:
            raise OSError(f"error writing template to file: {template_file}") from error

        config_copy = config_data.copy()  # template rendering changes the passed dict
        self.logger.info("Writing %s", settings_file)
        self.templar.render(template_data, config_copy, settings_file)

    def gen_full_config(self) -> Dict[str, str]:
        """Generate DHCP configuration for all systems."""
        system_definitions: Dict[str, str] = {}

        for system in self.systems:
            system_config = self._gen_system_config(system)
            system_definitions = utils.merge_dicts_recursive(
                system_definitions, system_config, str_append=True
            )

        metadata = {
            "insert_cobbler_system_definitions": system_definitions.get("default", ""),
            "date": time.asctime(time.gmtime()),
            "cobbler_server": self.settings.server,
            "next_server_v4": self.settings.next_server_v4,
            "next_server_v6": self.settings.next_server_v6,
            "addn_host_file": self.cobbler_hosts_file,
        }

        # now add in other DHCP expansions that are not tagged with "default"
        for dhcp_tag, system_str in system_definitions.items():
            if dhcp_tag == "default":
                continue
            metadata[f"insert_cobbler_system_definitions_{dhcp_tag}"] = system_str

        return metadata

    def remove_single_system(self, system_obj: "System") -> None:
        """
        This method removes a single system.

        :param system_obj: System to be removed.
        """
        if not self.config:
            self.config = self.gen_full_config()

        system_config = self._gen_system_config(system_obj)
        for dhcp_tag, system_iface_config in system_config.items():
            config_key = "insert_cobbler_system_definitions"
            if dhcp_tag != "default":
                config_key = f"insert_cobbler_system_definitions_{dhcp_tag}"
            if system_iface_config not in self.config[config_key]:
                continue
            self.config[config_key] = self.config[config_key].replace(
                system_iface_config, ""
            )

        self._write_configs(self.config)
        self.remove_single_ethers_entry(system_obj)

    def _gen_system_config(
        self,
        system_obj: "System",
    ) -> Dict[str, str]:
        """
        Generate dnsmasq config for a single system.

        :param system_obj: System to generate dnsmasq config for
        """
        # we used to just loop through each system, but now we must loop
        # through each network interface of each system.
        system_definitions: Dict[str, str] = {}

        if not system_obj.is_management_supported(cidr_ok=False):
            self.logger.debug(
                "%s does not meet precondition: MAC, IPv4, or IPv6 address is required.",
                system_obj.name,
            )
            return {}

        profile = system_obj.get_conceptual_parent()
        if profile is None:
            raise ValueError("Profile for system not found!")
        distro: Optional["Distro"] = profile.get_conceptual_parent()  # type: ignore
        if distro is None:
            raise ValueError("Distro for system not found!")

        for interface in system_obj.interfaces.values():
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

        return system_definitions

    def _find_unique_dhcp_entries(
        self, dhcp_entries: str, config_key: str
    ) -> Tuple[str, str]:
        """
        This method checks the dhcp entries in the current config and returns
        only those that are unique.

        This is necessary because the sync_single_system method is used for
        both adding and modifying a single system.
        """
        unique_entries = ""
        duplicate_entries = ""
        for dhcp_entry in dhcp_entries.split("\n"):
            if dhcp_entry and dhcp_entry not in self.config[config_key]:
                unique_entries += f"{dhcp_entry}\n"
            else:
                duplicate_entries += f"{dhcp_entry}\n"
        return unique_entries, duplicate_entries

    def _parse_mac_from_dnsmasq_entries(self, entries: str) -> List[str]:
        return [entry.split(",")[1] for entry in entries.split("\n") if entry]

    def sync_single_system(self, system: "System"):
        """
        Synchronize data for a single system.

        :param system: A system to be added.
        """
        if not self.config:
            # cache miss, need full sync for consistent data
            self.regen_ethers()
            return self.sync()

        system_config = self._gen_system_config(system)
        updated_dhcp_entries: Dict[str, str] = {}
        duplicate_dhcp_entries = ""
        for iface_tag, dhcp_entries in system_config.items():
            config_key = "insert_cobbler_system_definitions"
            if iface_tag != "default":
                config_key = f"insert_cobbler_system_definitions_{iface_tag}"
            (
                unique_dhcp_entries,
                duplicate_dhcp_entries,
            ) = self._find_unique_dhcp_entries(dhcp_entries, config_key)
            updated_dhcp_entries[config_key] = unique_dhcp_entries
            self.config = utils.merge_dicts_recursive(
                self.config, {config_key: unique_dhcp_entries}, str_append=True
            )

        if all(not dhcp_entry for dhcp_entry in updated_dhcp_entries.values()):
            # No entries were updated. Therefore, User removed
            # or modified already existing mac address and we don't
            # know which mac address that was. Consequently, trigger
            # a full sync to keep DNS and DHCP entries consistent.
            self.regen_ethers()
            return self.sync()

        duplicate_macs = self._parse_mac_from_dnsmasq_entries(duplicate_dhcp_entries)
        self.sync_single_ethers_entry(system, duplicate_macs)

        self.config["date"] = time.asctime(time.gmtime())
        self._write_configs(self.config)
        return self.restart_service()

    def regen_ethers(self) -> None:
        """
        This function regenerates the ethers file. To get more information please read ``man ethers``, the format is
        also in there described.
        """
        # dnsmasq knows how to read this database of MACs -> IPs, so we'll keep it up to date every time we add a
        # system.
        with open(self.ethers_file, "w", encoding="UTF-8") as ethers_fh:
            for system in self.systems:
                ethers_entry = self._gen_single_ethers_entry(system)
                if ethers_entry:
                    ethers_fh.write(ethers_entry)

    def _gen_single_ethers_entry(
        self, system_obj: "System", duplicate_macs: Optional[List[str]] = None
    ):
        """
        Generate an ethers entry for a system, such as:
        00:1A:2B:3C:4D:5E\t1.2.3.4\n
        01:2B:3C:4D:5E:6F\t1.2.4.4\n
        """
        if not system_obj.is_management_supported(cidr_ok=False):
            self.logger.debug(
                "%s does not meet precondition: MAC, IPv4, or IPv6 address is required.",
                system_obj.name,
            )
            return ""

        output = ""
        for interface in system_obj.interfaces.values():
            mac = interface.mac_address
            ip_address = interface.ip_address
            if not mac:
                # can't write this w/o a MAC address
                continue
            if duplicate_macs and mac in duplicate_macs:
                # explicitly skipping mac address
                continue
            if ip_address != "":
                output += mac.upper() + "\t" + ip_address + "\n"
        return output

    def sync_single_ethers_entry(
        self, system: "System", duplicate_macs: Optional[List[str]] = None
    ):
        """
        This appends a new single system entry to the ethers file.

        :param system: A system to be added.
        """
        # dnsmasq knows how to read this database of MACs -> IPs, so we'll keep it up to date every time we add a
        # system.
        with open(self.ethers_file, "a", encoding="UTF-8") as ethers_fh:
            host_entry = self._gen_single_ethers_entry(system, duplicate_macs)
            if host_entry:
                ethers_fh.write(host_entry)

    def remove_single_ethers_entry(
        self,
        system: "System",
    ):
        """
        This adds a new single system entry to the ethers file.

        :param system: A system to be removed.
        """
        # dnsmasq knows how to read this database of MACs -> IPs, so we'll keep it up to date every time we add a
        # system.
        ethers_entry = self._gen_single_ethers_entry(system)
        if not ethers_entry:
            return
        mac_addresses = self._extract_mac_from_ethers_entry(ethers_entry)
        utils.remove_lines_in_file(self.ethers_file, mac_addresses)

    def _extract_mac_from_ethers_entry(self, ethers_entry: str) -> List[str]:
        """
        One ethers entry can contain multiple MAC addresses.
        This method transforms:

        00:1A:2B:3C:4D:5E\t1.2.3.4\n
        01:2B:3C:4D:5E:6F\t1.2.4.4\n

        To:

        ["00:1A:2B:3C:4D:5E", "01:2B:3C:4D:5E:6F"]
        """
        return [line.split("\t")[0] for line in ethers_entry.split("\n") if line]

    def remove_single_hosts_entry(self, system: "System"):
        """
        This removes a single system entry from the Cobbler hosts file.

        :param system: A system to be removed.
        """
        host_entry = self._gen_single_host_entry(system)
        if not host_entry:
            return
        utils.remove_lines_in_file(self.cobbler_hosts_file, [host_entry])

    def _gen_single_host_entry(
        self,
        system_obj: "System",
    ):
        if not system_obj.is_management_supported(cidr_ok=False):
            self.logger.debug(
                "%s does not meet precondition: MAC, IPv4, or IPv6 address is required.",
                system_obj.name,
            )
            return ""

        output = ""
        for _, interface in system_obj.interfaces.items():
            mac = interface.mac_address
            host = interface.dns_name
            cnames = " ".join(interface.cnames)
            ipv4 = interface.ip_address
            ipv6 = interface.ipv6_address
            if not mac:
                continue
            if host != "" and ipv6 != "":
                output += ipv6 + "\t" + host
            elif host != "" and ipv4 != "":
                output += ipv4 + "\t" + host
            if cnames:
                output += " " + cnames + "\n"
            else:
                output += "\n"
        return output

    def add_single_hosts_entry(
        self,
        system: "System",
    ):
        """
        This adds a single system entry to the hosts file.

        :param system: A system to be added.
        """
        host_entries = self._gen_single_host_entry(system)
        if not host_entries:
            return

        # This method can be used for editing, so
        # remove duplicate entries first
        with open(self.cobbler_hosts_file, "r", encoding="UTF-8") as fd:
            for host_line in fd:
                host_line = host_line.strip()
                if host_line and host_line in host_entries:
                    host_entries = host_entries.replace(f"{host_line}\n", "")

        if not host_entries.strip():
            # No new entries present, we should trigger a full sync
            self.regen_hosts()
            return

        with open(self.cobbler_hosts_file, "a", encoding="UTF-8") as regen_hosts_fd:
            regen_hosts_fd.write(host_entries)

    def regen_hosts(self) -> None:
        """
        This rewrites the hosts file and thus also rewrites the dns config.
        """
        # dnsmasq knows how to read this database for host info (other things may also make use of this later)
        with open(self.cobbler_hosts_file, "w", encoding="UTF-8") as regen_hosts_fd:
            for system in self.systems:
                host_entry = self._gen_single_host_entry(system)
                if host_entry:
                    regen_hosts_fd.write(host_entry)

    def restart_service(self) -> int:
        """
        This restarts the dhcp server and thus applied the newly written config files.
        """
        service_name = "dnsmasq"
        if self.settings.restart_dhcp:
            return_code_service_restart = utils.process_management.service_restart(
                service_name
            )
            if return_code_service_restart != 0:
                self.logger.error("%s service failed", service_name)
            return return_code_service_restart
        return 0


def get_manager(api: "CobblerAPI") -> _DnsmasqManager:
    """
    Creates a manager object to manage a dnsmasq server.

    :param api: The API to resolve all information with.
    :return: The object generated from the class.
    """
    # Singleton used, therefore ignoring 'global'
    global MANAGER  # pylint: disable=global-statement

    if not MANAGER:
        MANAGER = _DnsmasqManager(api)  # type: ignore
    return MANAGER
