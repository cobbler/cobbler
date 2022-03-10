"""
Builds out filesystem trees/data based on the object tree.
This is the code behind 'cobbler sync'.

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

import glob
import logging
import os
import time
from typing import Optional, List

from cobbler.cexceptions import CX
from cobbler import templar
from cobbler import tftpgen
from cobbler import utils


class CobblerSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self, api, verbose: bool = True, dhcp=None, dns=None, tftpd=None):
        """
        Constructor

        :param api: The API instance which holds all information about cobbler.
        :param verbose: Whether to log the actions performed in this module verbose or not.
        :param dhcp: The DHCP manager which can update the DHCP config.
        :param dns: The DNS manager which can update the DNS config.
        :param tftpd: The TFTP manager which can update the TFTP config.
        """
        self.logger = logging.getLogger()

        self.verbose = verbose
        self.api = api
        self.distros = api.distros()
        self.profiles = api.profiles()
        self.systems = api.systems()
        self.images = api.images()
        self.settings = api.settings()
        self.repos = api.repos()
        self.templar = templar.Templar(self.api)
        self.tftpgen = tftpgen.TFTPGen(api)
        self.dns = dns
        self.dhcp = dhcp
        self.tftpd = tftpd
        self.bootloc = self.settings.tftpboot_location

        self.pxelinux_dir = os.path.join(self.bootloc, "pxelinux.cfg")
        self.grub_dir = os.path.join(self.bootloc, "grub")
        self.images_dir = os.path.join(self.bootloc, "images")
        self.ipxe_dir = os.path.join(self.bootloc, "ipxe")
        self.rendered_dir = os.path.join(self.settings.webdir, "rendered")
        self.links = os.path.join(self.settings.webdir, "links")
        self.distromirror_config = os.path.join(self.settings.webdir, "distro_mirror/config")
        # FIXME: See https://github.com/cobbler/cobbler/issues/2453
        # Move __create_tftpboot_dirs() outside of sync.py.
        self.__create_tftpboot_dirs()

    def run_sync_systems(self, systems: List[str]):
        """
        Syncs the specific systems with the config tree.
        """
        if not os.path.exists(self.bootloc):
            utils.die("cannot find directory: %s" % self.bootloc)

        self.logger.info("running pre-sync triggers")

        # run pre-triggers...
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/sync/pre/*")

        self.distros = self.api.distros()
        self.profiles = self.api.profiles()
        self.systems = self.api.systems()
        self.settings = self.api.settings()
        self.repos = self.api.repos()

        # Have the tftpd module handle copying bootloaders, distros, images, and all_system_files
        self.tftpd.sync_systems(systems)

        if self.settings.manage_dhcp:
            self.write_dhcp()
        if self.settings.manage_dns:
            self.logger.info("rendering DNS files")
            self.dns.regen_hosts()
            self.dns.write_dns_files()

        self.logger.info("cleaning link caches")
        self.clean_link_cache()

        if self.settings.manage_rsync:
            self.logger.info("rendering rsync files")
            self.rsync_gen()

        # run post-triggers
        self.logger.info("running post-sync triggers")
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/sync/post/*")
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/change/*")

    def run(self):
        """
        Syncs the current configuration file with the config tree.
        Using the ``Check().run_`` functions previously is recommended
        """
        if not os.path.exists(self.bootloc):
            utils.die("cannot find directory: %s" % self.bootloc)

        self.logger.info("running pre-sync triggers")

        # run pre-triggers...
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/sync/pre/*")

        self.distros = self.api.distros()
        self.profiles = self.api.profiles()
        self.systems = self.api.systems()
        self.settings = self.api.settings()
        self.repos = self.api.repos()

        # execute the core of the sync operation
        self.logger.info("cleaning trees")
        self.clean_trees()

        # Have the tftpd module handle copying bootloaders, distros, images, and all_system_files
        self.tftpd.sync(self.verbose)
        # Copy distros to the webdir
        # Adding in the exception handling to not blow up if files have been moved (or the path references an NFS
        # directory that's no longer mounted)
        for d in self.distros:
            try:
                self.logger.info("copying files for distro: %s" % d.name)
                self.tftpgen.copy_single_distro_files(d, self.settings.webdir, True)
                self.tftpgen.write_templates(d, write_file=True)
            except CX as e:
                self.logger.error(e.value)

        # make the default pxe menu anyway...
        self.tftpgen.make_pxe_menu()

        if self.settings.manage_dhcp:
            self.write_dhcp()
        if self.settings.manage_dns:
            self.logger.info("rendering DNS files")
            self.dns.regen_hosts()
            self.dns.write_configs()

        if self.settings.manage_tftpd:
            # copy in boot_files
            self.tftpd.write_boot_files()

        self.logger.info("cleaning link caches")
        self.clean_link_cache()

        if self.settings.manage_rsync:
            self.logger.info("rendering Rsync files")
            self.rsync_gen()

        # run post-triggers
        self.logger.info("running post-sync triggers")
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/sync/post/*")
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/change/*")

    def __create_tftpboot_dirs(self):
        """
        Create directories for tftpboot images
        """
        if not os.path.exists(self.pxelinux_dir):
            utils.mkdir(self.pxelinux_dir)
        if not os.path.exists(self.grub_dir):
            utils.mkdir(self.grub_dir)
        grub_images_link = os.path.join(self.grub_dir, "images")
        if not os.path.exists(grub_images_link):
            os.symlink("../images", grub_images_link)
        if not os.path.exists(self.images_dir):
            utils.mkdir(self.images_dir)
        if not os.path.exists(self.rendered_dir):
            utils.mkdir(self.rendered_dir)
        if not os.path.exists(self.ipxe_dir):
            utils.mkdir(self.ipxe_dir)
        if not os.path.exists(self.links):
            utils.mkdir(self.links)
        if not os.path.exists(self.distromirror_config):
            utils.mkdir(self.distromirror_config)

    def clean_trees(self):
        """
        Delete any previously built pxelinux.cfg tree and virt tree info and then create directories.

        Note: for SELinux reasons, some information goes in ``/tftpboot``, some in ``/var/www/cobbler`` and some must be
        duplicated in both. This is because PXE needs tftp, and automatic installation and Virt operations need http.
        Only the kernel and initrd images are duplicated, which is unfortunate, though SELinux won't let me give them
        two contexts, so symlinks are not a solution. *Otherwise* duplication is minimal.
        """

        # clean out parts of webdir and all of /tftpboot/images and /tftpboot/pxelinux.cfg
        for x in os.listdir(self.settings.webdir):
            path = os.path.join(self.settings.webdir, x)
            if os.path.isfile(path):
                if not x.endswith(".py"):
                    utils.rmfile(path)
            if os.path.isdir(path):
                if x not in self.settings.webdir_whitelist:
                    # delete directories that shouldn't exist
                    utils.rmtree(path)
                if x in ["templates", "images", "systems", "distros", "profiles", "repo_profile", "repo_system",
                         "rendered"]:
                    # clean out directory contents
                    utils.rmtree_contents(path)
        self.__create_tftpboot_dirs()
        utils.rmtree_contents(self.pxelinux_dir)
        utils.rmtree_contents(self.grub_dir)
        utils.rmtree_contents(self.images_dir)
        utils.rmtree_contents(self.ipxe_dir)
        utils.rmtree_contents(self.rendered_dir)

    def write_dhcp(self):
        """
        Write all files which are associated to DHCP.
        """
        self.logger.info("rendering DHCP files")
        self.dhcp.write_configs()
        self.dhcp.regen_ethers()

    def sync_dhcp(self):
        """
        This calls write_dhcp and restarts the DHCP server.
        """
        if self.settings.manage_dhcp:
            self.write_dhcp()
            self.dhcp.sync_dhcp()

    def clean_link_cache(self):
        """
        All files which are linked into the cache will be deleted so the cache can be rebuild.
        """
        for dirtree in [os.path.join(self.bootloc, 'images'), self.settings.webdir]:
            cachedir = os.path.join(dirtree, '.link_cache')
            if os.path.isdir(cachedir):
                cmd = ["find", cachedir, "-maxdepth", "1", "-type", "f", "-links", "1", "-exec", "rm", "-f"]
                utils.subprocess_call(cmd, shell=False)

    def rsync_gen(self):
        """
        Generate rsync modules of all repositories and distributions

        :raises OSError:
        """
        template_file = "/etc/cobbler/rsync.template"

        try:
            template = open(template_file, "r")
        except:
            raise OSError("error reading template %s" % template_file)

        template_data = ""
        template_data = template.read()
        template.close()

        distros = []

        for link in glob.glob(os.path.join(self.settings.webdir, 'links', '*')):
            distro = {}
            distro["path"] = os.path.realpath(link)
            distro["name"] = os.path.basename(link)
            distros.append(distro)

        repos = [repo.name for repo in self.api.repos()
                 if os.path.isdir(os.path.join(self.settings.webdir, "repo_mirror", repo.name))]

        metadata = {
            "date": time.asctime(time.gmtime()),
            "cobbler_server": self.settings.server,
            "distros": distros,
            "repos": repos,
            "webdir": self.settings.webdir
        }

        self.templar.render(template_data, metadata, "/etc/rsyncd.conf")

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
        self.tftpgen.copy_single_distro_files(distro, self.settings.webdir, True)
        self.tftpd.add_single_distro(distro)

        # create the symlink for this distro
        src_dir = utils.find_distro_path(self.settings, distro)
        dst_dir = os.path.join(self.settings.webdir, "links", name)
        if os.path.exists(dst_dir):
            self.logger.warning("skipping symlink, destination (%s) exists", dst_dir)
        elif utils.path_tail(os.path.join(self.settings.webdir, "distro_mirror"), src_dir) == "":
            self.logger.warning("skipping symlink, the source (%s) is not in %s",
                                src_dir, os.path.join(self.settings.webdir, "distro_mirror"))
        else:
            try:
                self.logger.info("trying symlink %s -> %s", src_dir, dst_dir)
                os.symlink(src_dir, dst_dir)
            except (IOError, OSError):
                self.logger.error("symlink failed (%s -> %s)", src_dir, dst_dir)

        # generate any templates listed in the distro
        self.tftpgen.write_templates(distro, write_file=True)
        # cascade sync
        kids = distro.get_children()
        for k in kids:
            self.add_single_profile(k, rebuild_menu=False)
        self.tftpgen.make_pxe_menu()

    def add_single_image(self, name):
        """
        Sync adding a single image.

        :param name: The name of the image.
        """
        image = self.images.find(name=name)
        self.tftpgen.copy_single_image_files(image)
        kids = image.get_children()
        for k in kids:
            self.add_single_system(k)
        self.tftpgen.make_pxe_menu()

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
        # delete potential distro config files
        utils.rmglob_files(os.path.join(self.settings.webdir, "distro_mirror", "config"), name + "*.repo")

    def remove_single_image(self, name):
        """
        Sync removing a single image.

        :param name: The name of the image.
        """
        bootloc = self.settings.tftpboot_location
        utils.rmfile(os.path.join(bootloc, "images2", name))

    def add_single_profile(self, name: str, rebuild_menu: bool = True) -> Optional[bool]:
        """
        Sync adding a single profile.

        :param name: The name of the profile.
        :param rebuild_menu: Whether to rebuild the grub/... menu or not.
        :return: ``True`` if this succeeded.
        """
        # get the profile object:
        profile = self.profiles.find(name=name)
        if profile is None:
            # Most likely a subprofile's kid has been removed already, though the object tree has not been reloaded and
            # this is just noise.
            return
        # Rebuild the yum configuration files for any attached repos generate any templates listed in the distro.
        self.tftpgen.write_templates(profile)
        # Cascade sync
        kids = profile.children
        for k in kids:
            if self.api.find_profile(name=k) is not None:
                self.add_single_profile(k, rebuild_menu=False)
            else:
                self.add_single_system(k)
        if rebuild_menu:
            self.tftpgen.make_pxe_menu()
        return True

    def remove_single_profile(self, name: str, rebuild_menu: bool = True):
        """
        Sync removing a single profile.

        :param name: The name of the profile.
        :param rebuild_menu: Whether to rebuild the grub/... menu or not.
        """
        # delete profiles/$name file in webdir
        utils.rmfile(os.path.join(self.settings.webdir, "profiles", name))
        # delete contents on autoinstalls/$name directory in webdir
        utils.rmtree(os.path.join(self.settings.webdir, "autoinstalls", name))
        if rebuild_menu:
            self.tftpgen.make_pxe_menu()

    def update_system_netboot_status(self, name: str):
        """
        Update the netboot status of a system.

        :param name: The name of the system.
        """
        system = self.systems.find(name=name)
        if system is None:
            return
        self.tftpd.sync_single_system(system)

    def add_single_system(self, name: str):
        """
        Sync adding a single system.

        :param name: The name of the system.
        """
        # get the system object:
        system = self.systems.find(name=name)
        if system is None:
            return
        # rebuild system_list file in webdir
        if self.settings.manage_dhcp:
            self.dhcp.regen_ethers()
        if self.settings.manage_dns:
            self.dns.regen_hosts()
        # write the PXE files for the system
        self.tftpd.sync_single_system(system)

    def remove_single_system(self, name: str):
        """
        Sync removing a single system.

        :param name: The name of the system.
        """
        bootloc = self.settings.tftpboot_location
        # delete contents of autoinsts_sys/$name in webdir
        system_record = self.systems.find(name=name)

        for (name, interface) in list(system_record.interfaces.items()):
            pxe_filename = system_record.get_config_filename(interface=name, loader="pxe")
            grub_filename = system_record.get_config_filename(interface=name, loader="grub")
            utils.rmfile(os.path.join(bootloc, "pxelinux.cfg", pxe_filename))
            utils.rmfile(os.path.join(bootloc, "grub", "system", grub_filename))
            utils.rmfile(os.path.join(bootloc, "grub", "system_link", system_record.name))

    def remove_single_menu(self, rebuild_menu: bool = True):
        """
        Sync removing a single menu.
        :param rebuild_menu: Whether to rebuild the grub/... menu or not.
        """
        if rebuild_menu:
            self.tftpgen.make_pxe_menu()
