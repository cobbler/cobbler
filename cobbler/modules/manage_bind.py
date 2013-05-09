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
import sys
import glob
import traceback
import errno
import re


import utils
from cexceptions import *
import templar 

import item_distro
import item_profile
import item_repo
import item_system

from utils import _

from types import *

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
        self.logger        = logger
        self.config        = config
        self.api           = config.api
        self.distros       = config.distros()
        self.profiles      = config.profiles()
        self.systems       = config.systems()
        self.settings      = config.settings()
        self.repos         = config.repos()
        self.templar       = templar.Templar(config)
        self.settings_file = utils.namedconf_location(self.api)
        self.zonefile_base = utils.zonefile_base(self.api)

    def regen_hosts(self):
        pass # not used

    def __expand_IPv6(self, address):
        """
        Expands an IPv6 address to long format i.e.
        xxxx:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx
        """
        # Function by Chris Miller, approved for GLP use, taken verbatim from:
        # http://forrst.com/posts/Python_Expand_Abbreviated_IPv6_Addresses-1kQ
        fullAddress = "" # All groups
        expandedAddress = "" # Each group padded with leading zeroes
        validGroupCount = 8
        validGroupSize = 4
        if "::" not in address: # All groups are already present
            fullAddress = address
        else: # Consecutive groups of zeroes have been collapsed with "::"
            sides = address.split("::")
            groupsPresent = 0
            for side in sides:
                if len(side) > 0:
                    groupsPresent += len(side.split(":"))
            if len(sides[0]) > 0:
                fullAddress += sides[0] + ":"
            for i in range(0,validGroupCount-groupsPresent):
                fullAddress += "0000:"
            if len(sides[1]) > 0:
                fullAddress += sides[1]
            if fullAddress[-1] == ":":
                fullAddress = fullAddress[:-1]
        groups = fullAddress.split(":")
        for group in groups:
            while(len(group) < validGroupSize):
                group = "0" + group
            expandedAddress += group + ":"
        if expandedAddress[-1] == ":":
            expandedAddress = expandedAddress[:-1]
        return expandedAddress

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
                ipv6   = interface["ipv6_address"]
                ipv6_sec_addrs = interface["ipv6_secondaries"]
                if not system.is_management_supported(cidr_ok=False):
                    continue
                if not host:
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

                # strip the zone off the dns_name
                host = re.sub('\.%s$' % best_match, '', host)

                # Create a list of IP addresses for this host
                ips = []
                if ip:
                   ips.append(ip)

                if ipv6:
                   ips.append(ipv6)

                if ipv6_sec_addrs:
                   ips = ips + ipv6_sec_addrs

                if ips:
                    try:
                       zones[best_match][host] = ips + zones[best_match][host]
                    except KeyError:
                       zones[best_match][host] = ips

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
           # expand and IPv6 zones
           if ":" in zone:
              zone = (self.__expand_IPv6(zone + '::1'))[:19]
           zones[zone] = {}

        for sys in self.systems:
            for (name, interface) in sys.interfaces.iteritems():
                host = interface["dns_name"]
                ip   = interface["ip_address"]
                ipv6 = interface["ipv6_address"]
                ipv6_sec_addrs = interface["ipv6_secondaries"]
                if not sys.is_management_supported(cidr_ok=False):
                    continue
                if not host or ( ( not ip ) and ( not ipv6) ):
                    # gotsta have some dns_name and ip or else!
                    continue

                if ip:
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

                    if best_match != '':
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

                if ipv6 or ipv6_sec_addrs:
                    ip6s = []
                    if ipv6:
                       ip6s.append(ipv6)
                    for each_ipv6 in ip6s + ipv6_sec_addrs:
                        # convert the IPv6 address to long format
                        long_ipv6 = self.__expand_IPv6(each_ipv6)
                        # All IPv6 zones are forced to have the format
                        # xxxx:xxxx:xxxx:xxxx
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
        """
        settings_file = self.settings.bind_chroot_path + self.settings_file
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
        Sorts IP addresses (or partial addresses) in a numerical fashion per-octet or quartet
        """
        quartets = []
        octets = []
        for each_ip in ips:
          # IPv6 addresses are ':' delimited
          if ":" in each_ip:
             # IPv6
             # strings to integer quartet chunks so we can sort numerically
             quartets.append([int(i,16) for i in each_ip.split(':')])
          else:
             # IPv4
             # strings to integer octet chunks so we can sort numerically
             octets.append([int(i) for i in each_ip.split('.')])
        quartets.sort()
        # integers back to four character hex strings
        quartets = map(lambda x: [format(i, '04x') for i in x], quartets)
        #
        octets.sort()
        # integers back to strings
        octets = map(lambda x: [str(i) for i in x], octets)
        #
        return ['.'.join(i) for i in octets] + [':'.join(i) for i in quartets]

    def __pretty_print_host_records(self, hosts, rectype='A', rclass='IN'):
        """
        Format host records by order and with consistent indentation
        """
        
        # Warns on hosts without dns_name, need to iterate over system to name the
        # particular system
                 
        for system in self.systems:
            for (name, interface) in system.interfaces.iteritems():
                if interface["dns_name"] == "":
                    self.logger.info(("Warning: dns_name unspecified in the system: %s, while writing host records") % system.name)                       
                
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
           my_host_record = hosts[name]
           my_host_list = []
           if type( my_host_record ) is StringType:
              my_host_list = [ my_host_record ]
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
    
    def __pretty_print_cname_records(self, hosts, rectype='CNAME'):
        """
        Format CNAMEs and with consistent indentation
        """
        s = ""
        
        # This loop warns and skips the host without dns_name instead of outright exiting
        # Which results in empty records without any warning to the users
        
        for system in self.systems:
            for (name, interface) in system.interfaces.iteritems():
                cnames = interface["cnames"]
        
                try:
                    if interface["dns_name"] != "":
                        dnsname = interface["dns_name"].split('.')[0] 
                        for cname in cnames:
                            s += "%s  %s  %s;\n" % (cname.split('.')[0], rectype, dnsname)                    
                    else:
                        self.logger.info(("Warning: dns_name unspecified in the system: %s, Skipped!, while writing cname records") % system.name)
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
        #this could be a config option too
        serial_filename="/var/lib/cobbler/bind_serial"
        #need a counter for new bind format
        serial = time.strftime("%Y%m%d00")
        try:
           serialfd = open(serial_filename,"r")
           old_serial = serialfd.readline()
           #same date
           if serial[0:8] == old_serial[0:8]:
              if int(old_serial[8:10]) < 99 :
                 serial= "%s%.2i" % (serial[0:8],int(old_serial[8:10]) +1)
           else:
              pass
           serialfd.close()
        except:
           pass

        serialfd = open(serial_filename,"w")
        serialfd.write(serial)
        serialfd.close()

        forward = self.__forward_zones()
        reverse = self.__reverse_zones()

        try:
            f2 = open(default_template_file,"r")
        except:
            raise CX(_("error reading template from file: %s") % default_template_file)
        default_template_data = ""
        default_template_data = f2.read()
        f2.close()

        zonefileprefix = self.settings.bind_chroot_path + self.zonefile_base

        for (zone, hosts) in forward.iteritems():
            metadata = {
                'cobbler_server': cobbler_server,
                'serial': serial,
                'zonetype': 'forward',
                'cname_record': '',
                'host_record': ''
                
            }

            # grab zone-specific template if it exists
            try:
               fd = open('/etc/cobbler/zone_templates/%s' % zone)
               template_data = fd.read()
               fd.close()
            except:
               # If this is an IPv6 zone, set the origin to the zone for this
               # template
               if ":" in zone:
                  long_zone = (self.__expand_IPv6(zone + '::1'))[:19]
                  tokens = list(re.sub(':', '', long_zone))
                  tokens.reverse()
                  zone_origin = '.'.join(tokens) + '.ip6.arpa.'
                  template_data = "\$ORIGIN " + zone_origin + "\n" + default_template_data
               else:
                  template_data = default_template_data

            metadata['cname_record'] = self.__pretty_print_cname_records(hosts)
            metadata['host_record'] = self.__pretty_print_host_records(hosts)
            
            
            zonefilename=zonefileprefix + zone
            if self.logger is not None:
               self.logger.info("generating (forward) %s" % zonefilename)
            self.templar.render(template_data, metadata, zonefilename, None)

        for (zone, hosts) in reverse.iteritems():
            metadata = {
                'cobbler_server': cobbler_server,
                'serial': serial,
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
