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

import re
import socket
import time

from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.manager import ManagerModule

MANAGER = None


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "manage"


class _BindManager(ManagerModule):

    @staticmethod
    def what() -> str:
        """
        Identifies what this class is managing.

        :return: Always will return ``bind``.
        """
        return "bind"

    def __init__(self, api):
        super().__init__(api)

        self.settings_file = utils.namedconf_location()
        self.zonefile_base = self.settings.bind_zonefile_path + "/"

    def regen_hosts(self):
        """
        Not used.
        """
        pass

    def __expand_IPv6(self, address):
        """
        Expands an IPv6 address to long format i.e. ``xxxx:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx``

        This function was created by Chris Miller, approved for GLP use, taken verbatim from:
        http://forrst.com/posts/Python_Expand_Abbreviated_IPv6_Addresses-1kQ

        :param address: Shortened IPv6 address.
        :return: The full IPv6 address.
        """
        fullAddress = ""            # All groups
        expandedAddress = ""        # Each group padded with leading zeroes
        validGroupCount = 8
        validGroupSize = 4
        if "::" not in address:     # All groups are already present
            fullAddress = address
        else:                       # Consecutive groups of zeroes have been collapsed with "::"
            sides = address.split("::")
            groupsPresent = 0
            for side in sides:
                if len(side) > 0:
                    groupsPresent += len(side.split(":"))
            if len(sides[0]) > 0:
                fullAddress += sides[0] + ":"
            for i in range(0, validGroupCount - groupsPresent):
                fullAddress += "0000:"
            if len(sides[1]) > 0:
                fullAddress += sides[1]
            if fullAddress[-1] == ":":
                fullAddress = fullAddress[:-1]
        groups = fullAddress.split(":")
        for group in groups:
            while len(group) < validGroupSize:
                group = "0" + group
            expandedAddress += group + ":"
        if expandedAddress[-1] == ":":
            expandedAddress = expandedAddress[:-1]
        return expandedAddress

    def __forward_zones(self):
        """
        Returns a map of zones and the records that belong in them
        """
        zones = {}
        forward_zones = self.settings.manage_forward_zones
        if not isinstance(forward_zones, list):
            # Gracefully handle when user inputs only a single zone as a string instead of a list with only a single
            # item
            forward_zones = [forward_zones]

        for zone in forward_zones:
            zones[zone] = {}

        for system in self.systems:
            for (name, interface) in system.interfaces.items():
                host = interface.dns_name
                ip = interface.ip_address
                ipv6 = interface.ipv6_address
                ipv6_sec_addrs = interface.ipv6_secondaries
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
                best_match = ''
                for zone in zones.keys():
                    if re.search(r'\.%s$' % zone, host) and len(zone) > len(best_match):
                        best_match = zone

                # no match
                if best_match == '':
                    continue

                # strip the zone off the dns_name
                host = re.sub(r'\.%s$' % best_match, '', host)

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
                            ipmi_ips = []
                            ipmi_ips.append(system.power_address)
                            try:
                                zones[best_match][ipmi_host] = ipmi_ips + zones[best_match][ipmi_host]
                            except KeyError:
                                zones[best_match][ipmi_host] = ipmi_ips

                # Create a list of IP addresses for this host
                ips = []
                if ip:
                    ips.append(ip)

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

    def __reverse_zones(self):
        """
        Returns a map of zones and the records that belong in them

        :return: A dict with all zones.
        """
        zones = {}
        reverse_zones = self.settings.manage_reverse_zones
        if not isinstance(reverse_zones, list):
            # Gracefully handle when user inputs only a single zone as a string instead of a list with only a single
            # item
            reverse_zones = [reverse_zones]

        for zone in reverse_zones:
            # expand and IPv6 zones
            if ":" in zone:
                zone = (self.__expand_IPv6(zone + '::1'))[:19]
            zones[zone] = {}

        for system in self.systems:
            for (name, interface) in system.interfaces.items():
                host = interface.dns_name
                ip = interface.ip_address
                ipv6 = interface.ipv6_address
                ipv6_sec_addrs = interface.ipv6_secondaries
                if not system.is_management_supported(cidr_ok=False):
                    continue
                if not host or ((not ip) and (not ipv6)):
                    # gotta have some dns_name and ip or else!
                    continue

                if ip:
                    # Match the longest zone! E.g. if you have an ip 1.2.3.4
                    # if manage_reverse_zones has:
                    # - 1.2
                    # - 1.2.3
                    # then 1.2.3.4 should go in 1.2.3
                    best_match = ''
                    for zone in zones.keys():
                        if re.search(r'^%s\.' % zone, ip) and len(zone) > len(best_match):
                            best_match = zone

                    if best_match != '':
                        # strip the zone off the front of the ip reverse the rest of the octets append the remainder
                        # + dns_name
                        ip = ip.replace(best_match, '', 1)
                        if ip[0] == '.':        # strip leading '.' if it's there
                            ip = ip[1:]
                        tokens = ip.split('.')
                        tokens.reverse()
                        ip = '.'.join(tokens)
                        zones[best_match][ip] = host + '.'

                if ipv6 or ipv6_sec_addrs:
                    ip6s = []
                    if ipv6:
                        ip6s.append(ipv6)
                    for each_ipv6 in ip6s + ipv6_sec_addrs:
                        # convert the IPv6 address to long format
                        long_ipv6 = self.__expand_IPv6(each_ipv6)
                        # All IPv6 zones are forced to have the format xxxx:xxxx:xxxx:xxxx
                        zone = long_ipv6[:19]
                        ipv6_host_part = long_ipv6[20:]
                        tokens = list(re.sub(':', '', ipv6_host_part))
                        tokens.reverse()
                        ip = '.'.join(tokens)
                        zones[zone][ip] = host + '.'

        return zones

    def __write_named_conf(self):
        """
        Write out the named.conf main config file from the template.

        :raises OSError
        """
        settings_file = self.settings.bind_chroot_path + self.settings_file
        template_file = "/etc/cobbler/named.template"
        # forward_zones = self.settings.manage_forward_zones
        # reverse_zones = self.settings.manage_reverse_zones

        metadata = {'forward_zones': self.__forward_zones().keys(),
                    'reverse_zones': [],
                    'zone_include': ''}

        for zone in metadata['forward_zones']:
            txt = """
zone "%(zone)s." {
    type master;
    file "%(zone)s";
};
""" % {'zone': zone}
            metadata['zone_include'] = metadata['zone_include'] + txt

        for zone in self.__reverse_zones().keys():
            # IPv6 zones are : delimited
            if ":" in zone:
                # if IPv6, assume xxxx:xxxx:xxxx:xxxx
                #                 0123456789012345678
                long_zone = (self.__expand_IPv6(zone + '::1'))[:19]
                tokens = list(re.sub(':', '', long_zone))
                tokens.reverse()
                arpa = '.'.join(tokens) + '.ip6.arpa'
            else:
                # IPv4 address split by '.'
                tokens = zone.split('.')
                tokens.reverse()
                arpa = '.'.join(tokens) + '.in-addr.arpa'
                #
            metadata['reverse_zones'].append((zone, arpa))
            txt = """
zone "%(arpa)s." {
    type master;
    file "%(zone)s";
};
""" % {'arpa': arpa, 'zone': zone}
            metadata['zone_include'] = metadata['zone_include'] + txt

        try:
            f2 = open(template_file, "r")
        except:
            raise OSError("error reading template from file: %s" % template_file)
        template_data = ""
        template_data = f2.read()
        f2.close()

        self.logger.info("generating %s", settings_file)
        self.templar.render(template_data, metadata, settings_file)

    def __write_secondary_conf(self):
        """
        Write out the secondary.conf secondary config file from the template.
        """
        settings_file = self.settings.bind_chroot_path + '/etc/secondary.conf'
        template_file = "/etc/cobbler/secondary.template"
        # forward_zones = self.settings.manage_forward_zones
        # reverse_zones = self.settings.manage_reverse_zones

        metadata = {'forward_zones': self.__forward_zones().keys(),
                    'reverse_zones': [],
                    'zone_include': ''}

        for zone in metadata['forward_zones']:
            txt = """
zone "%(zone)s." {
    type slave;
    masters {
        %(master)s;
    };
    file "data/%(zone)s";
};
""" % {'zone': zone, 'master': self.settings.bind_master}
            metadata['zone_include'] = metadata['zone_include'] + txt

        for zone in self.__reverse_zones().keys():
            # IPv6 zones are : delimited
            if ":" in zone:
                # if IPv6, assume xxxx:xxxx:xxxx:xxxx for the zone
                #                 0123456789012345678
                long_zone = (self.__expand_IPv6(zone + '::1'))[:19]
                tokens = list(re.sub(':', '', long_zone))
                tokens.reverse()
                arpa = '.'.join(tokens) + '.ip6.arpa'
            else:
                # IPv4 zones split by '.'
                tokens = zone.split('.')
                tokens.reverse()
                arpa = '.'.join(tokens) + '.in-addr.arpa'
                #
            metadata['reverse_zones'].append((zone, arpa))
            txt = """
zone "%(arpa)s." {
    type slave;
    masters {
        %(master)s;
    };
    file "data/%(zone)s";
};
""" % {'arpa': arpa, 'zone': zone, 'master': self.settings.bind_master}
            metadata['zone_include'] = metadata['zone_include'] + txt
            metadata['bind_master'] = self.settings.bind_master

        try:
            f2 = open(template_file, "r")
        except:
            raise OSError("error reading template from file: %s" % template_file)
        template_data = ""
        template_data = f2.read()
        f2.close()

        self.logger.info("generating %s", settings_file)
        self.templar.render(template_data, metadata, settings_file)

    def __ip_sort(self, ips: list):
        """
        Sorts IP addresses (or partial addresses) in a numerical fashion per-octet or quartet

        :param ips: A list of all IP addresses (v6 and v4 mixed possible) which shall be sorted.
        :return: The list with sorted IP addresses.
        """
        quartets = []
        octets = []
        for each_ip in ips:
            # IPv6 addresses are ':' delimited
            if ":" in each_ip:
                # IPv6
                # strings to integer quartet chunks so we can sort numerically
                quartets.append([int(i, 16) for i in each_ip.split(':')])
            else:
                # IPv4
                # strings to integer octet chunks so we can sort numerically
                octets.append([int(i) for i in each_ip.split('.')])
        quartets.sort()
        # integers back to four character hex strings
        quartets = [[format(i, '04x') for i in x] for x in quartets]
        #
        octets.sort()
        # integers back to strings
        octets = [[str(i) for i in x] for x in octets]
        #
        return ['.'.join(i) for i in octets] + [':'.join(i) for i in quartets]

    def __pretty_print_host_records(self, hosts, rectype: str = 'A', rclass: str = 'IN') -> str:
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
                    self.logger.info("Warning: dns_name unspecified in the system: %s, while writing host records",
                                     system.name)

        names = [k for k, v in hosts.items()]
        if not names:
            return ''  # zones with no hosts

        if rectype == 'PTR':
            names = self.__ip_sort(names)
        else:
            names.sort()

        max_name = max([len(i) for i in names])

        s = ""
        for name in names:
            spacing = " " * (max_name - len(name))
            my_name = "%s%s" % (name, spacing)
            my_host_record = hosts[name]
            my_host_list = []
            if isinstance(my_host_record, str):
                my_host_list = [my_host_record]
            else:
                my_host_list = my_host_record
            for my_host in my_host_list:
                my_rectype = rectype[:]
                if rectype == 'A':
                    if ":" in my_host:
                        my_rectype = 'AAAA'
                    else:
                        my_rectype = 'A   '
                s += "%s  %s  %s  %s;\n" % (my_name, rclass, my_rectype, my_host)
        return s

    def __pretty_print_cname_records(self, hosts, rectype: str = 'CNAME'):
        """
        Format CNAMEs and with consistent indentation

        :param hosts: This parameter is currently unused.
        :param rectype: The type of record which shall be pretty printed.
        :return: The pretty printed version of the cname records.
        """
        s = ""

        # This loop warns and skips the host without dns_name instead of outright exiting
        # Which results in empty records without any warning to the users

        for system in self.systems:
            for (name, interface) in system.interfaces.items():
                cnames = interface.cnames

                try:
                    if interface.get("dns_name", "") != "":
                        dnsname = interface.dns_name.split('.')[0]
                        for cname in cnames:
                            s += "%s  %s  %s;\n" % (cname.split('.')[0], rectype, dnsname)
                    else:
                        self.logger.info("Warning: dns_name unspecified in the system: %s, Skipped!, while writing "
                                         "cname records", system.name)
                        continue
                except:
                    pass

        return s

    def __write_zone_files(self):
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
            serialfd = open(serial_filename, "r")
            old_serial = serialfd.readline()
            # same date
            if serial[0:8] == old_serial[0:8]:
                if int(old_serial[8:10]) < 99:
                    serial = "%s%.2i" % (serial[0:8], int(old_serial[8:10]) + 1)
            else:
                pass
            serialfd.close()
        except:
            pass

        serialfd = open(serial_filename, "w")
        serialfd.write(serial)
        serialfd.close()

        forward = self.__forward_zones()
        reverse = self.__reverse_zones()

        try:
            f2 = open(default_template_file, "r")
        except:
            raise CX("error reading template from file: %s" % default_template_file)
        default_template_data = ""
        default_template_data = f2.read()
        f2.close()

        zonefileprefix = self.settings.bind_chroot_path + self.zonefile_base

        for (zone, hosts) in forward.items():
            metadata = {
                'cobbler_server': cobbler_server,
                'serial': serial,
                'zonename': zone,
                'zonetype': 'forward',
                'cname_record': '',
                'host_record': ''
            }

            if ":" in zone:
                long_zone = (self.__expand_IPv6(zone + '::1'))[:19]
                tokens = list(re.sub(':', '', long_zone))
                tokens.reverse()
                zone_origin = '.'.join(tokens) + '.ip6.arpa.'
            else:
                zone_origin = ''
            # grab zone-specific template if it exists
            try:
                fd = open('/etc/cobbler/zone_templates/%s' % zone)
                # If this is an IPv6 zone, set the origin to the zone for this
                # template
                if zone_origin:
                    template_data = r"\$ORIGIN " + zone_origin + "\n" + fd.read()
                else:
                    template_data = fd.read()
                fd.close()
            except:
                # If this is an IPv6 zone, set the origin to the zone for this
                # template
                if zone_origin:
                    template_data = r"\$ORIGIN " + zone_origin + "\n" + default_template_data
                else:
                    template_data = default_template_data

            metadata['cname_record'] = self.__pretty_print_cname_records(hosts)
            metadata['host_record'] = self.__pretty_print_host_records(hosts)

            zonefilename = zonefileprefix + zone
            self.logger.info("generating (forward) %s", zonefilename)
            self.templar.render(template_data, metadata, zonefilename)

        for (zone, hosts) in reverse.items():
            metadata = {
                'cobbler_server': cobbler_server,
                'serial': serial,
                'zonename': zone,
                'zonetype': 'reverse',
                'cname_record': '',
                'host_record': ''
            }

            # grab zone-specific template if it exists
            try:
                fd = open('/etc/cobbler/zone_templates/%s' % zone)
                template_data = fd.read()
                fd.close()
            except:
                template_data = default_template_data

            metadata['cname_record'] = self.__pretty_print_cname_records(hosts)
            metadata['host_record'] = self.__pretty_print_host_records(hosts, rectype='PTR')

            zonefilename = zonefileprefix + zone
            self.logger.info("generating (reverse) %s", zonefilename)
            self.templar.render(template_data, metadata, zonefilename)

    def write_configs(self):
        """
        BIND files are written when ``manage_dns`` is set in our settings.
        """

        self.__write_named_conf()
        self.__write_secondary_conf()
        self.__write_zone_files()

    def restart_service(self):
        """
        This syncs the bind server with it's new config files.
        Basically this restarts the service to apply the changes.
        """
        # TODO: Reuse the utils method for service restarts
        named_service_name = utils.named_service_name()
        dns_restart_command = ["service", named_service_name, "restart"]
        ret = utils.subprocess_call(dns_restart_command, shell=False)
        if ret != 0:
            self.logger.error("%s service failed", named_service_name)
        return ret


def get_manager(api):
    """
    This returns the object to manage a BIND server located locally on the Cobbler server.

    :param api: The API to resolve all information with.
    :return: The BindManger object to manage bind with.
    """
    # Singleton used, therefore ignoring 'global'
    global MANAGER  # pylint: disable=global-statement

    if not MANAGER:
        MANAGER = _BindManager(api)
    return MANAGER
