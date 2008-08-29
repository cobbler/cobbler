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
import sub_process
import sys
import glob
import traceback
import errno

import utils
from cexceptions import *
import templar 

import item_distro
import item_profile
import item_repo
import item_system

from utils import _


class YumGen:

    def __init__(self,config):
        """
        Constructor
        """
        self.config      = config
        self.api         = config.api
        self.distros     = config.distros()
        self.profiles    = config.profiles()
        self.systems     = config.systems()
        self.settings    = config.settings()
        self.repos       = config.repos()
        self.templar     = templar.Templar(config)

    #def retemplate_all_yum_repos(self):
    #    for p in self.profiles:
    #        self.retemplate_yum_repos(p,True)
    #    for system in self.systems:
    #        self.retemplate_yum_repos(system,False)

    def get_yum_config(self,obj,is_profile):
        """
        Return one large yum repo config blob suitable for use by any target system that requests it.
        """

        totalbuf = ""

        blended  = utils.blender(self.api, False, obj)

        input_files = []

        # chance old versions from upgrade do not have a source_repos
        # workaround for user bug
        if not blended.has_key("source_repos"):
            blended["source_repos"] = []

        # tack on all the install source repos IF there is more than one.
        # this is basically to support things like RHEL5 split trees
        # if there is only one, then there is no need to do this.

        for r in blended["source_repos"]:
            filename = self.settings.webdir + "/" + "/".join(r[0].split("/")[4:])
            input_files.append(filename)

        for repo in blended["repos"]:
            input_files.append(os.path.join(self.settings.webdir, "repo_mirror", repo, "config.repo"))

        for infile in input_files:
            if infile.find("ks_mirror") == -1:
                dispname = infile.split("/")[-2]
            else:
                dispname = infile.split("/")[-1].replace(".repo","")
            try:
                infile_h = open(infile)
            except:
                # file does not exist and the user needs to run reposync
                # before we will use this, cobbler check will mention
                # this problem
                continue
            infile_data = infile_h.read()
            infile_h.close()
            outfile = None # disk output only
            totalbuf = totalbuf + self.templar.render(infile_data, blended, outfile, None)
            totalbuf = totalbuf + "\n\n"

        return totalbuf



