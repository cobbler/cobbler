"""
Builds out filesystem trees/data based on the object tree.
This is the code behind 'cobbler sync'.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import glob
import logging
import os
import time
from typing import TYPE_CHECKING, Dict, List, Optional

from cobbler import templar, tftpgen, utils
from cobbler.cexceptions import CX
from cobbler.utils import filesystem_helpers

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.distro import Distro
    from cobbler.items.image import Image
    from cobbler.items.profile import Profile
    from cobbler.items.system import System
    from cobbler.modules.managers import (
        DhcpManagerModule,
        DnsManagerModule,
        TftpManagerModule,
    )


class CobblerSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(
        self,
        api: "CobblerAPI",
        verbose: bool = True,
        dhcp: Optional["DhcpManagerModule"] = None,
        dns: Optional["DnsManagerModule"] = None,
        tftpd: Optional["TftpManagerModule"] = None,
    ) -> None:
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
        if dns is None:
            raise ValueError("dns not optional")
        self.dns = dns
        if dhcp is None:
            raise ValueError("dns not optional")
        self.dhcp = dhcp
        if tftpd is None:
            raise ValueError("dns not optional")
        self.tftpd = tftpd
        self.bootloc = self.settings.tftpboot_location

        self.pxelinux_dir = os.path.join(self.bootloc, "pxelinux.cfg")
        self.grub_dir = os.path.join(self.bootloc, "grub")
        self.images_dir = os.path.join(self.bootloc, "images")
        self.ipxe_dir = os.path.join(self.bootloc, "ipxe")
        self.esxi_dir = os.path.join(self.bootloc, "esxi")
        self.rendered_dir = os.path.join(self.settings.webdir, "rendered")
        self.links = os.path.join(self.settings.webdir, "links")
        self.distromirror_config = os.path.join(
            self.settings.webdir, "distro_mirror/config"
        )
        filesystem_helpers.create_tftpboot_dirs(self.api)
        filesystem_helpers.create_web_dirs(self.api)

    def __common_run(self):
        """
        Common startup code for the different sync algorithms
        """
        if not os.path.exists(self.bootloc):
            utils.die(f"cannot find directory: {self.bootloc}")

        self.logger.info("running pre-sync triggers")

        # run pre-triggers...
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/sync/pre/*")

        self.distros = self.api.distros()
        self.profiles = self.api.profiles()
        self.systems = self.api.systems()
        self.settings = self.api.settings()
        self.repos = self.api.repos()

    def run_sync_systems(self, systems: List[str]):
        """
        Syncs the specific systems with the config tree.
        """
        self.__common_run()

        # Have the tftpd module handle copying bootloaders, distros, images, and all_system_files
        self.tftpd.sync_systems(systems)

        if self.settings.manage_dhcp:
            self.write_dhcp()
        if self.settings.manage_dns:
            self.logger.info("rendering DNS files")
            self.dns.regen_hosts()
            self.dns.write_configs()

        self.logger.info("cleaning link caches")
        self.clean_link_cache()

        if self.settings.manage_rsync:
            self.logger.info("rendering rsync files")
            self.rsync_gen()

        # run post-triggers
        self.logger.info("running post-sync triggers")
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/sync/post/*")
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/change/*")

    def run(self) -> None:
        """
        Syncs the current configuration file with the config tree.
        Using the ``Check().run_`` functions previously is recommended
        """
        self.__common_run()

        # execute the core of the sync operation
        self.logger.info("cleaning trees")
        self.clean_trees()

        # Have the tftpd module handle copying bootloaders, distros, images, and all_system_files
        self.tftpd.sync()
        # Copy distros to the webdir
        # Adding in the exception handling to not blow up if files have been moved (or the path references an NFS
        # directory that's no longer mounted)
        for distro in self.distros:
            try:
                self.logger.info("copying files for distro: %s", distro.name)
                self.tftpgen.copy_single_distro_files(
                    distro, self.settings.webdir, True
                )
                self.tftpgen.write_templates(distro, write_file=True)
            except CX as cobbler_exception:
                self.logger.error(cobbler_exception.value)

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

    def clean_trees(self):
        """
        Delete any previously built pxelinux.cfg tree and virt tree info and then create directories.

        Note: for SELinux reasons, some information goes in ``/tftpboot``, some in ``/var/www/cobbler`` and some must be
        duplicated in both. This is because PXE needs tftp, and automatic installation and Virt operations need http.
        Only the kernel and initrd images are duplicated, which is unfortunate, though SELinux won't let me give them
        two contexts, so symlinks are not a solution. *Otherwise* duplication is minimal.
        """

        # clean out parts of webdir and all of /tftpboot/images and /tftpboot/pxelinux.cfg
        for file_obj in os.listdir(self.settings.webdir):
            path = os.path.join(self.settings.webdir, file_obj)
            if os.path.isfile(path):
                if not file_obj.endswith(".py"):
                    filesystem_helpers.rmfile(path)
            if os.path.isdir(path):
                if file_obj not in self.settings.webdir_whitelist:
                    # delete directories that shouldn't exist
                    filesystem_helpers.rmtree(path)
                if file_obj in [
                    "templates",
                    "images",
                    "systems",
                    "distros",
                    "profiles",
                    "repo_profile",
                    "repo_system",
                    "rendered",
                ]:
                    # clean out directory contents
                    filesystem_helpers.rmtree_contents(path)
        for file_obj in [
            self.pxelinux_dir,
            self.grub_dir,
            self.images_dir,
            self.ipxe_dir,
            self.esxi_dir,
            self.rendered_dir,
        ]:
            filesystem_helpers.rmtree(file_obj)
        filesystem_helpers.create_tftpboot_dirs(self.api)

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
        for dirtree in [os.path.join(self.bootloc, "images"), self.settings.webdir]:
            cachedir = os.path.join(dirtree, ".link_cache")
            if os.path.isdir(cachedir):
                cmd = [
                    "find",
                    cachedir,
                    "-maxdepth",
                    "1",
                    "-type",
                    "f",
                    "-links",
                    "1",
                    "-exec",
                    "rm",
                    "-f",
                    "{}",
                    ";",
                ]
                utils.subprocess_call(cmd, shell=False)

    def rsync_gen(self) -> None:
        """
        Generate rsync modules of all repositories and distributions

        :raises OSError:
        """
        template_file = "/etc/cobbler/rsync.template"

        try:
            with open(template_file, "r", encoding="UTF-8") as template:
                template_data = template.read()
        except Exception as error:
            raise OSError(f"error reading template {template_file}") from error

        distros: List[Dict[str, str]] = []

        for link in glob.glob(os.path.join(self.settings.webdir, "links", "*")):
            distro = {}
            distro["path"] = os.path.realpath(link)
            distro["name"] = os.path.basename(link)
            distros.append(distro)

        repos = [
            repo.name
            for repo in self.api.repos()
            if os.path.isdir(
                os.path.join(self.settings.webdir, "repo_mirror", repo.name)
            )
        ]

        metadata = {
            "date": time.asctime(time.gmtime()),
            "cobbler_server": self.settings.server,
            "distros": distros,
            "repos": repos,
            "webdir": self.settings.webdir,
        }

        self.templar.render(template_data, metadata, "/etc/rsyncd.conf")

    def add_single_distro(self, distro_obj: "Distro") -> None:
        """
        Sync adding a single distro.

        :param name: The name of the distribution.
        """
        # copy image files to images/$name in webdir & tftpboot:
        self.tftpgen.copy_single_distro_files(distro_obj, self.settings.webdir, True)
        self.tftpd.add_single_distro(distro_obj)

        # create the symlink for this distro
        src_dir = distro_obj.find_distro_path()
        dst_dir = os.path.join(self.settings.webdir, "links", distro_obj.name)
        if os.path.exists(dst_dir):
            self.logger.warning("skipping symlink, destination (%s) exists", dst_dir)
        elif (
            filesystem_helpers.path_tail(
                os.path.join(self.settings.webdir, "distro_mirror"), src_dir
            )
            == ""
        ):
            self.logger.warning(
                "skipping symlink, the source (%s) is not in %s",
                src_dir,
                os.path.join(self.settings.webdir, "distro_mirror"),
            )
        else:
            try:
                self.logger.info("trying symlink %s -> %s", src_dir, dst_dir)
                os.symlink(src_dir, dst_dir)
            except (IOError, OSError):
                self.logger.error("symlink failed (%s -> %s)", src_dir, dst_dir)

        # generate any templates listed in the distro
        self.tftpgen.write_templates(distro_obj, write_file=True)
        # cascade sync
        kids = self.api.find_profile(return_list=True, **{"distro": distro_obj.name})
        if not isinstance(kids, list):
            raise ValueError("Expected to get list of profiles from search!")
        for k in kids:
            self.add_single_profile(k, rebuild_menu=False)
        self.tftpgen.make_pxe_menu()

    def add_single_image(self, image_obj: "Image") -> None:
        """
        Sync adding a single image.

        :param name: The name of the image.
        """
        self.tftpgen.copy_single_image_files(image_obj)
        kids = self.api.find_system(return_list=True, **{"image": image_obj.name})
        if not isinstance(kids, list):
            raise ValueError("Expected to get list of profiles from search!")
        for k in kids:
            self.add_single_system(k)
        self.tftpgen.make_pxe_menu()

    def remove_single_distro(self, distro_obj: "Distro") -> None:
        """
        Sync removing a single distro.

        :param name: The name of the distribution.
        """
        bootloc = self.settings.tftpboot_location
        # delete contents of images/$name directory in webdir
        filesystem_helpers.rmtree(
            os.path.join(self.settings.webdir, "images", distro_obj.name)
        )
        # delete contents of images/$name in tftpboot
        filesystem_helpers.rmtree(os.path.join(bootloc, "images", distro_obj.name))
        # delete potential symlink to tree in webdir/links
        filesystem_helpers.rmfile(
            os.path.join(self.settings.webdir, "links", distro_obj.name)
        )
        # delete potential distro config files
        filesystem_helpers.rmglob_files(
            os.path.join(self.settings.webdir, "distro_mirror", "config"),
            distro_obj.name + "*.repo",
        )

    def remove_single_image(self, image_obj: "Image") -> None:
        """
        Sync removing a single image.

        :param image_obj: The name of the image.
        """
        bootloc = self.settings.tftpboot_location
        filesystem_helpers.rmfile(os.path.join(bootloc, "images2", image_obj.name))

    def add_single_profile(
        self, profile: "Profile", rebuild_menu: bool = True
    ) -> Optional[bool]:
        """
        Sync adding a single profile.

        :param name: The name of the profile.
        :param rebuild_menu: Whether to rebuild the grub/... menu or not.
        :return: ``True`` if this succeeded.
        """
        if profile is None or isinstance(profile, list):  # type: ignore
            # Most likely a subprofile's kid has been removed already, though the object tree has not been reloaded and
            # this is just noise.
            return None
        # Rebuild the yum configuration files for any attached repos generate any templates listed in the distro.
        self.tftpgen.write_templates(profile)
        # Cascade sync
        kids = profile.children
        for k in kids:
            self.add_single_profile(k, rebuild_menu=False)  # type: ignore
        kids = self.api.find_system(return_list=True, **{"profile": profile.name})
        if not isinstance(kids, list):
            raise ValueError("Expected to get list of profiles from search!")
        for k in kids:
            self.add_single_system(k)
        if rebuild_menu:
            self.tftpgen.make_pxe_menu()
        return True

    def remove_single_profile(
        self, profile_obj: "Profile", rebuild_menu: bool = True
    ) -> None:
        """
        Sync removing a single profile.

        :param name: The name of the profile.
        :param rebuild_menu: Whether to rebuild the grub/... menu or not.
        """
        # delete profiles/$name file in webdir
        filesystem_helpers.rmfile(
            os.path.join(self.settings.webdir, "profiles", profile_obj.name)
        )
        # delete contents on autoinstalls/$name directory in webdir
        filesystem_helpers.rmtree(
            os.path.join(self.settings.webdir, "autoinstalls", profile_obj.name)
        )
        if rebuild_menu:
            self.tftpgen.make_pxe_menu()

    def update_system_netboot_status(self, name: str) -> None:
        """
        Update the netboot status of a system.

        :param name: The name of the system.
        """
        system = self.systems.find(name=name)
        if system is None or isinstance(system, list):
            return
        self.tftpd.sync_single_system(system)

    def add_single_system(self, system_obj: "System") -> None:
        """
        Sync adding a single system.

        :param name: The name of the system.
        """
        # rebuild system_list file in webdir
        if self.settings.manage_dhcp:
            self.dhcp.regen_ethers()
        if self.settings.manage_dns:
            self.dns.regen_hosts()
        # write the PXE files for the system
        self.tftpd.sync_single_system(system_obj)

    def remove_single_system(self, system_obj: "System") -> None:
        """
        Sync removing a single system.

        :param name: The name of the system.
        """
        bootloc = self.settings.tftpboot_location
        # delete contents of autoinsts_sys/$name in webdir
        for (interface_name, _) in list(system_obj.interfaces.items()):
            pxe_filename = system_obj.get_config_filename(
                interface=interface_name, loader="pxe"
            )
            grub_filename = system_obj.get_config_filename(
                interface=interface_name, loader="grub"
            )
            if pxe_filename is not None:
                filesystem_helpers.rmfile(
                    os.path.join(bootloc, "pxelinux.cfg", pxe_filename)
                )
            if not (system_obj.name == "default" and grub_filename is None):
                # A default system can't have GRUB entries and thus we want to skip this.
                filesystem_helpers.rmfile(
                    os.path.join(bootloc, "grub", "system", grub_filename)  # type: ignore
                )
            filesystem_helpers.rmfile(
                os.path.join(bootloc, "grub", "system_link", system_obj.name)
            )
            if pxe_filename is not None:
                filesystem_helpers.rmtree(os.path.join(bootloc, "esxi", pxe_filename))

    def remove_single_menu(self, rebuild_menu: bool = True) -> None:
        """
        Sync removing a single menu.

        :param rebuild_menu: Whether to rebuild the grub/... menu or not.
        """
        if rebuild_menu:
            self.tftpgen.make_pxe_menu()
