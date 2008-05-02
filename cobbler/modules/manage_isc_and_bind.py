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


class IscAndBindManager:

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

    def write_dhcp_lease(self,port,host,ip,mac):
        """
        Use DHCP's API to create a DHCP entry in the 
        /var/lib/dhcpd/dhcpd.leases file
        #Code from http://svn.osgdc.org/browse/kusu/kusu
        # /trunk/src/kits/base/packages/kusu-base-installer/lib/kusu/nodefun.py?r=3025
        # FIXME: should use subprocess
        """
        try:
            fromchild, tochild = popen2.popen2("/usr/bin/omshell")
            tochild.write("port %s\n" % port)
            tochild.flush()
            tochild.write("connect\n")
            tochild.flush()
            tochild.write("new host\n")
            tochild.flush()
            tochild.write('set name = \"%s\"\n' % host)
            tochild.flush()
            tochild.write("set ip-address = %s\n" % ip)
            tochild.flush()
            tochild.write("set hardware-address = %s\n" % mac)
            tochild.flush()
            tochild.write("set hardware-type = 1\n")
            tochild.flush()
            tochild.write("create\n")
            tochild.flush()
            tochild.close()
            fromchild.close()
        except IOError:
            # FIXME: just catch 32 (broken pipe) and show a warning
            pass

    def remove_dhcp_lease(self,port,host):
        """
        removeDHCPLease(port,host)
        Use DHCP's API to delete a DHCP entry in 
        the /var/lib/dhcpd/dhcpd.leases file 
        """
 	fromchild, tochild = popen2.popen2("/usr/bin/omshell")
     	try:
            tochild.write("port %s\n" % port)
 	    tochild.flush()
            tochild.write("connect\n")
            tochild.flush()
            tochild.write("new host\n")
            tochild.flush()
            tochild.write('set name = \"%s\"\n' % host)
            tochild.flush()
            tochild.write("open\n")   # opens register with host information
            tochild.flush()
            tochild.write("remove\n")
            tochild.flush()
            tochild.close()
            fromchild.close()
        except IOError:
            # FIXME: convert this to subprocess.
            # FIXME: catch specific errors only (32/broken pipe)
            pass
            
    def write_dhcp_file(self):
        """
        DHCP files are written when manage_dhcp is set in
        /var/lib/cobbler/settings.
        """
        
        settings_file = self.settings.dhcpd_conf
        template_file = "/etc/cobbler/dhcp.template"
        mode = self.settings.manage_dhcp_mode.lower()

        try:
            f2 = open(template_file,"r")
        except:
            raise CX(_("error writing template to file: %s") % template_file)
        template_data = ""
        template_data = f2.read()
        f2.close()

        # build each per-system definition
        # as configured, this only works for ISC, patches accepted
        # from those that care about Itanium.  elilo seems to be unmaintained
        # so additional maintaince in other areas may be required to keep
        # this working.

        elilo = os.path.basename(self.settings.bootloaders["ia64"])

        system_definitions = {}
        counter = 0
        
        
        # Clean system definitions in /var/lib/dhcpd/dhcpd.leases just in
        # case to avoid conflicts with the hosts we're defining and to clean
        # possible removed hosts (only if using OMAPI)
        if self.settings.omapi_enabled and self.settings.omapi_port:
            if os.path.exists("/var/lib/dhcpd/dhcpd.leases"):
                file = open('/var/lib/dhcpd/dhcpd.leases')
                item = shlex(file)
                while 1:
                    elem = item.get_token()
                    if not elem:
                        break
                    if elem == 'host':
                        hostremove =  item.get_token()
                        self.removeDHCPLease(self.settings.omapi_port,hostremove)

        # we used to just loop through each system, but now we must loop
        # through each network interface of each system.
        
        for system in self.systems:
            profile = system.get_conceptual_parent()
            distro  = profile.get_conceptual_parent()
            for (name, interface) in system.interfaces.iteritems():

                mac  = interface["mac_address"]
                ip   = interface["ip_address"]
                host = interface["hostname"]

                if mac is None or mac == "":
                    # can't write a DHCP entry for this system
                    continue 
 
                counter = counter + 1
                systxt = "" 


                # the label the entry after the hostname if possible
                if host is not None and host != "":
                    systxt = "\nhost %s {\n" % host
                    if self.settings.isc_set_host_name:
                        systxt = systxt + "    option host-name = \"%s\";\n" % host
                else:
                    systxt = "\nhost generic%d {\n" % counter

                if distro.arch == "ia64":
                    # can't use pxelinux.0 anymore
                    systxt = systxt + "    filename \"/%s\";\n" % elilo
                systxt = systxt + "    hardware ethernet %s;\n" % mac
                if ip is not None and ip != "":
                    systxt = systxt + "    fixed-address %s;\n" % ip
                systxt = systxt + "}\n"
                    
                # If we have all values defined and we're using omapi,
                # we will just create entries dinamically into DHCPD
                # without requiring a restart (but file will be written
                # as usual for having it working after restart)
                    
                if ip is not None and ip != "":
                  if mac is not None and mac != "":
                    if host is not None and host != "":
                      if self.settings.omapi_enabled and self.settings.omapi_port:
                        self.removeDHCPLease(self.settings.omapi_port,host)
                        self.writeDHCPLease(self.settings.omapi_port,host,ip,mac)
                        
                dhcp_tag = interface["dhcp_tag"]
                if dhcp_tag == "":
                   dhcp_tag = "default"

                if not system_definitions.has_key(dhcp_tag):
                    system_definitions[dhcp_tag] = ""
                system_definitions[dhcp_tag] = system_definitions[dhcp_tag] + systxt

        # we are now done with the looping through each interface of each system

        metadata = {
           "omapi_enabled"  : self.settings.omapi_enabled,
           "omapi_port"     : self.settings.omapi_port,
           "insert_cobbler_system_definitions" : system_definitions.get("default",""),
           "date"           : time.asctime(time.gmtime()),
           "cobbler_server" : self.settings.server,
           "next_server"    : self.settings.next_server,
           "elilo"          : elilo
        }

        # now add in other DHCP expansions that are not tagged with "default"
        for x in system_definitions.keys():
            if x == "default":
                continue
            metadata["insert_cobbler_system_definitions_%s" % x] = system_definitions[x]   

        self.templar.render(template_data, metadata, settings_file, None)

    def regen_ethers(self):
        pass # ISC/BIND do not use this


    def regen_hosts(self):
        pass # ISC/BIND do not use this


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
    return IscAndBindManager(config)

