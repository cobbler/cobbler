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
        self.verbose      = verbose
        self.config       = config
        self.api          = config.api
        self.distros      = config.distros()
        self.profiles     = config.profiles()
        self.systems      = config.systems()
        self.settings     = config.settings()
        self.repos        = config.repos()
        self.templar      = templar.Templar(config)
        self.pxegen       = pxegen.PXEGen(config)
        self.dns          = dns
        self.dhcp         = dhcp
        self.bootloc      = utils.tftpboot_location()
        self.pxegen.verbose = verbose
        self.dns.verbose    = verbose
        self.dhcp.verbose   = verbose

    def run(self):
        """
        Syncs the current configuration file with the config tree.
        Using the Check().run_ functions previously is recommended
        """
        if not os.path.exists(self.bootloc):
            raise CX(_("cannot find directory: %s") % self.bootloc)

        if self.verbose:
            print "- running pre-sync triggers"

        # run pre-triggers...
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/sync/pre/*")

        self.distros  = self.config.distros()
        self.profiles = self.config.profiles()
        self.systems  = self.config.systems()
        self.settings = self.config.settings()
        self.repos    = self.config.repos()

        # execute the core of the sync operation

        if self.verbose:
           print "- cleaning trees"
        self.clean_trees()

        if self.verbose:
           print "- copying bootloaders"
        self.pxegen.copy_bootloaders()

        if self.verbose:
           print "- copying distros" 
        self.pxegen.copy_distros()

        if self.verbose:
           print "- copying images"
        self.pxegen.copy_images()
        self.pxegen.generate_windows_files()
        for x in self.systems:
            if self.verbose:
                print "- copying files for system: %s" % x.name
            self.pxegen.write_all_system_files(x)

        if self.settings.manage_dhcp:
           if self.verbose:
                print "- rendering DHCP files"
           self.dhcp.write_dhcp_file()
           self.dhcp.regen_ethers()
        if self.settings.manage_dns:
           if self.verbose:
                print "- rendering DNS files"
           self.dns.regen_hosts()
           self.dns.write_dns_files()

        if self.verbose:
           print "- generating PXE menu structure"
        self.pxegen.make_pxe_menu()

        # run post-triggers
        if self.verbose:
            print "- running post-sync triggers"

        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/sync/post/*")
        utils.run_triggers(self.api, None, "/var/lib/cobbler/triggers/change/*")

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
                    utils.rmfile(path,verbose=self.verbose)
            if os.path.isdir(path):
                if not x in ["aux", "web", "webui", "localmirror","repo_mirror","ks_mirror","images","links","repo_profile","repo_system","svc","rendered"] :
                    # delete directories that shouldn't exist
                    utils.rmtree(path,verbose=self.verbose)
                if x in ["kickstarts","kickstarts_sys","images","systems","distros","profiles","repo_profile","repo_system","rendered"]:
                    # clean out directory contents
                    utils.rmtree_contents(path,verbose=self.verbose)
        pxelinux_dir = os.path.join(self.bootloc, "pxelinux.cfg")
        images_dir = os.path.join(self.bootloc, "images")
        yaboot_bin_dir = os.path.join(self.bootloc, "ppc")
        yaboot_cfg_dir = os.path.join(self.bootloc, "etc")
        s390_dir = os.path.join(self.bootloc, "s390x")
        profiles_dir = os.path.join(self.bootloc, "profiles")
        systems_dir = os.path.join(self.bootloc, "systems")
        rendered_dir = os.path.join(self.settings.webdir, "rendered")
        if not os.path.exists(pxelinux_dir):
            utils.mkdir(pxelinux_dir,verbose=self.verbose)
        if not os.path.exists(images_dir):
            utils.mkdir(images_dir,verbose=self.verbose)
        if not os.path.exists(rendered_dir):
            utils.mkdir(rendered_dir,verbose=self.verbose)
        if not os.path.exists(yaboot_bin_dir):
            utils.mkdir(yaboot_bin_dir,verbose=self.verbose)
        if not os.path.exists(yaboot_cfg_dir):
            utils.mkdir(yaboot_cfg_dir,verbose=self.verbose)
        if not os.path.exists(profiles_dir):
            utils.mkdir(profiles_dir,verbose=self.verbose)
        if not os.path.exists(systems_dir):
            utils.mkdir(systems_dir,verbose=self.verbose)
        utils.rmtree_contents(os.path.join(self.bootloc, "pxelinux.cfg"),verbose=self.verbose)
        utils.rmtree_contents(os.path.join(self.bootloc, "images"),verbose=self.verbose)
        utils.rmtree_contents(os.path.join(self.bootloc, "s390x"),verbose=self.verbose)
        utils.rmtree_contents(os.path.join(self.bootloc, "ppc"),verbose=self.verbose)
        utils.rmtree_contents(os.path.join(self.bootloc, "etc"),verbose=self.verbose)
        utils.rmtree_contents(profiles_dir,verbose=self.verbose)
        utils.rmtree_contents(systems_dir,verbose=self.verbose)
        utils.rmtree_contents(rendered_dir,verbose=self.verbose)
        


