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
from typing import List

from cobbler import templar
from cobbler import utils
from cobbler import tftpgen

from cobbler.cexceptions import CX
from cobbler.manager import ManagerModule

MANAGER = None


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "manage"


class _InTftpdManager(ManagerModule):

    @staticmethod
    def what() -> str:
        """
        Static method to identify the manager.

        :return: Always "in_tftpd".
        """
        return "in_tftpd"

    def __init__(self, api):
        super().__init__(api)

        self.tftpgen = tftpgen.TFTPGen(api)
        self.bootloc = api.settings().tftpboot_location
        self.webdir = api.settings().webdir

    def write_boot_files_distro(self, distro):
        # Collapse the object down to a rendered datastructure.
        # The second argument set to false means we don't collapse dicts/arrays into a flat string.
        target = utils.blender(self.api, False, distro)

        # Create metadata for the templar function.
        # Right now, just using local_img_path, but adding more Cobbler variables here would probably be good.
        metadata = {}
        metadata["local_img_path"] = os.path.join(self.bootloc, "images", distro.name)
        metadata["web_img_path"] = os.path.join(self.webdir, "distro_mirror", distro.name)
        # Create the templar instance.  Used to template the target directory
        templater = templar.Templar(self.api)

        # Loop through the dict of boot files, executing a cp for each one
        self.logger.info("processing boot_files for distro: %s" % distro.name)
        for boot_file in list(target["boot_files"].keys()):
            rendered_target_file = templater.render(boot_file, metadata, None)
            rendered_source_file = templater.render(target["boot_files"][boot_file], metadata, None)
            try:
                for file in glob.glob(rendered_source_file):
                    if file == rendered_source_file:
                        # this wasn't really a glob, so just copy it as is
                        filedst = rendered_target_file
                    else:
                        # this was a glob, so figure out what the destination file path/name should be
                        tgt_path, tgt_file = os.path.split(file)
                        rnd_path, rnd_file = os.path.split(rendered_target_file)
                        filedst = os.path.join(rnd_path, tgt_file)

                        if not os.path.isdir(rnd_path):
                            utils.mkdir(rnd_path)
                    if not os.path.isfile(filedst):
                        shutil.copyfile(file, filedst)
                    self.logger.info("copied file %s to %s for %s", file, filedst, distro.name)
            except:
                self.logger.error("failed to copy file %s to %s for %s", file, filedst, distro.name)

        return 0

    def write_boot_files(self):
        """
        Copy files in ``profile["boot_files"]`` into the TFTP server folder. Used for vmware currently.

        :return: ``0`` on success.
        """
        for distro in self.distros:
            self.write_boot_files_distro(distro)

        return 0

    def sync_single_system(self, system, menu_items=None):
        """
        Write out new ``pxelinux.cfg`` files to the TFTP server folder (or grub/system/<mac> in grub case)

        :param system: The system to be added.
        :param menu_items: The menu items to add
        """
        if not menu_items:
            menu_items = self.tftpgen.get_menu_items()
        self.tftpgen.write_all_system_files(system, menu_items)
        # generate any templates listed in the distro
        self.tftpgen.write_templates(system)

    def add_single_distro(self, distro):
        self.tftpgen.copy_single_distro_files(distro, self.bootloc, False)
        self.write_boot_files_distro(distro)

    def sync_systems(self, systems: List[str], verbose: bool = True):
        """
        Write out specified systems as separate files to the TFTP server folder.

        :param systems: List of systems to write PXE configuration files for.
        :param verbose: Whether the TFTP server should log this verbose or not.
        """
        if not (isinstance(systems, list) and all(isinstance(sys_name, str) for sys_name in systems)):
            raise TypeError("systems needs to be a list of strings")

        if not isinstance(verbose, bool):
            raise TypeError("verbose needs to be of type bool")

        self.tftpgen.verbose = verbose

        system_objs = []
        for system_name in systems:
            # get the system object:
            system_obj = self.api.find_system(name=system_name)
            if system_obj is None:
                self.logger.info("did not find any system named %s", system_name)
                continue
            system_objs.append(system_obj)

        menu_items = self.tftpgen.get_menu_items()
        for system in system_objs:
            self.sync_single_system(system, menu_items)

        self.logger.info("generating PXE menu structure")
        self.tftpgen.make_pxe_menu()

    def sync(self, verbose: bool = True):
        """
        Write out all files to /tftpdboot

        :param verbose: Whether the tftp server should log this verbose or not.
        """
        self.tftpgen.verbose = verbose
        self.logger.info("copying bootloaders")
        self.tftpgen.copy_bootloaders(self.bootloc)

        self.logger.info("copying distros to tftpboot")

        # Adding in the exception handling to not blow up if files have been moved (or the path references an NFS
        # directory that's no longer mounted)
        for d in self.distros:
            try:
                self.logger.info("copying files for distro: %s", d.name)
                self.tftpgen.copy_single_distro_files(d, self.bootloc, False)
            except CX as e:
                self.logger.error(e.value)

        self.logger.info("copying images")
        self.tftpgen.copy_images()

        # the actual pxelinux.cfg files, for each interface
        self.logger.info("generating PXE configuration files")
        menu_items = self.tftpgen.get_menu_items()
        for system in self.systems:
            self.tftpgen.write_all_system_files(system, menu_items)

        self.logger.info("generating PXE menu structure")
        self.tftpgen.make_pxe_menu()


def get_manager(api):
    """
    Creates a manager object to manage an in_tftp server.

    :param api: The API which holds all information in the current Cobbler instance.
    :return: The object to manage the server with.
    """
    # Singleton used, therefore ignoring 'global'
    global MANAGER  # pylint: disable=global-statement

    if not MANAGER:
        MANAGER = _InTftpdManager(api)
    return MANAGER
