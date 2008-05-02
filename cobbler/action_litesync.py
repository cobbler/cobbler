"""
Running small pieces of cobbler sync when certain actions are taken,
such that we don't need a time consuming sync when adding new
systems if nothing has changed for systems that have already 
been created.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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
import yaml # Howell-Clark version
import sub_process
import sys

import utils
import action_sync
from cexceptions import *
import traceback
import errno

from utils import _


class BootLiteSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config):
        """
        Constructor
        """
        self.verbose     = True
        self.config      = config
        self.distros     = config.distros()
        self.profiles    = config.profiles()
        self.systems     = config.systems()
        self.settings    = config.settings()
        self.repos       = config.repos()
        self.sync        = config.api.get_sync()

    def add_single_distro(self, name):
        # get the distro record
        distro = self.distros.find(name=name)
        if distro is None:
            raise CX(_("error in distro lookup: %s") % name)
        # copy image files to images/$name in webdir & tftpboot:
        self.sync.pxegen.copy_single_distro_files(distro)
        # cascade sync
        kids = distro.get_children()
        for k in kids:
            self.add_single_profile(k.name)    

    def remove_single_distro(self, name):
        bootloc = utils.tftpboot_location()
        # delete contents of images/$name directory in webdir
        utils.rmtree(os.path.join(self.settings.webdir, "images", name))
        # delete contents of images/$name in tftpboot
        utils.rmtree(os.path.join(bootloc, "images", name))
        # delete potential symlink to tree in webdir/links
        utils.rmfile(os.path.join(self.settings.webdir, "links", name)) 

    def add_single_profile(self, name):
        # get the profile object:
        profile = self.profiles.find(name=name)
        if profile is None:
            raise CX(_("error in profile lookup"))
        # rebuild the yum configuration files for any attached repos
        self.sync.yumgen.retemplate_yum_repos(profile,True)
        # cascade sync
        kids = profile.get_children()
        for k in kids:
            if k.COLLECTION_TYPE == "profile":
                self.add_single_profile(k.name)
            else:
                self.add_single_system(k.name)
 
    def remove_single_profile(self, name):
        # delete profiles/$name file in webdir
        utils.rmfile(os.path.join(self.settings.webdir, "profiles", name))
        # delete contents on kickstarts/$name directory in webdir
        utils.rmtree(os.path.join(self.settings.webdir, "kickstarts", name))
   
    def update_system_netboot_status(self,name):
        system = self.systems.find(name=name)
        if system is None:
            raise CX(_("error in system lookup for %s") % name)
        self.sync.pxegen.write_all_system_files(system)
 
    def add_single_system(self, name):
        # get the system object:
        system = self.systems.find(name=name)
        if system is None:
            raise CX(_("error in system lookup for %s") % name)
        # rebuild system_list file in webdir
        if self.settings.manage_dhcp:
            self.sync.dns.regen_ethers() 
        if self.settings.manage_dns:
            self.sync.dhcp.regen_hosts()  
        # write the PXE files for the system
        self.sync.pxegen.write_all_system_files(system)
        # per system kickstarts
        self.sync.yumgen.retemplate_yum_repos(system,False)
        if self.settings.manage_dhcp:
            if self.settings.omapi_enabled: 
                for (name,interface) in system.interfaces.iteritems():
                    self.sync.dhcp.write_dhcp_lease(
                        self.settings.omapi_port,
                        interface["hostname"],
                        interface["mac_address"],
                        interface["ip_address"]
                    )


    def remove_single_system(self, name):
        bootloc = utils.tftpboot_location()
        system_record = self.systems.find(name=name)
        # delete contents of kickstarts_sys/$name in webdir
        system_record = self.systems.find(name=name)
        # delete any kickstart files related to this system
        for (name,interface) in system_record.interfaces.iteritems():
           filename = utils.get_config_filename(system_record,interface=name)
           utils.rmtree(os.path.join(self.settings.webdir, "kickstarts_sys", filename))

        if self.settings.manage_dhcp:
            if self.settings.omapi_enabled: 
                for (name,interface) in system_record.interfaces.iteritems():
                    self.sync.dhcp.remove_dhcp_lease(
                        self.settings.omapi_port,
                        interface["hostname"]
                    )

        # unneeded
        #if not system_record.is_pxe_supported():
        #   # no need to go any further with PXE cleanup
        #   return
        
        # delete PXE Linux configuration file (which might be in one of two places)
        itanic = False
        profile = self.profiles.find(name=system_record.profile)
        if profile is not None:
            distro = self.distros.find(name=profile.distro)
            if distro is not None and distro in [ "ia64", "IA64"]:
                itanic = True
        if not itanic:
            utils.rmfile(os.path.join(bootloc, "pxelinux.cfg", filename))
        else:
            utils.rmfile(os.path.join(bootloc, filename))

