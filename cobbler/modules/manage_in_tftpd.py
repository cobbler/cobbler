"""
This is some of the code behind 'cobbler sync'.

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

import traceback
import errno
import re
import clogger
import pxegen

import utils
from cexceptions import *
import templar 

from utils import _


def register():
   """
   The mandatory cobbler module registration hook.
   """
   return "manage"


class InTftpdManager:

    def what(self):
        return "tftpd"

    def __init__(self,config,logger):
        """
        Constructor
        """
        self.logger        = logger
        if self.logger is None:
            self.logger = clogger.Logger()

        self.config        = config
        self.templar       = templar.Templar(config)
        self.settings_file = "/etc/xinetd.d/tftp"
        self.pxegen        = pxegen.PXEGen(config, self.logger)
        self.systems       = config.systems()
        self.bootloc       = utils.tftpboot_location()

    def regen_hosts(self):
        pass # not used

    def write_dns_files(self):
        pass # not used

    def write_boot_files_distro(self,distro):
        # collapse the object down to a rendered datastructure
        # the second argument set to false means we don't collapse
        # hashes/arrays into a flat string
        target      = utils.blender(api, False, distro)

        # Create metadata for the templar function
        # Right now, just using img_path, but adding more
        # cobbler variables here would probably be good
        metadata = {}
        metadata["img_path"] = os.path.join(
                                    utils.tftpboot_location(),
                                    "images",distro.name)

        # Loop through the hash of boot files,
        # executing a cp for each one
        for file in target["boot_files"].keys():
            file_dst = templater.render(file,metadata,None)
            try:
                shutil.copyfile(target["boot_files"][file], file_dst)
                api.log("copied file %s to %s for %s" % (
                        target["boot_files"][file],
                        file_dst,
                        distro.name))
            except:
                logger.error("failed to copy file %s to %s for %s" % (
                        target["boot_files"][file],
                        file_dst,
                    distro.name))
                # Continue on to sync what you can

        return 0

    def write_boot_files(self):
        """
        Copy files in profile["boot_files"] into /tftpboot.  Used for vmware
        currently.
        """
        # Create the templar instance.  Used to template the target directory
        templater = templar.Templar()

        for distro in api.distros():
            self.write_boot_files_distro(distro)

        return 0

    def write_tftpd_files(self):
        """
        xinetd files are written when manage_tftp is set in
        /var/lib/cobbler/settings.
        """
        template_file = "/etc/cobbler/tftpd.template"

        try:
            f = open(template_file,"r")
        except:
            raise CX(_("error reading template %s") % template_file)
        template_data = ""
        template_data = f.read()
        f.close()

        metadata = {
            "user"      : "root",
            "binary"    : "/usr/sbin/in.tftpd",
            "args"      : "-v -s %s" % self.bootloc
        }
        self.logger.info("generating %s" % self.settings_file)
        self.templar.render(template_data, metadata, self.settings_file, None)

    def update_netboot(self,name):
        """
        Write out new pxelinux.cfg files to /tftpboot
        """
        system = self.systems.find(name=name)
        if system is None:
            utils.die(self.logger,"error in system lookup for %s" % name)
        self.pxegen.write_all_system_files(system)
        # generate any templates listed in the system
        self.pxegen.write_templates(system)

    def add_single_system(self,system):
        """
        Write out new pxelinux.cfg files to /tftpboot
        """
        # write the PXE files for the system
        self.pxegen.write_all_system_files(system)
        # generate any templates listed in the distro
        self.pxegen.write_templates(system)

    def add_single_distro(self,distro):
        self.pxegen.copy_single_distro_files(distro,self.bootloc,False)
        self.write_boot_files_distro(distro)

    def sync(self,verbose=True):
        """
        Write out all files to /tftpdboot
        """
        self.pxegen.verbose = verbose
        self.logger.info("copying bootloaders")
        self.pxegen.copy_bootloaders()

        self.logger.info("copying distros to tftpboot")

        # Adding in the exception handling to not blow up if files have
        # been moved (or the path references an NFS directory that's no longer
        # mounted)
        for d in self.config.distros():
            try:
                self.logger.info("copying files for distro: %s" % d.name)
                self.pxegen.copy_single_distro_files(d,self.bootloc,False)
            except CX, e:
                self.logger.error(e.value)

        self.logger.info("copying images")
        self.pxegen.copy_images()

        # the actual pxelinux.cfg files, for each interface
        self.logger.info("generating PXE configuration files")
        for x in self.systems:
            self.pxegen.write_all_system_files(x)

        self.logger.info("generating PXE menu structure")
        self.pxegen.make_pxe_menu()

def get_manager(config,logger):
    return InTftpdManager(config,logger)
