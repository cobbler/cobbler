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

from builtins import object
import glob
import os
import time

from cobbler.cexceptions import CX
from cobbler import clogger
from cobbler import templar
from cobbler import tftpgen
from cobbler import utils
from cobbler.utils import _


class CobblerSync(object):
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self, collection_mgr, verbose=True, dhcp=None, dns=None, logger=None, tftpd=None):
        """
        Constructor

        :param collection_mgr: The collection manager instance which holds all information about cobbler.
        :param verbose: Whether to log the actions performed in this module verbose or not.
        :param dhcp: The DHCP manager which can update the DHCP config.
        :param dns: The DNS manager which can update the DNS config.
        :param logger: The logger to audit all action with.
        :param tftpd: The TFTP manager which can update the TFTP config.
        """
        self.logger = logger
        if logger is None:
            self.logger = clogger.Logger()

        self.verbose = verbose
        self.collection_mgr = collection_mgr
        self.api = collection_mgr.api
        self.distros = collection_mgr.distros()
        self.profiles = collection_mgr.profiles()
        self.systems = collection_mgr.systems()
        self.settings = collection_mgr.settings()
        self.repos = collection_mgr.repos()
        self.templar = templar.Templar(collection_mgr, self.logger)
        self.tftpgen = tftpgen.TFTPGen(collection_mgr, self.logger)
        self.dns = dns
        self.dhcp = dhcp
        self.tftpd = tftpd
        self.bootloc = self.settings.tftpboot_location
        self.tftpgen.verbose = verbose
        self.dns.verbose = verbose
        self.dhcp.verbose = verbose

        self.pxelinux_dir = os.path.join(self.bootloc, "pxelinux.cfg")
        self.grub_dir = os.path.join(self.bootloc, "grub")
        self.images_dir = os.path.join(self.bootloc, "images")
        self.yaboot_bin_dir = os.path.join(self.bootloc, "ppc")
        self.yaboot_cfg_dir = os.path.join(self.bootloc, "etc")
        self.rendered_dir = os.path.join(self.settings.webdir, "rendered")

    def run(self):
        """
        Syncs the current configuration file with the config tree.
        Using the ``Check().run_`` functions previously is recommended
        """
        if not os.path.exists(self.bootloc):
            utils.die(self.logger, "cannot find directory: %s" % self.bootloc)

        self.logger.info("running pre-sync triggers")

        # run pre-triggers...
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/sync/pre/*")

        self.distros = self.collection_mgr.distros()
        self.profiles = self.collection_mgr.profiles()
        self.systems = self.collection_mgr.systems()
        self.settings = self.collection_mgr.settings()
        self.repos = self.collection_mgr.repos()

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
            self.dns.write_dns_files()

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
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/sync/post/*", logger=self.logger)
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/change/*", logger=self.logger)

    def make_tftpboot(self):
        """
        Make directories for tftpboot images
        """
        if not os.path.exists(self.pxelinux_dir):
            utils.mkdir(self.pxelinux_dir, logger=self.logger)
        if not os.path.exists(self.grub_dir):
            utils.mkdir(self.grub_dir, logger=self.logger)
        grub_images_link = os.path.join(self.grub_dir, "images")
        if not os.path.exists(grub_images_link):
            os.symlink("../images", grub_images_link)
        if not os.path.exists(self.images_dir):
            utils.mkdir(self.images_dir, logger=self.logger)
        if not os.path.exists(self.rendered_dir):
            utils.mkdir(self.rendered_dir, logger=self.logger)
        if not os.path.exists(self.yaboot_bin_dir):
            utils.mkdir(self.yaboot_bin_dir, logger=self.logger)
        if not os.path.exists(self.yaboot_cfg_dir):
            utils.mkdir(self.yaboot_cfg_dir, logger=self.logger)

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
                    utils.rmfile(path, logger=self.logger)
            if os.path.isdir(path):
                if x not in self.settings.webdir_whitelist:
                    # delete directories that shouldn't exist
                    utils.rmtree(path, logger=self.logger)
                if x in ["autoinstall_templates", "autoinstall_templates_sys", "images", "systems", "distros", "profiles", "repo_profile", "repo_system", "rendered"]:
                    # clean out directory contents
                    utils.rmtree_contents(path, logger=self.logger)
        #
        self.make_tftpboot()
        utils.rmtree_contents(self.pxelinux_dir, logger=self.logger)
        utils.rmtree_contents(self.grub_dir, logger=self.logger)
        utils.rmtree_contents(self.images_dir, logger=self.logger)
        utils.rmtree_contents(self.yaboot_bin_dir, logger=self.logger)
        utils.rmtree_contents(self.yaboot_cfg_dir, logger=self.logger)
        utils.rmtree_contents(self.rendered_dir, logger=self.logger)

    def write_dhcp(self):
        """
        Write all files which are associated to DHCP.
        """
        self.logger.info("rendering DHCP files")
        self.dhcp.write_dhcp_file()
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
                cmd = "find %s -maxdepth 1 -type f -links 1 -exec rm -f '{}' ';'" % cachedir
                utils.subprocess_call(self.logger, cmd)

    def rsync_gen(self):
        """
        Generate rsync modules of all repositories and distributions
        """
        template_file = "/etc/cobbler/rsync.template"

        try:
            template = open(template_file, "r")
        except:
            raise CX(_("error reading template %s") % template_file)

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

        self.templar.render(template_data, metadata, "/etc/rsyncd.conf", None)
