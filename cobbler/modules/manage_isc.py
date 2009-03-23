"""
This is some of the code behind 'cobbler sync'.

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>
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
import sub_process
import sys
import glob
import traceback
import errno
from utils import popen2
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


class IscManager:

    def what(self):
        return "isc"

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
        if ip.find("/") != -1:
            return 
        try:
            fromchild, tochild = popen2([self.settings.omshell_bin])
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
            tochild.write("set hardware-address = %s\n" % mac.lower())
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
        Use DHCP's API to delete a DHCP entry in 
        the /var/lib/dhcpd/dhcpd.leases file 
        """
 	fromchild, tochild = popen2([self.settings.omshell_bin])
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
        blender_cache = {}

        try:
            f2 = open(template_file,"r")
        except:
            raise CX(_("error writing template to file: %s") % template_file)
        template_data = ""
        template_data = f2.read()
        f2.close()

        # use a simple counter for generating generic names where a hostname
        # is not available
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
                        self.remove_dhcp_lease(self.settings.omapi_port,hostremove)

        # we used to just loop through each system, but now we must loop
        # through each network interface of each system.
        dhcp_tags = { "default": {} }
        elilo = "/elilo-3.6-ia64.efi"
        yaboot = "/yaboot-1.3.14"

        for system in self.systems:
            if not system.is_management_supported(cidr_ok=False):
                continue

            profile = system.get_conceptual_parent()
            distro  = profile.get_conceptual_parent()

            # if distro is None then the profile is really an image
            # record!         

            for (name, interface) in system.interfaces.iteritems():

                # this is really not a per-interface setting
                # but we do this to make the templates work
                # without upgrade
                interface["gateway"] = system.gateway

                mac  = interface["mac_address"]
                ip   = interface["ip_address"]
                host = interface["dns_name"]


                if distro is not None:
                    interface["distro"]  = distro.to_datastruct()

                if mac is None or mac == "":
                    # can't write a DHCP entry for this system
                    continue 
 
                counter = counter + 1

                # the label the entry after the hostname if possible
                if host is not None and host != "":
                    interface["name"] = host
                else:
                    interface["name"] = "generic%d" % counter

                # add references to the system, profile, and distro
                # for use in the template
                if blender_cache.has_key(interface["name"]):
                    blended_system = blender_cache[interface["name"]]
                else:
                    blended_system  = utils.blender( self.api, False, system )
                    
                interface["next_server"] = blended_system["server"]
                interface["netboot_enabled"] = blended_system["netboot_enabled"]
                    
                interface["filename"] = "/pxelinux.0"
                # can't use pxelinux.0 anymore
                if distro is not None:
                    if distro.arch == "ia64":
                        interface["filename"] = elilo
                    elif distro.arch.startswith("ppc"):
                        interface["filename"] = yaboot
                    
                # If we have all values defined and we're using omapi,
                # we will just create entries dinamically into DHCPD
                # without requiring a restart (but file will be written
                # as usual for having it working after restart)

                if ip is not None and ip != "":
                  if mac is not None and mac != "":
                    if host is not None and host != "":
                      if self.settings.omapi_enabled and self.settings.omapi_port:
                        self.remove_dhcp_lease(self.settings.omapi_port,host)
                        self.write_dhcp_lease(self.settings.omapi_port,host,ip,mac)
                        
                dhcp_tag = interface["dhcp_tag"]
                if dhcp_tag == "":
                   dhcp_tag = "default"


                if not dhcp_tags.has_key(dhcp_tag):
                    dhcp_tags[dhcp_tag] = {
                       mac: interface
                    }
                else:
                    dhcp_tags[dhcp_tag][mac] = interface

        # we are now done with the looping through each interface of each system
        metadata = {
           "omapi_enabled"  : self.settings.omapi_enabled,
           "omapi_port"     : self.settings.omapi_port,
           "date"           : time.asctime(time.gmtime()),
           "cobbler_server" : self.settings.server,
           "next_server"    : self.settings.next_server,
           "elilo"          : elilo,
           "yaboot"         : yaboot,
           "dhcp_tags"      : dhcp_tags
        }

        self.templar.render(template_data, metadata, settings_file, None)

    def regen_ethers(self):
        pass # ISC/BIND do not use this


def get_manager(config):
    return IscManager(config)

