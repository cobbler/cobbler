"""
Running small pieces of Cobbler sync when certain actions are taken,
such that we don't need a time consuming sync when adding new
systems if nothing has changed for systems that have already
been created.

Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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

from builtins import object
import os
import os.path

from cobbler import clogger
from cobbler import module_loader
from cobbler import utils


class CobblerLiteSync(object):
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self, collection_mgr, verbose=False, logger=None):
        """
        Constructor

        :param collection_mgr: The collection manager which has all information.
        :param verbose: Whether the action should be logged verbose.
        :type verbose: bool
        :param logger: The logger to audit all action with.
        """
        self.verbose = verbose
        self.collection_mgr = collection_mgr
        self.distros = collection_mgr.distros()
        self.profiles = collection_mgr.profiles()
        self.systems = collection_mgr.systems()
        self.images = collection_mgr.images()
        self.settings = collection_mgr.settings()
        self.repos = collection_mgr.repos()
        if logger is None:
            logger = clogger.Logger()
        self.logger = logger
        self.tftpd = module_loader.get_module_from_file("tftpd", "module", "in_tftpd").get_manager(collection_mgr, logger)
        self.sync = collection_mgr.api.get_sync(verbose, logger=self.logger)
        self.sync.make_tftpboot()

    def add_single_distro(self, name):
        """
        Sync adding a single distro.

        :param name: The name of the distribution.
        """
        # get the distro record
        distro = self.distros.find(name=name)
        if distro is None:
            return
        # copy image files to images/$name in webdir & tftpboot:
        self.sync.tftpgen.copy_single_distro_files(distro, self.settings.webdir, True)
        self.tftpd.add_single_distro(distro)

        # create the symlink for this distro
        src_dir = utils.find_distro_path(self.settings, distro)
        dst_dir = os.path.join(self.settings.webdir, "links", name)
        if os.path.exists(dst_dir):
            self.logger.warning("skipping symlink, destination (%s) exists" % dst_dir)
        elif utils.path_tail(os.path.join(self.settings.webdir, "distro_mirror"), src_dir) == "":
            self.logger.warning("skipping symlink, the source (%s) is not in %s" % (src_dir, os.path.join(self.settings.webdir, "distro_mirror")))
        else:
            try:
                self.logger.info("trying symlink %s -> %s" % (src_dir, dst_dir))
                os.symlink(src_dir, dst_dir)
            except (IOError, OSError):
                self.logger.error("symlink failed (%s -> %s)" % (src_dir, dst_dir))

        # generate any templates listed in the distro
        self.sync.tftpgen.write_templates(distro, write_file=True)
        # cascade sync
        kids = distro.get_children()
        for k in kids:
            self.add_single_profile(k.name, rebuild_menu=False)
        self.sync.tftpgen.make_pxe_menu()

    def add_single_image(self, name):
        """
        Sync adding a single image.

        :param name: The name of the image.
        """
        image = self.images.find(name=name)
        self.sync.tftpgen.copy_single_image_files(image)
        kids = image.get_children()
        for k in kids:
            self.add_single_system(k.name)
        self.sync.tftpgen.make_pxe_menu()

    def remove_single_distro(self, name):
        """
        Sync removing a single distro.

        :param name: The name of the distribution.
        """
        bootloc = self.settings.tftpboot_location
        # delete contents of images/$name directory in webdir
        utils.rmtree(os.path.join(self.settings.webdir, "images", name))
        # delete contents of images/$name in tftpboot
        utils.rmtree(os.path.join(bootloc, "images", name))
        # delete potential symlink to tree in webdir/links
        utils.rmfile(os.path.join(self.settings.webdir, "links", name))

    def remove_single_image(self, name):
        """
        Sync removing a single image.

        :param name: The name of the image.
        """
        bootloc = self.settings.tftpboot_location
        utils.rmfile(os.path.join(bootloc, "images2", name))

    def add_single_profile(self, name, rebuild_menu=True):
        """
        Sync adding a single profile.

        :param name: The name of the profile.
        :type name: str
        :param rebuild_menu: Whether to rebuild the grub/... menu or not.
        :type rebuild_menu: bool
        :return: ``True`` if this succeeded.
        """
        # get the profile object:
        profile = self.profiles.find(name=name)
        if profile is None:
            # Most likely a subprofile's kid has been removed already, though the object tree has not been reloaded and
            # this is just noise.
            return
        # Rebuild the yum configuration files for any attached repos generate any templates listed in the distro.
        self.sync.tftpgen.write_templates(profile)
        # Cascade sync
        kids = profile.get_children()
        for k in kids:
            if k.COLLECTION_TYPE == "profile":
                self.add_single_profile(k.name, rebuild_menu=False)
            else:
                self.add_single_system(k.name)
        if rebuild_menu:
            self.sync.tftpgen.make_pxe_menu()
        return True

    def remove_single_profile(self, name, rebuild_menu=True):
        """
        Sync removing a single profile.

        :param name: The name of the profile.
        :type name: str
        :param rebuild_menu: Whether to rebuild the grub/... menu or not.
        :type rebuild_menu: bool
        """
        # delete profiles/$name file in webdir
        utils.rmfile(os.path.join(self.settings.webdir, "profiles", name))
        # delete contents on autoinstalls/$name directory in webdir
        utils.rmtree(os.path.join(self.settings.webdir, "autoinstalls", name))
        if rebuild_menu:
            self.sync.tftpgen.make_pxe_menu()

    def update_system_netboot_status(self, name):
        """
        Update the netboot status of a system.

        :param name: The name of the system.
        :type name: str
        """
        self.tftpd.update_netboot(name)

    def add_single_system(self, name):
        """
        Sync adding a single system.

        :param name: The name of the system.
        :type name: str
        """
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
        self.tftpd.add_single_system(system)

    def remove_single_system(self, name):
        """
        Sync removing a single system.

        :param name: The name of the system.
        :type name: str
        """
        bootloc = self.settings.tftpboot_location
        # delete contents of autoinsts_sys/$name in webdir
        system_record = self.systems.find(name=name)

        for (name, interface) in list(system_record.interfaces.items()):
            filename = system_record.get_config_filename(interface=name)
            utils.rmfile(os.path.join(bootloc, "pxelinux.cfg", filename))
            utils.rmfile(os.path.join(bootloc, "grub", filename.upper()))
