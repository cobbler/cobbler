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

import os
import os.path
import glob
import shutil
import time
import yaml # Howell-Clark version
import sys
import glob
import traceback
import errno
import utils
from cexceptions import *
import templar 
import pxegen
import item_distro
import item_profile
import item_repo
import item_system
from Cheetah.Template import Template
import clogger
from utils import _
import cobbler.module_loader as module_loader


class BootSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config,verbose=True,dhcp=None,dns=None,logger=None,tftpd=None):
        """
        Constructor
        """

        self.logger         = logger
        if logger is None:
            self.logger     = clogger.Logger()

        self.verbose      = verbose
        self.config       = config
        self.api          = config.api
        self.distros      = config.distros()
        self.profiles     = config.profiles()
        self.systems      = config.systems()
        self.settings     = config.settings()
        self.repos        = config.repos()
        self.templar      = templar.Templar(config, self.logger)
        self.pxegen       = pxegen.PXEGen(config, self.logger)
        self.dns          = dns
        self.dhcp         = dhcp
        self.tftpd        = tftpd
        self.bootloc      = utils.tftpboot_location()
        self.pxegen.verbose = verbose
        self.dns.verbose    = verbose
        self.dhcp.verbose   = verbose

        self.pxelinux_dir = os.path.join(self.bootloc, "pxelinux.cfg")
        self.grub_dir = os.path.join(self.bootloc, "grub")
        self.images_dir = os.path.join(self.bootloc, "images")
        self.yaboot_bin_dir = os.path.join(self.bootloc, "ppc")
        self.yaboot_cfg_dir = os.path.join(self.bootloc, "etc")
        self.s390_dir = os.path.join(self.bootloc, "s390x")
        self.rendered_dir = os.path.join(self.settings.webdir, "rendered")



    def run(self):
        """
        Syncs the current configuration file with the config tree.
        Using the Check().run_ functions previously is recommended
        """
        if not os.path.exists(self.bootloc):
            utils.die(self.logger,"cannot find directory: %s" % self.bootloc)

        self.logger.info("running pre-sync triggers")

        # run pre-triggers...
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/sync/pre/*")

        self.distros  = self.config.distros()
        self.profiles = self.config.profiles()
        self.systems  = self.config.systems()
        self.settings = self.config.settings()
        self.repos    = self.config.repos()

        # execute the core of the sync operation
        self.logger.info("cleaning trees")
        self.clean_trees()

        # Have the tftpd module handle copying bootloaders,
        # distros, images, and all_system_files
        self.tftpd.sync(self.verbose)
        # Copy distros to the webdir
        # Adding in the exception handling to not blow up if files have
        # been moved (or the path references an NFS directory that's no longer
        # mounted)
	for d in self.distros:
            try:
                self.logger.info("copying files for distro: %s" % d.name)
                self.pxegen.copy_single_distro_files(d,
                                                     self.settings.webdir,True)
            except CX, e:
                self.logger.error(e.value)

        # make the default pxe menu anyway...
        self.pxegen.make_pxe_menu()

        if self.settings.manage_dhcp:
            self.write_dhcp()
        if self.settings.manage_dns:
            self.logger.info("rendering DNS files")
            self.dns.regen_hosts()
            self.dns.write_dns_files()

        if self.settings.manage_tftpd:
           # xinetd.d/tftpd, basically
           self.logger.info("rendering TFTPD files")
           self.tftpd.write_tftpd_files()
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

        return True

    def make_tftpboot(self):
        """
        Make directories for tftpboot images
        """
        if not os.path.exists(self.pxelinux_dir):
            utils.mkdir(self.pxelinux_dir,logger=self.logger)
        if not os.path.exists(self.grub_dir):
            utils.mkdir(self.grub_dir,logger=self.logger)
        grub_images_link = os.path.join(self.grub_dir, "images")
        if not os.path.exists(grub_images_link):
            os.symlink("../images", grub_images_link)
        if not os.path.exists(self.images_dir):
            utils.mkdir(self.images_dir,logger=self.logger)
        if not os.path.exists(self.s390_dir):
            utils.mkdir(self.s390_dir,logger=self.logger)
        if not os.path.exists(self.rendered_dir):
            utils.mkdir(self.rendered_dir,logger=self.logger)
        if not os.path.exists(self.yaboot_bin_dir):
            utils.mkdir(self.yaboot_bin_dir,logger=self.logger)
        if not os.path.exists(self.yaboot_cfg_dir):
            utils.mkdir(self.yaboot_cfg_dir,logger=self.logger)

    def clean_trees(self):
        """
        Delete any previously built pxelinux.cfg tree and virt tree info and then create
        directories.

        Note: for SELinux reasons, some information goes in /tftpboot, some in /var/www/cobbler
        and some must be duplicated in both.  This is because PXE needs tftp, and auto-kickstart
        and Virt operations need http.   Only the kernel and initrd images are duplicated, which is
        unfortunate, though SELinux won't let me give them two contexts, so symlinks are not
        a solution.  *Otherwise* duplication is minimal.
        """

        # clean out parts of webdir and all of /tftpboot/images and /tftpboot/pxelinux.cfg
        for x in os.listdir(self.settings.webdir):
            path = os.path.join(self.settings.webdir,x)
            if os.path.isfile(path):
                if not x.endswith(".py"):
                    utils.rmfile(path,logger=self.logger)
            if os.path.isdir(path):
                if not x in ["aux", "web", "webui", "localmirror","repo_mirror","ks_mirror","images","links","pub","repo_profile","repo_system","svc","rendered",".link_cache"] :
                    # delete directories that shouldn't exist
                    utils.rmtree(path,logger=self.logger)
                if x in ["kickstarts","kickstarts_sys","images","systems","distros","profiles","repo_profile","repo_system","rendered"]:
                    # clean out directory contents
                    utils.rmtree_contents(path,logger=self.logger)
        #
        self.make_tftpboot()
        utils.rmtree_contents(self.pxelinux_dir,logger=self.logger)
        utils.rmtree_contents(self.grub_dir,logger=self.logger)
        utils.rmtree_contents(self.images_dir,logger=self.logger)
        utils.rmtree_contents(self.s390_dir,logger=self.logger)
        utils.rmtree_contents(self.yaboot_bin_dir,logger=self.logger)
        utils.rmtree_contents(self.yaboot_cfg_dir,logger=self.logger)
        utils.rmtree_contents(self.rendered_dir,logger=self.logger)

    def write_dhcp(self):
        self.logger.info("rendering DHCP files")
        self.dhcp.write_dhcp_file()
        self.dhcp.regen_ethers()

    def sync_dhcp(self):
        restart_dhcp = str(self.settings.restart_dhcp).lower()
        which_dhcp_module = module_loader.get_module_from_file("dhcp","module",just_name=True).strip()

        if self.settings.manage_dhcp:
            self.write_dhcp()
            if which_dhcp_module == "manage_isc":
                if restart_dhcp != "0":
                    rc = utils.subprocess_call(self.logger, "dhcpd -t -q", shell=True)
                    if rc != 0:
                       self.logger.error("dhcpd -t failed")
                       return False
                    rc = utils.subprocess_call(self.logger,"service dhcpd restart", shell=True)
                    if rc != 0:
                       self.logger.error("service dhcpd restart failed")
                       return False
            elif which_dhcp_module == "manage_dnsmasq":
                if restart_dhcp != "0":
                    rc = utils.subprocess_call(self.logger, "service dnsmasq restart")
                    if rc != 0:
                       self.logger.error("service dnsmasq restart failed")
                       return False
        return True

    def clean_link_cache(self):
        for dirtree in [os.path.join(self.bootloc,'images'), self.settings.webdir]:
            cachedir = os.path.join(dirtree,'.link_cache')
            if os.path.isdir(cachedir):
                cmd = "find %s -maxdepth 1 -type f -links 1 -exec rm -f '{}' ';'"%cachedir
                utils.subprocess_call(self.logger,cmd)

    def rsync_gen(self):
        """
        Generate rsync modules of all repositories and distributions
        """
        template_file = "/etc/cobbler/rsync.template"

        try:
            template = open(template_file,"r")
        except:
            raise CX(_("error reading template %s") % template_file)

        template_data = ""
        template_data = template.read()
        template.close()

        distros = []

        for link in glob.glob(os.path.join(self.settings.webdir,'links','*')):
            distro = {}
            distro["path"] = os.path.realpath(link)
            distro["name"] = os.path.basename(link)
            distros.append(distro)

        repos = [ repo.name for repo in self.api.repos()
                  if os.path.isdir(os.path.join(self.settings.webdir,"repo_mirror", repo.name))
                  ]

        metadata = {
           "date"           : time.asctime(time.gmtime()),
           "cobbler_server" : self.settings.server,
           "distros"        : distros,
           "repos"          : repos,
           "webdir"         : self.settings.webdir
        }

        self.templar.render(template_data, metadata, "/etc/rsyncd.conf", None)


