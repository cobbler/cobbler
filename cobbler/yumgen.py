"""
Builds out filesystem trees/data based on the object tree.
This is the code behind 'cobbler sync'.

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
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

    def retemplate_all_yum_repos(self):
        for p in self.profiles:
            self.retemplate_yum_repos(p,True)
        for system in self.systems:
            self.retemplate_yum_repos(system,False)

    def retemplate_yum_repos(self,obj,is_profile):
        """
        Yum repository management files are in self.settings.webdir/repo_mirror/$name/config.repo
        and also potentially in listed in the source_repos structure of the distro object, however
        these files have server URLs in them that must be templated out.  This function does this.
        """
        blended  = utils.blender(self.api, False, obj)

        if is_profile:
           outseg = "repos_profile"
        else:
           outseg = "repos_system"

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
            confdir = os.path.join(self.settings.webdir, outseg)
            outdir = os.path.join(confdir, blended["name"])
            utils.mkdir(outdir) 
            try:
                infile_h = open(infile)
            except:
                # file does not exist and the user needs to run reposync
                # before we will use this, cobbler check will mention
                # this problem
                continue
            infile_data = infile_h.read()
            infile_h.close()
            outfile = os.path.join(outdir, "%s.repo" % (dispname))
            self.templar.render(infile_data, blended, outfile, None)


