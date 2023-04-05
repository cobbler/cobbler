"""
This is some of the code behind 'cobbler sync'.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>
# SPDX-FileCopyrightText: John Eckersberg <jeckersb@redhat.com>

import re
import socket
import time
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Union

from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.manager import ManagerModule

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


MANAGER = None


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "manage"


class MetadataZoneHelper:
    def __init__(
        self,
        forward_zones: List[str],
        reverse_zones: List[Tuple[str, str]],
        zone_include: str,
    ):
        self.forward_zones: List[str] = forward_zones
        self.reverse_zones: List[Tuple[str, str]] = reverse_zones
        self.zone_include = zone_include
        self.bind_master = ""


class _BindManager(ManagerModule):
    @staticmethod
    def what() -> str:
        """
        Identifies what this class is managing.

        :return: Always will return ``bind``.
        """
        return "bind"

    def __init__(self, api: "CobblerAPI"):
        super().__init__(api)

        self.settings_file = utils.namedconf_location()
        self.zonefile_base = self.settings.bind_zonefile_path + "/"

    def regen_hosts(self) -> None:
        """
        Not used.
        """

    @staticmethod
    def __expand_ipv6(address: str) -> str:
        """
        Expands an IPv6 address to long format i.e. ``xxxx:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx``

        This function was created by Chris Miller, approved for GLP use, taken verbatim from:
        https://forrst.com/posts/Python_Expand_Abbreviated_IPv6_Addresses-1kQ

        :param address: Shortened IPv6 address.
        :return: The full IPv6 address.
        """
        full_address = ""  # All groups
        expanded_address = ""  # Each group padded with leading zeroes
        valid_group_count = 8
        valid_group_size = 4
        if "::" not in address:  # All groups are already present
            full_address = address
        else:  # Consecutive groups of zeroes have been collapsed with "::"
            sides = address.split("::")
            groups_present = 0
            for side in sides:
                if len(side) > 0:
                    groups_present += len(side.split(":"))
            if len(sides[0]) > 0:
                full_address += sides[0] + ":"
            for _ in range(0, valid_group_count - groups_present):
                full_address += "0000:"
            if len(sides[1]) > 0:
                full_address += sides[1]
            if full_address[-1] == ":":
                full_address = full_address[:-1]
        groups = full_address.split(":")
        for group in groups:
            while len(group) < valid_group_size:
                group = "0" + group
            expanded_address += group + ":"
        if expanded_address[-1] == ":":
            expanded_address = expanded_address[:-1]
        return expanded_address

    def __forward_zones(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Returns a map of zones and the records that belong in them
        """
        zones: Dict[str, Dict[str, List[str]]] = {}
        forward_zones = self.settings.manage_forward_zones
        if not isinstance(forward_zones, list):  # type: ignore
            # Gracefully handle when user inputs only a single zone as a string instead of a list with only a single
            # item
            forward_zones = [forward_zones]

        for zone in forward_zones:
            zones[zone] = {}

        for system in self.systems:
            for (_, interface) in system.interfaces.items():
                host: str = interface.dns_name
                ipv4: str = interface.ip_address
                ipv6: str = interface.ipv6_address
                ipv6_sec_addrs: List[str] = interface.ipv6_secondaries
                if not system.is_management_supported(cidr_ok=False):
                    continue
                if not host:
                    # gotsta have some dns_name and ip or else!
                    continue
                if host.find(".") == -1:
                    continue

                # Match the longest zone! E.g. if you have a host a.b.c.d.e
                # if manage_forward_zones has:
                # - c.d.e
                # - b.c.d.e
                # then a.b.c.d.e should go in b.c.d.e
                best_match = ""
                for zone in zones:
                    if re.search(rf"\.{zone}$", host) and len(zone) > len(best_match):
                        best_match = zone

                # no match
                if best_match == "":
                    continue

                # strip the zone off the dns_name
                host = re.sub(rf"\.{best_match}$", "", host)

                # if we are to manage ipmi hosts, add that too
                if self.settings.bind_manage_ipmi:
                    if system.power_address != "":
                        power_address_is_ip = False
                        # see if the power address is an IP
                        try:
                            socket.inet_aton(system.power_address)
                            power_address_is_ip = True
                        except socket.error:
                            power_address_is_ip = False

                        # if the power address is an IP, then add it to the DNS with the host suffix of "-ipmi"
                        # TODO: Perhpas the suffix can be configurable through settings?
                        if power_address_is_ip:
                            ipmi_host = host + "-ipmi"
                            ipmi_ips: List[str] = [system.power_address]
                            try:
                                zones[best_match][ipmi_host] = (
                                    ipmi_ips + zones[best_match][ipmi_host]
                                )
                            except KeyError:
                                zones[best_match][ipmi_host] = ipmi_ips

                # Create a list of IP addresses for this host
                ips: List[str] = []
                if ipv4:
                    ips.append(ipv4)

                if ipv6:
                    ips.append(ipv6)

                if ipv6_sec_addrs:
                    ips += ipv6_sec_addrs

                if ips:
                    try:
                        zones[best_match][host] = ips + zones[best_match][host]
                    except KeyError:
                        zones[best_match][host] = ips

        return zones

    def __reverse_zones(self) -> Dict[Any, Any]:
        """
        Returns a map of zones and the records that belong in them

        :return: A dict with all zones.
        """
        zones: Dict[str, Dict[str, Union[str, List[str]]]] = {}
        reverse_zones = self.settings.manage_reverse_zones
        if not isinstance(reverse_zones, list):  # type: ignore
            # Gracefully handle when user inputs only a single zone as a string instead of a list with only a single
            # item
            reverse_zones = [reverse_zones]

        for zone in reverse_zones:
            # expand and IPv6 zones
            if ":" in zone:
                zone = (self.__expand_ipv6(zone + "::1"))[:19]
            zones[zone] = {}

        for system in self.systems:
            for (_, interface) in system.interfaces.items():
                host = interface.dns_name
                ip_address = interface.ip_address
                ipv6 = interface.ipv6_address
                ipv6_sec_addrs = interface.ipv6_secondaries
                if not system.is_management_supported(cidr_ok=False):
                    continue
                if not host or ((not ip_address) and (not ipv6)):
                    # gotta have some dns_name and ip or else!
                    continue

                if ip_address:
                    # Match the longest zone! E.g. if you have an ip 1.2.3.4
                    # if manage_reverse_zones has:
                    # - 1.2
                    # - 1.2.3
                    # then 1.2.3.4 should go in 1.2.3
                    best_match = ""
                    for zone in zones:
                        if re.search(rf"^{zone}\.", ip_address) and len(zone) > len(
                            best_match
                        ):
                            best_match = zone

                    if best_match != "":
                        # strip the zone off the front of the ip reverse the rest of the octets append the remainder
                        # + dns_name
                        ip_address = ip_address.replace(best_match, "", 1)
                        if ip_address[0] == ".":  # strip leading '.' if it's there
                            ip_address = ip_address[1:]
                        tokens = ip_address.split(".")
                        tokens.reverse()
                        ip_address = ".".join(tokens)
                        zones[best_match][ip_address] = host + "."

                if ipv6 or ipv6_sec_addrs:
                    ip6s: List[str] = []
                    if ipv6:
                        ip6s.append(ipv6)
                    for each_ipv6 in ip6s + ipv6_sec_addrs:
                        # convert the IPv6 address to long format
                        long_ipv6 = self.__expand_ipv6(each_ipv6)
                        # All IPv6 zones are forced to have the format xxxx:xxxx:xxxx:xxxx
                        zone = long_ipv6[:19]
                        ipv6_host_part = long_ipv6[20:]
                        tokens = list(re.sub(":", "", ipv6_host_part))
                        tokens.reverse()
                        ip_address = ".".join(tokens)
                        zones[zone][ip_address] = host + "."

        return zones

    def __write_named_conf(self) -> None:
        """
        Write out the named.conf main config file from the template.

        :raises OSError
        """
        settings_file = self.settings.bind_chroot_path + self.settings_file
        template_file = "/etc/cobbler/named.template"
        # forward_zones = self.settings.manage_forward_zones
        # reverse_zones = self.settings.manage_reverse_zones

        metadata = MetadataZoneHelper(list(self.__forward_zones().keys()), [], "")

        for zone in metadata.forward_zones:
            txt = f"""
zone "{zone}." {{
    type master;
    file "{zone}";
}};
"""
            metadata.zone_include = metadata.zone_include + txt

        for zone in self.__reverse_zones():
            # IPv6 zones are : delimited
            if ":" in zone:
                # if IPv6, assume xxxx:xxxx:xxxx:xxxx
                #                 0123456789012345678
                long_zone = (self.__expand_ipv6(zone + "::1"))[:19]
                tokens = list(re.sub(":", "", long_zone))
                tokens.reverse()
                arpa = ".".join(tokens) + ".ip6.arpa"
            else:
                # IPv4 address split by '.'
                tokens = zone.split(".")
                tokens.reverse()
                arpa = ".".join(tokens) + ".in-addr.arpa"
                #
            metadata.reverse_zones.append((zone, arpa))
            txt = f"""
zone "{arpa}." {{
    type master;
    file "{zone}";
}};
"""
            metadata.zone_include = metadata.zone_include + txt

        try:
            with open(template_file, "r", encoding="UTF-8") as template_fd:
                template_data = template_fd.read()
        except Exception as error:
            raise OSError(
                f"error reading template from file: {template_file}"
            ) from error

        self.logger.info("generating %s", settings_file)
        self.templar.render(template_data, metadata.__dict__, settings_file)

    def __write_secondary_conf(self) -> None:
        """
        Write out the secondary.conf secondary config file from the template.
        """
        settings_file = self.settings.bind_chroot_path + "/etc/secondary.conf"
        template_file = "/etc/cobbler/secondary.template"
        # forward_zones = self.settings.manage_forward_zones
        # reverse_zones = self.settings.manage_reverse_zones

        metadata = MetadataZoneHelper(list(self.__forward_zones().keys()), [], "")

        for zone in metadata.forward_zones:
            txt = f"""
zone "{zone}." {{
    type slave;
    masters {{
        {self.settings.bind_master};
    }};
    file "data/{zone}";
}};
"""
            metadata.zone_include = metadata.zone_include + txt

        for zone in self.__reverse_zones():
            # IPv6 zones are : delimited
            if ":" in zone:
                # if IPv6, assume xxxx:xxxx:xxxx:xxxx for the zone
                #                 0123456789012345678
                long_zone = (self.__expand_ipv6(zone + "::1"))[:19]
                tokens = list(re.sub(":", "", long_zone))
                tokens.reverse()
                arpa = ".".join(tokens) + ".ip6.arpa"
            else:
                # IPv4 zones split by '.'
                tokens = zone.split(".")
                tokens.reverse()
                arpa = ".".join(tokens) + ".in-addr.arpa"
                #
            metadata.reverse_zones.append((zone, arpa))
            txt = f"""
zone "{arpa}." {{
    type slave;
    masters {{
        {self.settings.bind_master};
    }};
    file "data/{zone}";
}};
"""
            metadata.zone_include = metadata.zone_include + txt
            metadata.bind_master = self.settings.bind_master

        try:
            with open(template_file, "r", encoding="UTF-8") as template_fd:
                template_data = template_fd.read()
        except Exception as error:
            raise OSError(
                f"error reading template from file: {template_file}"
            ) from error

        self.logger.info("generating %s", settings_file)
        self.templar.render(template_data, metadata.__dict__, settings_file)

    def __ip_sort(self, ips: List[str]) -> List[str]:
        """
        Sorts IP addresses (or partial addresses) in a numerical fashion per-octet or quartet

        :param ips: A list of all IP addresses (v6 and v4 mixed possible) which shall be sorted.
        :return: The list with sorted IP addresses.
        """
        quartets: List[List[int]] = []
        octets: List[List[int]] = []
        for each_ip in ips:
            # IPv6 addresses are ':' delimited
            if ":" in each_ip:
                # IPv6
                # strings to integer quartet chunks so we can sort numerically
                quartets.append([int(i, 16) for i in each_ip.split(":")])
            else:
                # IPv4
                # strings to integer octet chunks so we can sort numerically
                octets.append([int(i) for i in each_ip.split(".")])

        quartets.sort()
        octets.sort()

        # integers back to four character hex strings
        quartets_str = [[format(i, "04x") for i in x] for x in quartets]
        # integers back to strings
        octets_str = [[str(i) for i in x] for x in octets]
        return [".".join(i) for i in octets_str] + [":".join(i) for i in quartets_str]

    def __pretty_print_host_records(
        self, hosts: Dict[str, Any], rectype: str = "A", rclass: str = "IN"
    ) -> str:
        """
        Format host records by order and with consistent indentation

        :param hosts: The hosts to pretty print.
        :param rectype: The record type.
        :param rclass: The record class.
        :return: A string with all pretty printed hosts.
        """

        # Warns on hosts without dns_name, need to iterate over system to name the
        # particular system

        for system in self.systems:
            for (name, interface) in system.interfaces.items():
                if interface.dns_name == "":
                    self.logger.info(
                        "Warning: dns_name unspecified in the system: %s, while writing host records",
                        system.name,
                    )

        names = list(hosts.keys())
        if not names:
            return ""  # zones with no hosts

        if rectype == "PTR":
            names = self.__ip_sort(names)
        else:
            names.sort()

        max_name = max([len(i) for i in names])

        result = ""
        for name in names:
            spacing = " " * (max_name - len(name))
            my_name = f"{name}{spacing}"
            my_host_record = hosts[name]
            my_host_list = []
            if isinstance(my_host_record, str):
                my_host_list = [my_host_record]
            else:
                my_host_list = my_host_record
            for my_host in my_host_list:
                my_rectype = rectype[:]
                if rectype == "A":
                    if ":" in my_host:
                        my_rectype = "AAAA"
                    else:
                        my_rectype = "A   "
                result += f"{my_name}  {rclass}  {my_rectype}  {my_host};\n"
        return result

    def __pretty_print_cname_records(
        self, hosts: Dict[str, Any], rectype: str = "CNAME"
    ) -> str:
        """
        Format CNAMEs and with consistent indentation

        :param hosts: This parameter is currently unused.
        :param rectype: The type of record which shall be pretty printed.
        :return: The pretty printed version of the cname records.
        """
        result = ""

        # This loop warns and skips the host without dns_name instead of outright exiting
        # Which results in empty records without any warning to the users

        for system in self.systems:
            for (_, interface) in system.interfaces.items():
                cnames = interface.cnames

                try:
                    if interface.dns_name != "":
                        dnsname = interface.dns_name.split(".")[0]
                        for cname in cnames:
                            result += f"{cname.split('.')[0]}  {rectype}  {dnsname};\n"
                    else:
                        self.logger.warning(
                            'CNAME generation for system "%s" was skipped due to a missing dns_name entry while writing'
                            "records!",
                            system.name,
                        )
                        continue
                except Exception as exception:
                    self.logger.exception(
                        "Unspecified error during creation of CNAME for bind9 records!",
                        exc_info=exception,
                    )

        return result

    def __write_zone_files(self) -> None:
        """
        Write out the forward and reverse zone files for all configured zones
        """
        default_template_file = "/etc/cobbler/zone.template"
        cobbler_server = self.settings.server
        # this could be a config option too
        serial_filename = "/var/lib/cobbler/bind_serial"
        # need a counter for new bind format
        serial = time.strftime("%Y%m%d00")
        try:
            with open(serial_filename, "r", encoding="UTF-8") as serialfd:
                old_serial = serialfd.readline()
                # same date
                if serial[0:8] == old_serial[0:8]:
                    if int(old_serial[8:10]) < 99:
                        serial = f"{serial[0:8]}{int(old_serial[8:10]) + 1:.2d}"
        except Exception:
            pass

        with open(serial_filename, "w", encoding="UTF-8") as serialfd:
            serialfd.write(serial)

        forward = self.__forward_zones()
        reverse = self.__reverse_zones()

        try:
            with open(default_template_file, "r", encoding="UTF-8") as template_fd:
                default_template_data = template_fd.read()
        except Exception as error:
            raise CX(
                f"error reading template from file: {default_template_file}"
            ) from error

        zonefileprefix = self.settings.bind_chroot_path + self.zonefile_base

        for (zone, hosts) in forward.items():
            metadata = {
                "cobbler_server": cobbler_server,
                "serial": serial,
                "zonename": zone,
                "zonetype": "forward",
                "cname_record": "",
                "host_record": "",
            }

            if ":" in zone:
                long_zone = (self.__expand_ipv6(zone + "::1"))[:19]
                tokens = list(re.sub(":", "", long_zone))
                tokens.reverse()
                zone_origin = ".".join(tokens) + ".ip6.arpa."
            else:
                zone_origin = ""
            # grab zone-specific template if it exists
            try:
                with open(
                    f"/etc/cobbler/zone_templates/{zone}", encoding="UTF-8"
                ) as zone_fd:
                    # If this is an IPv6 zone, set the origin to the zone for this
                    # template
                    if zone_origin:
                        template_data = (
                            r"\$ORIGIN " + zone_origin + "\n" + zone_fd.read()
                        )
                    else:
                        template_data = zone_fd.read()
            except Exception:
                # If this is an IPv6 zone, set the origin to the zone for this
                # template
                if zone_origin:
                    template_data = (
                        r"\$ORIGIN " + zone_origin + "\n" + default_template_data
                    )
                else:
                    template_data = default_template_data

            metadata["cname_record"] = self.__pretty_print_cname_records(hosts)
            metadata["host_record"] = self.__pretty_print_host_records(hosts)

            zonefilename = zonefileprefix + zone
            self.logger.info("generating (forward) %s", zonefilename)
            self.templar.render(template_data, metadata, zonefilename)

        for (zone, hosts) in reverse.items():
            metadata = {
                "cobbler_server": cobbler_server,
                "serial": serial,
                "zonename": zone,
                "zonetype": "reverse",
                "cname_record": "",
                "host_record": "",
            }

            # grab zone-specific template if it exists
            try:
                with open(
                    f"/etc/cobbler/zone_templates/{zone}", encoding="UTF-8"
                ) as zone_fd:
                    template_data = zone_fd.read()
            except Exception:
                template_data = default_template_data

            metadata["cname_record"] = self.__pretty_print_cname_records(hosts)
            metadata["host_record"] = self.__pretty_print_host_records(
                hosts, rectype="PTR"
            )

            zonefilename = zonefileprefix + zone
            self.logger.info("generating (reverse) %s", zonefilename)
            self.templar.render(template_data, metadata, zonefilename)

    def write_configs(self) -> None:
        """
        BIND files are written when ``manage_dns`` is set in our settings.
        """

        self.__write_named_conf()
        self.__write_secondary_conf()
        self.__write_zone_files()

    def restart_service(self) -> int:
        """
        This syncs the bind server with it's new config files.
        Basically this restarts the service to apply the changes.
        """
        # TODO: Reuse the utils method for service restarts
        named_service_name = utils.named_service_name()
        dns_restart_command = ["service", named_service_name, "restart"]
        ret: int = utils.subprocess_call(dns_restart_command, shell=False)
        if ret != 0:
            self.logger.error("%s service failed", named_service_name)
        return ret


def get_manager(api: "CobblerAPI") -> "_BindManager":
    """
    This returns the object to manage a BIND server located locally on the Cobbler server.

    :param api: The API to resolve all information with.
    :return: The BindManger object to manage bind with.
    """
    # Singleton used, therefore ignoring 'global'
    global MANAGER  # pylint: disable=global-statement

    if not MANAGER:
        MANAGER = _BindManager(api)  # type: ignore
    return MANAGER
