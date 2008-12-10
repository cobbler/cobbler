"""
Builds out filesystem trees/data based on the object tree.
This is the code behind 'cobbler sync'.

Copyright 2006-2008, Red Hat, Inc
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
import shutil
import time
import yaml # Howell-Clark version
import sub_process
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

from utils import _


class BootSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config,verbose=False,dhcp=None,dns=None):
        """
        Constructor
        """
        self.verbose     = verbose
        self.config      = config
        self.api         = config.api
        self.distros     = config.distros()
        self.profiles    = config.profiles()
        self.systems     = config.systems()
        self.settings    = config.settings()
        self.repos       = config.repos()
        self.templar     = templar.Templar(config)
        self.pxegen      = pxegen.PXEGen(config)
        self.dns         = dns
        self.dhcp        = dhcp
        self.bootloc     = utils.tftpboot_location()

    def run(self):
        """
        Syncs the current configuration file with the config tree.
        Using the Check().run_ functions previously is recommended
        """
        if not os.path.exists(self.bootloc):
            raise CX(_("cannot find directory: %s") % self.bootloc)

        # run pre-triggers...
        utils.run_triggers(None, "/var/lib/cobbler/triggers/sync/pre/*")

        # (paranoid) in case the pre-trigger modified any objects...
        self.api.deserialize()
        self.distros  = self.config.distros()
        self.profiles = self.config.profiles()
        self.systems  = self.config.systems()
        self.settings = self.config.settings()
        self.repos    = self.config.repos()
        self.pxegen   = pxegen.PXEGen(self.config)

        # execute the core of the sync operation
        self.clean_trees()
        self.pxegen.copy_bootloaders()
        self.pxegen.copy_distros()
        self.pxegen.copy_images()
        for x in self.systems:
            self.pxegen.write_all_system_files(x)
        if self.settings.manage_dhcp:
           self.dhcp.write_dhcp_file()
           self.dhcp.regen_ethers()
        if self.settings.manage_dns:
           self.dns.regen_hosts()
           self.dns.write_dns_files()
        self.pxegen.make_pxe_menu()

        # run post-triggers
        utils.run_triggers(None, "/var/lib/cobbler/triggers/sync/post/*")
        return True

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
                    utils.rmfile(path)
            if os.path.isdir(path):
                if not x in ["web", "webui", "localmirror","repo_mirror","ks_mirror","images","links","repo_profile","repo_system","svc","rendered"] :
                    # delete directories that shouldn't exist
                    utils.rmtree(path)
                if x in ["kickstarts","kickstarts_sys","images","systems","distros","profiles","repo_profile","repo_system","rendered"]:
                    # clean out directory contents
                    utils.rmtree_contents(path)
        pxelinux_dir = os.path.join(self.bootloc, "pxelinux.cfg")
        images_dir = os.path.join(self.bootloc, "images")
        yaboot_bin_dir = os.path.join(self.bootloc, "ppc")
        yaboot_cfg_dir = os.path.join(self.bootloc, "etc")
        s390_dir = os.path.join(self.bootloc, "s390x")
        rendered_dir = os.path.join(self.settings.webdir, "rendered")
        if not os.path.exists(pxelinux_dir):
            utils.mkdir(pxelinux_dir)
        if not os.path.exists(images_dir):
            utils.mkdir(images_dir)
        if not os.path.exists(rendered_dir):
            utils.mkdir(rendered_dir)
        if not os.path.exists(yaboot_bin_dir):
            utils.mkdir(yaboot_bin_dir)
        if not os.path.exists(yaboot_cfg_dir):
            utils.mkdir(yaboot_cfg_dir)
        utils.rmtree_contents(os.path.join(self.bootloc, "pxelinux.cfg"))
        utils.rmtree_contents(os.path.join(self.bootloc, "images"))
        utils.rmtree_contents(os.path.join(self.bootloc, "s390x"))
        utils.rmtree_contents(os.path.join(self.bootloc, "ppc"))
        utils.rmtree_contents(os.path.join(self.bootloc, "etc"))
        utils.rmtree_contents(rendered_dir)
        


