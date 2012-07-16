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

import os
import os.path
import shutil
import time
import sys
import glob
import traceback
import errno
import re
from shlex import shlex


import utils
from cexceptions import *
import templar 

import item_distro
import item_profile
import item_repo
import item_system

from utils import _


def register():
   """
   The mandatory cobbler module registration hook.
   """
   return "manage"


class BindManager:

    def what(self):
        return "bind"

    def __init__(self,config,logger):
        """
        Constructor
        """
        self.logger      = logger
        self.config      = config
        self.api         = config.api
        self.distros     = config.distros()
        self.profiles    = config.profiles()
        self.systems     = config.systems()
        self.settings    = config.settings()
        self.repos       = config.repos()
        self.templar     = templar.Templar(config)

    def regen_hosts(self):
        pass # not used

    def __forward_zones(self):
        """
        Returns a map of zones and the records that belong
        in them
        """
        zones = {}
        forward_zones = self.settings.manage_forward_zones
        if type(forward_zones) != type([]):
           # gracefully handle when user inputs only a single zone
           # as a string instead of a list with only a single item
           forward_zones = [forward_zones]

        for zone in forward_zones:
           zones[zone] = {}

        for system in self.systems:
            for (name, interface) in system.interfaces.iteritems():
                host = interface["dns_name"]
                ip   = interface["ip_address"]
                if not system.is_management_supported(cidr_ok=False):
                    continue
                if not host or not ip:
                    # gotsta have some dns_name and ip or else!
                    continue
                if host.find(".") == -1:
                    continue

                # match the longest zone!
                # e.g. if you have a host a.b.c.d.e
                # if manage_forward_zones has:
                # - c.d.e
                # - b.c.d.e
                # then a.b.c.d.e should go in b.c.d.e
                best_match = ''
                for zone in zones.keys():
                   if re.search('\.%s$' % zone, host) and len(zone) > len(best_match):
                      best_match = zone

                if best_match == '': # no match
                   continue

                # strip the zone off the dns_name and append the
                # remainder + ip to the zone list
                host = re.sub('\.%s$' % best_match, '', host)

                zones[best_match][host] = ip

        return zones

    def __reverse_zones(self):
        """
        Returns a map of zones and the records that belong
        in them
        """
        zones = {}
        reverse_zones = self.settings.manage_reverse_zones
        if type(reverse_zones) != type([]):
           # gracefully handle when user inputs only a single zone
           # as a string instead of a list with only a single item
           reverse_zones = [reverse_zones]

        for zone in reverse_zones:
           zones[zone] = {}

        for sys in self.systems:
            for (name, interface) in sys.interfaces.iteritems():
                host = interface["dns_name"]
                ip   = interface["ip_address"]
                if not sys.is_management_supported(cidr_ok=False):
                    continue
                if not host or not ip:
                    # gotsta have some dns_name and ip or else!
                    continue

                # match the longest zone!
                # e.g. if you have an ip 1.2.3.4
                # if manage_reverse_zones has:
                # - 1.2
                # - 1.2.3
                # then 1.2.3.4 should go in 1.2.3
                best_match = ''
                for zone in zones.keys():
                   if re.search('^%s\.' % zone, ip) and len(zone) > len(best_match):
                      best_match = zone

                if best_match == '': # no match
                   continue

                # strip the zone off the front of the ip
                # reverse the rest of the octets
                # append the remainder + dns_name
                ip = ip.replace(best_match, '', 1)
                if ip[0] == '.': # strip leading '.' if it's there
                   ip = ip[1:]
                tokens = ip.split('.')
                tokens.reverse()
                ip = '.'.join(tokens)
                zones[best_match][ip] = host + '.'

        return zones


    def __write_named_conf(self):
        """
        Write out the named.conf main config file from the template.
        """
        settings_file = self.settings.bind_chroot_path + '/etc/named.conf'
        template_file = "/etc/cobbler/named.template"
        forward_zones = self.settings.manage_forward_zones
        reverse_zones = self.settings.manage_reverse_zones

        metadata = {'forward_zones': self.__forward_zones().keys(),
                    'reverse_zones': [],
                    'zone_include': ''}

        for zone in metadata['forward_zones']:
                txt =  """
zone "%(zone)s." {
    type master;
    file "%(zone)s";
};
""" % {'zone': zone}
                metadata['zone_include'] = metadata['zone_include'] + txt

        for zone in self.__reverse_zones().keys():
                tokens = zone.split('.')
                tokens.reverse()
                arpa = '.'.join(tokens) + '.in-addr.arpa'
                metadata['reverse_zones'].append((zone, arpa))
                txt = """
zone "%(arpa)s." {
    type master;
    file "%(zone)s";
};
""" % {'arpa': arpa, 'zone': zone}
                metadata['zone_include'] = metadata['zone_include'] + txt

        try:
            f2 = open(template_file,"r")
        except:
            raise CX(_("error reading template from file: %s") % template_file)
        template_data = ""
        template_data = f2.read()
        f2.close()

        if self.logger is not None:
            self.logger.info("generating %s" % settings_file)
        self.templar.render(template_data, metadata, settings_file, None)

    def __write_secondary_conf(self):
        """
        Write out the secondary.conf secondary config file from the template.
        """
        settings_file = self.settings.bind_chroot_path + '/etc/secondary.conf'
        template_file = "/etc/cobbler/secondary.template"
        forward_zones = self.settings.manage_forward_zones
        reverse_zones = self.settings.manage_reverse_zones

        metadata = {'forward_zones': self.__forward_zones().keys(),
                    'reverse_zones': [],
                    'zone_include': ''}

        for zone in metadata['forward_zones']:
                txt =  """
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
                tokens = zone.split('.')
                tokens.reverse()
                arpa = '.'.join(tokens) + '.in-addr.arpa'
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

        try:
            f2 = open(template_file,"r")
        except:
            raise CX(_("error reading template from file: %s") % template_file)
        template_data = ""
        template_data = f2.read()
        f2.close()

        if self.logger is not None:
            self.logger.info("generating %s" % settings_file)
        self.templar.render(template_data, metadata, settings_file, None)

    def __ip_sort(self, ips):
        """
        Sorts IP addresses (or partial addresses) in a numerical fashion per-octet
        """
        # strings to integer octet chunks so we can sort numerically
        octets = map(lambda x: [int(i) for i in x.split('.')], ips)
        octets.sort()
        # integers back to strings
        octets = map(lambda x: [str(i) for i in x], octets)
        return ['.'.join(i) for i in octets]

    def __pretty_print_host_records(self, hosts, rectype='A', rclass='IN'):
        """
        Format host records by order and with consistent indentation
        """
        names = [k for k,v in hosts.iteritems()]
        if not names: return '' # zones with no hosts

        if rectype == 'PTR':
           names = self.__ip_sort(names)
        else:
           names.sort()

        max_name = max([len(i) for i in names])

        s = ""
        for name in names:
           spacing = " " * (max_name - len(name))
           my_name = "%s%s" % (name, spacing)
           my_host = hosts[name]
           s += "%s  %s  %s  %s;\n" % (my_name, rclass, rectype, my_host)
        return s

    def __write_zone_files(self):
        """
        Write out the forward and reverse zone files for all configured zones
        """
        default_template_file = "/etc/cobbler/zone.template"
        cobbler_server = self.settings.server
        serial = int(time.time())
        forward = self.__forward_zones()
        reverse = self.__reverse_zones()

        try:
            f2 = open(default_template_file,"r")
        except:
            raise CX(_("error reading template from file: %s") % default_template_file)
        default_template_data = ""
        default_template_data = f2.read()
        f2.close()

        zonefileprefix = self.settings.bind_chroot_path + '/var/named/master'

        for (zone, hosts) in forward.iteritems():
            metadata = {
                'cobbler_server': cobbler_server,
                'serial': serial,
                'host_record': ''
            }

            # grab zone-specific template if it exists
            try:
               fd = open('/etc/cobbler/zone_templates/%s' % zone)
               template_data = fd.read()
               fd.close()
            except:
               template_data = default_template_data

            metadata['host_record'] = self.__pretty_print_host_records(hosts)

            zonefilename=zonefileprefix + zone
            if self.logger is not None:
               self.logger.info("generating (forward) %s" % zonefilename)
            self.templar.render(template_data, metadata, zonefilename, None)

        for (zone, hosts) in reverse.iteritems():
            metadata = {
                'cobbler_server': cobbler_server,
                'serial': serial,
                'host_record': ''
            }

            # grab zone-specific template if it exists
            try:
               fd = open('/etc/cobbler/zone_templates/%s' % zone)
               template_data = fd.read()
               fd.close()
            except:
               template_data = default_template_data

            metadata['host_record'] = self.__pretty_print_host_records(hosts, rectype='PTR')

            zonefilename=zonefileprefix + zone
            if self.logger is not None:
               self.logger.info("generating (reverse) %s" % zonefilename)
            self.templar.render(template_data, metadata, zonefilename, None)


    def write_dns_files(self):
        """
        BIND files are written when manage_dns is set in
        /var/lib/cobbler/settings.
        """

        self.__write_named_conf()
        self.__write_secondary_conf()
        self.__write_zone_files()

def get_manager(config,logger):
    return BindManager(config,logger)
