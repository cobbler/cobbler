"""
Builds out filesystem trees/data based on the object tree.
This is the code behind 'cobbler sync'.

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


class BootSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config,verbose=True,dhcp=None,dns=None,logger=None):
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
        self.bootloc      = utils.tftpboot_location()
        self.pxegen.verbose = verbose
        self.dns.verbose    = verbose
        self.dhcp.verbose   = verbose

        self.pxelinux_dir = os.path.join(self.bootloc, "pxelinux.cfg")
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

        if self.verbose:
            self.logger.info("running pre-sync triggers")

        # run pre-triggers...
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/sync/pre/*")

        self.distros  = self.config.distros()
        self.profiles = self.config.profiles()
        self.systems  = self.config.systems()
        self.settings = self.config.settings()
        self.repos    = self.config.repos()

        # execute the core of the sync operation

        if self.verbose:
           self.logger.info("cleaning trees")
        self.clean_trees()

        if self.verbose:
           self.logger.info("copying bootloaders")
        self.pxegen.copy_bootloaders()

        if self.verbose:
           self.logger.info("copying distros")
        self.pxegen.copy_distros()

        if self.verbose:
           self.logger.info("copying images")
        self.pxegen.copy_images()

        for x in self.systems:
            self.pxegen.write_all_system_files(x)

        if self.settings.manage_dhcp:
           if self.verbose:
                self.logger.info("rendering DHCP files")
           self.dhcp.write_dhcp_file()
           self.dhcp.regen_ethers()
        if self.settings.manage_dns:
           if self.verbose:
                self.logger.info("rendering DNS files")
           self.dns.regen_hosts()
           self.dns.write_dns_files()

        if self.verbose:
           self.logger.info("rendering Rsync files")
        self.rsync_gen()

        if self.verbose:
           self.logger.info("generating PXE menu structure")
        self.pxegen.make_pxe_menu()

        # run post-triggers
        if self.verbose:
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
                if not x in ["aux", "web", "webui", "localmirror","repo_mirror","ks_mirror","images","links","repo_profile","repo_system","svc","rendered"] :
                    # delete directories that shouldn't exist
                    utils.rmtree(path,logger=self.logger)
                if x in ["kickstarts","kickstarts_sys","images","systems","distros","profiles","repo_profile","repo_system","rendered"]:
                    # clean out directory contents
                    utils.rmtree_contents(path,logger=self.logger)
        self.make_tftpboot()
        utils.rmtree_contents(self.pxelinux_dir,logger=self.logger)
        utils.rmtree_contents(self.images_dir,logger=self.logger)
        utils.rmtree_contents(self.s390_dir,logger=self.logger)
        utils.rmtree_contents(self.yaboot_bin_dir,logger=self.logger)
        utils.rmtree_contents(self.yaboot_cfg_dir,logger=self.logger)
        utils.rmtree_contents(self.rendered_dir,logger=self.logger)


    def rsync_gen(self):
        """
        Generate rsync modules of all repositories and distributions
        """
        template_file = "/etc/cobbler/rsync.template"

        try:
            template = open(template_file,"r")
        except:
            raise CX(_("error writing template to file: %s") % template_file)

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


