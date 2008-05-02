"""
This is some of the code behind 'cobbler sync'.

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>
John Eckersberg <jeckersb@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import os.path
import shutil
import time
import sub_process
import sys
import glob
import traceback
import errno
import popen2
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
        return "isc_and_bind"

    def __init__(self,config,verbose=False):
        """
        Constructor
        """
        self.verbose     = verbose
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
        Returns ALL forward zones for all systems
        """
        zones = {}
        for sys in self.systems:
            for (name, interface) in sys.interfaces.iteritems():
                host = interface["hostname"]
                ip   = interface["ip_address"]
                if not host or not ip:
                    # gotsta have some hostname and ip or else!
                    continue
                if host.find(".") == -1:
                    continue
                tokens = host.split('.')
                zone = '.'.join(tokens[1:])
                if zones.has_key(zone):
                    zones[zone].append((host.split('.')[0], ip))
                else:
                    zones[zone] = [(host.split('.')[0], ip)]
        return zones

    def __reverse_zones(self):
        """
        Returns ALL reverse zones for all systems
        """
        zones = {}
        for sys in self.systems:
            for (name, interface) in sys.interfaces.iteritems():
                host = interface["hostname"]
                ip   = interface["ip_address"]
                if not host or not ip:
                    # gotsta have some hostname and ip or else!
                    continue
                tokens = ip.split('.')
                zone = '.'.join(tokens[0:3])
                if zones.has_key(zone):
                    zones[zone].append((tokens[3], host + '.'))
                else:
                    zones[zone] = [(tokens[3], host + '.')]
        return zones

    def __config_forward_zones(self):
        """
        Returns only the forward zones which have systems and are defined
        in the option manage_forward_zones

        Alternatively if manage_forward_zones is empty, return all systems
        """
        all = self.__forward_zones()
        want = self.settings.manage_forward_zones
        if want == []: return all
        ret = {}
        for zone in all.keys():
            if zone in want:
                ret[zone] = all[zone]
        return ret

    def __config_reverse_zones(self):
        """
        Returns only the reverse zones which have systems and are defined
        in the option manage_reverse_zones

        Alternatively if manage_reverse_zones is empty, return all systems
        """
        all = self.__reverse_zones()
        want = self.settings.manage_reverse_zones
        if want == []: return all
        ret = {}
        for zone in all.keys():
            if zone in want:
                ret[zone] = all[zone]
        return ret

    def __write_named_conf(self):
        """
        Write out the named.conf main config file from the template.
        """
        settings_file = self.settings.named_conf
        template_file = "/etc/cobbler/named.template"
        forward_zones = self.settings.manage_forward_zones
        reverse_zones = self.settings.manage_reverse_zones

        metadata = {'zone_include': ''}
        for zone in self.__config_forward_zones().keys():
                txt =  """
zone "%(zone)s." {
    type master;
    file "%(zone)s";
};
""" % {'zone': zone}
                metadata['zone_include'] = metadata['zone_include'] + txt

        for zone in self.__config_reverse_zones().keys():
                tokens = zone.split('.')
                tokens.reverse()
                arpa = '.'.join(tokens) + '.in-addr.arpa'
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

        self.templar.render(template_data, metadata, settings_file, None)

    def __write_zone_files(self):
        """
        Write out the forward and reverse zone files for all the zones
        defined in manage_forward_zones and manage_reverse_zones
        """
        template_file = "/etc/cobbler/zone.template"
        cobbler_server = self.settings.server
        serial = int(time.time())
        forward = self.__config_forward_zones()
        reverse = self.__config_reverse_zones()

        try:
            f2 = open(template_file,"r")
        except:
            raise CX(_("error reading template from file: %s") % template_file)
        template_data = ""
        template_data = f2.read()
        f2.close()

        for (zone, hosts) in forward.iteritems():
            metadata = {
                'cobbler_server': cobbler_server,
                'serial': serial,
                'host_record': ''
            }

            for host in hosts:
                txt = '%s\tIN\tA\t%s\n' % host
                metadata['host_record'] = metadata['host_record'] + txt

            self.templar.render(template_data, metadata, '/var/named/' + zone, None)

        for (zone, hosts) in reverse.iteritems():
            metadata = {
                'cobbler_server': cobbler_server,
                'serial': serial,
                'host_record': ''
            }

            for host in hosts:
                txt = '%s\tIN\tPTR\t%s\n' % host
                metadata['host_record'] = metadata['host_record'] + txt

            self.templar.render(template_data, metadata, '/var/named/' + zone, None)


    def write_dns_files(self):
        """
        BIND files are written when manage_dns is set in
        /var/lib/cobbler/settings.
        """

        self.__write_named_conf()
        self.__write_zone_files()

def get_manager(config):
    return BindManager(config)

