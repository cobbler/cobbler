"""
This is some of the code behind 'cobbler sync'.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>
# SPDX-FileCopyrightText: John Eckersberg <jeckersb@redhat.com>

import shutil
import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Set

from cobbler import enums, utils
from cobbler.enums import Archs
from cobbler.modules.managers import DhcpManagerModule
from cobbler.utils import process_management

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.distro import Distro
    from cobbler.items.profile import Profile
    from cobbler.items.system import NetworkInterface, System

MANAGER = None


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "manage"


class _IscManager(DhcpManagerModule):
    @staticmethod
    def what() -> str:
        """
        Static method to identify the manager.

        :return: Always "isc".
        """
        return "isc"

    def __init__(self, api: "CobblerAPI"):
        super().__init__(api)

        self.settings_file_v4 = utils.dhcpconf_location(enums.DHCP.V4)
        self.settings_file_v6 = utils.dhcpconf_location(enums.DHCP.V6)

        # cache config to allow adding systems incrementally
        self.config: Dict[str, Any] = {}
        self.generic_entry_cnt = 0

    def sync_single_system(self, system: "System"):
        """
        Update the config with data for a single system, write it to the filesysemt, and restart DHCP service.
        :param system: System object to generate the config for.
        """
        if not self.config:
            # cache miss, need full sync for consistent data
            return self.sync()

        profile: Optional["Profile"] = system.get_conceptual_parent()  # type: ignore
        distro: Optional["Distro"] = profile.get_conceptual_parent()  # type: ignore
        blend_data = utils.blender(self.api, False, system)

        system_config = self._gen_system_config(system, blend_data, distro)

        if all(
            mac in self.config.get("dhcp_tags", {}).get(dhcp_tag, {})
            for dhcp_tag, interface in system_config.items()
            for mac in interface
        ):
            # All interfaces in the added system are already cached. Therefore,
            # user might have removed an interface and we don't know which.
            # Trigger full sync.
            return self.sync()

        self.config = utils.merge_dicts_recursive(
            self.config,
            {"dhcp_tags": system_config},
        )
        self.config["date"] = time.asctime(time.gmtime())
        self._write_configs(self.config)
        return self.restart_service()

    def remove_single_system(self, system_obj: "System") -> None:
        if not self.config:
            self.write_configs()
            return

        profile: Optional["Profile"] = system_obj.get_conceptual_parent()  # type: ignore
        distro: Optional["Distro"] = profile.get_conceptual_parent()  # type: ignore
        blend_data = utils.blender(self.api, False, system_obj)

        system_config = self._gen_system_config(system_obj, blend_data, distro)
        for dhcp_tag, mac_addresses in system_config.items():
            for mac_address in mac_addresses:
                self.config.get("dhcp_tags", {}).get(dhcp_tag, {}).pop(mac_address, "")
        self.config["date"] = time.asctime(time.gmtime())
        self._write_configs(self.config)
        self.restart_service()

    def _gen_system_config(
        self,
        system_obj: "System",
        system_blend_data: Dict[str, Any],
        distro_obj: Optional["Distro"],
    ) -> Dict[str, Any]:
        """
        Generate DHCP config for a single system.

        :param system_obj: System to generate DHCP config for
        :param system_blend_data: utils.blender() data for the System
        :param distro_object: Optional, is used to access distro-specific information like arch when present
        """
        dhcp_tags: Dict[str, Any] = {"default": {}}
        processed_system_master_interfaces: Set[str] = set()
        ignore_macs: Set[str] = set()
        if not system_obj.is_management_supported(cidr_ok=False):
            self.logger.debug(
                "%s does not meet precondition: MAC, IPv4, or IPv6 address is required.",
                system_obj.name,
            )
            return {}

        profile: Optional["Profile"] = system_obj.get_conceptual_parent()  # type: ignore
        for iface_name, iface_obj in system_obj.interfaces.items():
            iface = iface_obj.to_dict()
            mac = iface_obj.mac_address
            if (
                not self.settings.always_write_dhcp_entries
                and not system_blend_data["netboot_enabled"]
                and iface["static"]
            ):
                continue
            if not mac:
                self.logger.warning("%s has no MAC address", system_obj.name)
                continue

            iface["gateway"] = iface_obj.if_gateway or system_obj.gateway
            if iface["interface_type"] in (
                "bond_slave",
                "bridge_slave",
                "bonded_bridge_slave",
            ):
                if iface["interface_master"] not in system_obj.interfaces:
                    # Can't write DHCP entry: master interface does not exist
                    continue

                master_name = iface["interface_master"]
                master_iface = system_obj.interfaces[master_name]
                # There may be multiple bonded interfaces, need composite index
                system_master_name = f"{system_obj.name}-{master_name}"
                if system_master_name not in processed_system_master_interfaces:
                    processed_system_master_interfaces.add(system_master_name)
                else:
                    ignore_macs.add(mac)
                # IPv4
                iface["netmask"] = master_iface.netmask
                iface["ip_address"] = master_iface.ip_address
                if not iface["ip_address"]:
                    iface["ip_address"] = self._find_ip_addr(
                        system_obj.interfaces, prefix=master_name, ip_version="ipv4"
                    )
                # IPv6
                iface["ipv6_address"] = master_iface.ipv6_address
                if not iface["ipv6_address"]:
                    iface["ipv6_address"] = self._find_ip_addr(
                        system_obj.interfaces, prefix=master_name, ip_version="ipv6"
                    )
                # common
                host = master_iface.dns_name
                dhcp_tag = master_iface.dhcp_tag
            else:
                # TODO: simplify _slave / non_slave branches
                host = iface["dns_name"]
                dhcp_tag = iface["dhcp_tag"]

            if distro_obj is not None:
                iface["distro"] = distro_obj.to_dict()
            if profile is not None:
                iface["profile"] = profile.to_dict()  # type: ignore
            if host:
                if iface_name == "eth0":
                    iface["name"] = host
                else:
                    iface["name"] = f"{host}-{iface_name}"
            else:
                self.generic_entry_cnt += 1
                iface["name"] = f"generic{self.generic_entry_cnt:d}"

            for key in (
                "next_server_v6",
                "next_server_v4",
                "filename",
                "netboot_enabled",
                "hostname",
                "enable_ipxe",
                "name_servers",
            ):
                iface[key] = system_blend_data[key]
            iface["owner"] = system_blend_data["name"]
            # esxi
            if distro_obj is not None and distro_obj.os_version.startswith("esxi"):
                iface["filename_esxi"] = (
                    "esxi/system",
                    # config filename can be None
                    system_obj.get_config_filename(interface=iface_name, loader="pxe")
                    or "",
                    "mboot.efi",
                )
            elif distro_obj is not None and not iface["filename"]:
                if distro_obj.arch in (
                    Archs.PPC,
                    Archs.PPC64,
                    Archs.PPC64LE,
                    Archs.PPC64EL,
                ):
                    iface["filename"] = "grub/grub.ppc64le"
                elif distro_obj.arch == Archs.AARCH64:
                    iface["filename"] = "grub/grubaa64.efi"

            if not dhcp_tag:
                dhcp_tag = system_blend_data.get("dhcp_tag", "")
                if dhcp_tag == "":
                    dhcp_tag = "default"
            if dhcp_tag not in dhcp_tags:
                dhcp_tags[dhcp_tag] = {mac: iface}
            else:
                dhcp_tags[dhcp_tag][mac] = iface

        for macs in dhcp_tags.values():
            for mac in macs:
                if mac in ignore_macs:
                    del macs[mac]

        return dhcp_tags

    def _find_ip_addr(
        self,
        interfaces: Dict[str, "NetworkInterface"],
        prefix: str,
        ip_version: str,
    ) -> str:
        """Find the first interface with an IP address that begins with prefix."""

        if ip_version.lower() == "ipv4":
            attr_name = "ip_address"
        elif ip_version.lower() == "ipv6":
            attr_name = "ipv6_address"
        else:
            return ""

        for name, obj in interfaces:
            if name.startswith(prefix + ".") and hasattr(obj, attr_name):
                return getattr(obj, attr_name)
        return ""

    def gen_full_config(self) -> Dict[str, Any]:
        """Generate DHCP configuration for all systems."""
        dhcp_tags: Dict[str, Any] = {"default": {}}
        self.generic_entry_cnt = 0
        for system in self.systems:
            profile: Optional["Profile"] = system.get_conceptual_parent()  # type: ignore
            if profile is None:
                continue
            distro: Optional["Distro"] = profile.get_conceptual_parent()  # type: ignore
            blended_system = utils.blender(self.api, False, system)
            new_tags = self._gen_system_config(system, blended_system, distro)
            dhcp_tags = utils.merge_dicts_recursive(dhcp_tags, new_tags)

        metadata = {
            "date": time.asctime(time.gmtime()),
            "cobbler_server": f"{self.settings.server}:{self.settings.http_port}",
            "next_server_v4": self.settings.next_server_v4,
            "next_server_v6": self.settings.next_server_v6,
            "dhcp_tags": dhcp_tags,
        }
        return metadata

    def _write_config(
        self,
        config_data: Dict[Any, Any],
        template_file: str,
        settings_file: str,
    ) -> None:
        """DHCP files are written when ``manage_dhcp_v4`` or ``manage_dhcp_v6``
        is set in the settings for the respective version. DHCPv4 files are
        written when ``manage_dhcp_v4`` is set in our settings.

        :param config_data: DHCP data to write.
        :param template_file: The location of the DHCP template.
        :param settings_file: The location of the final config file.
        """
        try:
            with open(template_file, "r", encoding="UTF-8") as template_fd:
                template_data = template_fd.read()
        except OSError as e:
            self.logger.error("Can't read dhcp template '%s':\n%s", template_file, e)
            return
        config_copy = config_data.copy()  # template rendering changes the passed dict
        self.logger.info("Writing %s", settings_file)
        self.templar.render(template_data, config_copy, settings_file)

    def write_v4_config(
        self,
        config_data: Optional[Dict[Any, Any]] = None,
        template_file: str = "/etc/cobbler/dhcp.template",
    ):
        """Write DHCP files for IPv4.

        :param config_data: DHCP data to write.
        :param template_file: The location of the DHCP template.
        :param settings_file: The location of the final config file.
        """
        if not config_data:
            raise ValueError("No config to write.")
        self._write_config(config_data, template_file, self.settings_file_v4)

    def write_v6_config(
        self,
        config_data: Optional[Dict[Any, Any]] = None,
        template_file: str = "/etc/cobbler/dhcp6.template",
    ):
        """Write DHCP files for IPv6.

        :param config_data: DHCP data to write.
        :param template_file: The location of the DHCP template.
        :param settings_file: The location of the final config file.
        """
        if not config_data:
            raise ValueError("No config to write.")
        self._write_config(config_data, template_file, self.settings_file_v6)

    def restart_dhcp(self, service_name: str, version: int) -> int:
        """
        This syncs the dhcp server with it's new config files.
        Basically this restarts the service to apply the changes.

        :param service_name: The name of the DHCP service.
        """
        dhcpd_path = shutil.which(service_name)
        if dhcpd_path is None:
            self.logger.error("%s path could not be found", service_name)
            return -1
        return_code_service_restart = utils.subprocess_call(
            [dhcpd_path, f"-{version}", "-t", "-q"], shell=False
        )
        if return_code_service_restart != 0:
            self.logger.error("Testing config - %s -t failed", service_name)
        if version == 4:
            return_code_service_restart = process_management.service_restart(
                service_name
            )
        else:
            return_code_service_restart = process_management.service_restart(
                f"{service_name}{version}"
            )
        if return_code_service_restart != 0:
            self.logger.error("%s service failed", service_name)
        return return_code_service_restart

    def write_configs(self) -> None:
        """
        DHCP files are written when ``manage_dhcp`` is set in our settings.

        :raises OSError
        :raises ValueError
        """
        self.generic_entry_cnt = 0
        self.config = self.gen_full_config()
        self._write_configs(self.config)

    def _write_configs(self, data: Optional[Dict[Any, Any]] = None) -> None:
        if not data:
            raise ValueError("No config to write.")

        if self.settings.manage_dhcp_v4:
            self.write_v4_config(data)
        if self.settings.manage_dhcp_v6:
            self.write_v6_config(data)

    def restart_service(self) -> int:
        if not self.settings.restart_dhcp:
            return 0

        # Even if one fails, try both and return an error
        ret = 0
        service = utils.dhcp_service_name()
        if self.settings.manage_dhcp_v4:
            ret |= self.restart_dhcp(service, 4)
        if self.settings.manage_dhcp_v6:
            ret |= self.restart_dhcp(service, 6)
        return ret


def get_manager(api: "CobblerAPI") -> _IscManager:
    """
    Creates a manager object to manage an isc dhcp server.

    :param api: The API which holds all information in the current Cobbler instance.
    :return: The object to manage the server with.
    """
    # Singleton used, therefore ignoring 'global'
    global MANAGER  # pylint: disable=global-statement

    if not MANAGER:
        MANAGER = _IscManager(api)  # type: ignore
    return MANAGER
