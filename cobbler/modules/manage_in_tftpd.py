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

import glob
import os.path
import shutil
import tftpgen

import cobbler.clogger as clogger
import cobbler.templar as templar
import cobbler.utils as utils

from cobbler.utils import _
from cobbler.cexceptions import CX


def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "manage"


class InTftpdManager:

    def what(self):
        return "in_tftpd"

    def __init__(self, collection_mgr, logger):
        """
        Constructor
        """
        self.logger = logger
        if self.logger is None:
            self.logger = clogger.Logger()

        self.collection_mgr = collection_mgr
        self.templar = templar.Templar(collection_mgr)
        self.settings_file = "/etc/xinetd.d/tftp"
        self.tftpgen = tftpgen.TFTPGen(collection_mgr, self.logger)
        self.systems = collection_mgr.systems()
        self.bootloc = utils.tftpboot_location()

    def regen_hosts(self):
        pass        # not used

    def write_dns_files(self):
        pass        # not used

    def write_boot_files_distro(self, distro):
        # collapse the object down to a rendered datastructure
        # the second argument set to false means we don't collapse
        # dicts/arrays into a flat string
        target = utils.blender(self.collection_mgr.api, False, distro)

        # Create metadata for the templar function
        # Right now, just using local_img_path, but adding more
        # cobbler variables here would probably be good
        metadata = {}
        metadata["local_img_path"] = os.path.join(utils.tftpboot_location(), "images", distro.name)
        # Create the templar instance.  Used to template the target directory
        templater = templar.Templar(self.collection_mgr)

        # Loop through the dict of boot files,
        # executing a cp for each one
        self.logger.info("processing boot_files for distro: %s" % distro.name)
        for file in target["boot_files"].keys():
            rendered_file = templater.render(file, metadata, None)
            try:
                for f in glob.glob(target["boot_files"][file]):
                    if f == target["boot_files"][file]:
                        # this wasn't really a glob, so just copy it as is
                        filedst = rendered_file
                    else:
                        # this was a glob, so figure out what the destination
                        # file path/name should be
                        tgt_path, tgt_file = os.path.split(f)
                        rnd_path, rnd_file = os.path.split(rendered_file)
                        filedst = os.path.join(rnd_path, tgt_file)
                    if not os.path.isfile(filedst):
                        shutil.copyfile(f, filedst)
                    self.collection_mgr.api.log("copied file %s to %s for %s" % (f, filedst, distro.name))
            except:
                self.logger.error("failed to copy file %s to %s for %s" % (f, filedst, distro.name))

        return 0

    def write_boot_files(self):
        """
        Copy files in profile["boot_files"] into /tftpboot.  Used for vmware
        currently.
        """
        for distro in self.collection_mgr.distros():
            self.write_boot_files_distro(distro)

        return 0

    def write_tftpd_files(self):
        """
        xinetd files are written when manage_tftp is set in
        /var/lib/cobbler/settings.
        """
        template_file = "/etc/cobbler/tftpd.template"

        try:
            f = open(template_file, "r")
        except:
            raise CX(_("error reading template %s") % template_file)
        template_data = ""
        template_data = f.read()
        f.close()

        metadata = {
            "user": "root",
            "binary": "/usr/sbin/in.tftpd",
            "args": "%s" % self.bootloc
        }
        self.logger.info("generating %s" % self.settings_file)
        self.templar.render(template_data, metadata, self.settings_file, None)

    def update_netboot(self, name):
        """
        Write out new pxelinux.cfg files to /tftpboot
        """
        system = self.systems.find(name=name)
        if system is None:
            utils.die(self.logger, "error in system lookup for %s" % name)
        menu_items = self.tftpgen.get_menu_items()['pxe']
        self.tftpgen.write_all_system_files(system, menu_items)
        # generate any templates listed in the system
        self.tftpgen.write_templates(system)

    def add_single_system(self, system):
        """
        Write out new pxelinux.cfg files to /tftpboot
        """
        # write the PXE files for the system
        menu_items = self.tftpgen.get_menu_items()['pxe']
        self.tftpgen.write_all_system_files(system, menu_items)
        # generate any templates listed in the distro
        self.tftpgen.write_templates(system)

    def add_single_distro(self, distro):
        self.tftpgen.copy_single_distro_files(distro, self.bootloc, False)
        self.write_boot_files_distro(distro)

    def sync(self, verbose=True):
        """
        Write out all files to /tftpdboot
        """
        self.tftpgen.verbose = verbose
        self.logger.info("copying bootloaders")
        self.tftpgen.copy_bootloaders()

        self.logger.info("copying distros to tftpboot")

        # Adding in the exception handling to not blow up if files have
        # been moved (or the path references an NFS directory that's no longer
        # mounted)
        for d in self.collection_mgr.distros():
            try:
                self.logger.info("copying files for distro: %s" % d.name)
                self.tftpgen.copy_single_distro_files(d, self.bootloc, False)
            except CX, e:
                self.logger.error(e.value)

        self.logger.info("copying images")
        self.tftpgen.copy_images()

        # the actual pxelinux.cfg files, for each interface
        self.logger.info("generating PXE configuration files")
        menu_items = self.tftpgen.get_menu_items()['pxe']
        for x in self.systems:
            self.tftpgen.write_all_system_files(x, menu_items)

        self.logger.info("generating PXE menu structure")
        self.tftpgen.make_pxe_menu()


def get_manager(collection_mgr, logger):
    return InTftpdManager(collection_mgr, logger)
