"""
Running small pieces of cobbler sync when certain actions are taken,
such that we don't need a time consuming sync when adding new
systems if nothing has changed for systems that have already 
been created.

Copyright 2006-2009, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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

import utils
import traceback
import clogger

class BootLiteSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config,verbose=False,logger=None):
        """
        Constructor
        """
        self.verbose     = verbose
        self.config      = config
        self.distros     = config.distros()
        self.profiles    = config.profiles()
        self.systems     = config.systems()
        self.images      = config.images()
        self.settings    = config.settings()
        self.repos       = config.repos()
        if logger is None:
            logger = clogger.Logger()
        self.logger      = logger
        self.sync        = config.api.get_sync(verbose,logger=self.logger)
        self.sync.make_tftpboot()

    def add_single_distro(self, name):
        # get the distro record
        distro = self.distros.find(name=name)
        if distro is None:
            return
        # copy image files to images/$name in webdir & tftpboot:
        self.sync.pxegen.copy_single_distro_files(distro)
        # generate any templates listed in the distro
        self.sync.pxegen.write_templates(distro)
        # cascade sync
        kids = distro.get_children()
        for k in kids:
            self.add_single_profile(k.name, rebuild_menu=False)    
        self.sync.pxegen.make_pxe_menu()


    def add_single_image(self, name):
        image = self.images.find(name=name)
        self.sync.pxegen.copy_single_image_files(image)
        kids = image.get_children()
        for k in kids:
            self.add_single_system(k.name)
        self.sync.pxegen.make_pxe_menu()

    def remove_single_distro(self, name):
        bootloc = utils.tftpboot_location()
        # delete contents of images/$name directory in webdir
        utils.rmtree(os.path.join(self.settings.webdir, "images", name))
        # delete contents of images/$name in tftpboot
        utils.rmtree(os.path.join(bootloc, "images", name))
        # delete potential symlink to tree in webdir/links
        utils.rmfile(os.path.join(self.settings.webdir, "links", name)) 

    def remove_single_image(self, name):
        bootloc = utils.tftpboot_location()
        utils.rmfile(os.path.join(bootloc, "images2", name))

    def add_single_profile(self, name, rebuild_menu=True):
        # get the profile object:
        profile = self.profiles.find(name=name)
        if profile is None:
            # most likely a subprofile's kid has been
            # removed already, though the object tree has
            # not been reloaded ... and this is just noise.
            return
        # rebuild the yum configuration files for any attached repos
        # generate any templates listed in the distro
        self.sync.pxegen.write_templates(profile)
        # cascade sync
        kids = profile.get_children()
        for k in kids:
            if k.COLLECTION_TYPE == "profile":
                self.add_single_profile(k.name, rebuild_menu=False)
            else:
                self.add_single_system(k.name)
        if rebuild_menu:
            self.sync.pxegen.make_pxe_menu()
        return True
         
    def remove_single_profile(self, name, rebuild_menu=True):
        # delete profiles/$name file in webdir
        utils.rmfile(os.path.join(self.settings.webdir, "profiles", name))
        # delete contents on kickstarts/$name directory in webdir
        utils.rmtree(os.path.join(self.settings.webdir, "kickstarts", name))
        if rebuild_menu:
            self.sync.pxegen.make_pxe_menu()
   
    def update_system_netboot_status(self,name):
        system = self.systems.find(name=name)
        if system is None:
            utils.die(self.logger,"error in system lookup for %s" % name)
        self.sync.pxegen.write_all_system_files(system)
        # generate any templates listed in the system
        self.sync.pxegen.write_templates(system)
 
    def add_single_system(self, name):
        # get the system object:
        system = self.systems.find(name=name)
        if system is None:
            return
        # rebuild system_list file in webdir
        if self.settings.manage_dhcp:
            self.sync.dhcp.regen_ethers() 
        if self.settings.manage_dns:
            self.sync.dns.regen_hosts()  
        # write the PXE files for the system
        self.sync.pxegen.write_all_system_files(system)
        # generate any templates listed in the distro
        self.sync.pxegen.write_templates(system)

    def remove_single_system(self, name):
        bootloc = utils.tftpboot_location()
        system_record = self.systems.find(name=name)
        # delete contents of kickstarts_sys/$name in webdir
        system_record = self.systems.find(name=name)

        itanic = False
        profile = self.profiles.find(name=system_record.profile)
        if profile is not None:
            distro = self.distros.find(name=profile.get_conceptual_parent().name)
            if distro is not None and distro in [ "ia64", "IA64"]:
                itanic = True

        for (name,interface) in system_record.interfaces.iteritems():
            filename = utils.get_config_filename(system_record,interface=name)

            if not itanic:
                utils.rmfile(os.path.join(bootloc, "pxelinux.cfg", filename))
                utils.rmfile(os.path.join(bootloc, "grub", filename.upper()))
            else:
                utils.rmfile(os.path.join(bootloc, filename))

