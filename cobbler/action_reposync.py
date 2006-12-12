"""
Builds out and synchronizes yum repo mirrors.
Initial support for rsync, perhaps reposync coming later.

Copyright 2006, Red Hat, Inc
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
import yaml # Howell-Clark version
import sub_process
import sys

import utils
import cobbler_msg
import cexceptions
import traceback
import errno



class RepoSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self,config):
        """
        Constructor
        """
        self.verbose  = True
        self.config   = config
        self.distros  = config.distros()
        self.profiles = config.profiles()
        self.systems  = config.systems()
        self.settings = config.settings()
        self.repos    = config.repos()

    def run(self,dryrun=False,verbose=True):
        """
        Syncs the current repo configuration file with the filesystem.
        """

        self.verbose = verbose
        self.dryrun = dryrun
        for repo in self.repos:
            print "considering: %s" % repo
            repo_path = os.path.join(repo.root, repo.name)
            mirror = repo.mirror
            if not os.path.isdir(repo_path):
                try:
                    os.makedirs(repo_path)
                except OSError, oe:
                    if not oe.errno == 17: # already exists, constant for this?
                        raise cexceptions.CobblerException("no_create", repo_path)
            if mirror.startswith("rsync://") or mirror.startswith("ssh://"):
                self.do_rsync_repo(repo)
            else:
                raise cexceptions.CobblerException("no_mirror")

        return True
   
    def do_rsync_repo(self,repo):
        if not repo.keep_updated:
            print "- %s is set to not be updated"
            return True
        print "imagine an rsync happened here, and that it was amazing..."
        dest_path = os.path.join(self.settings.webdir, "repo_mirror", repo.name)
        spacer = ""
        if repo.mirror.find("ssh://") != -1:
            spacer = "-e ssh"
        cmd = "rsync -av %s --exclude=debug/ %s %s" % (spacer, repo.mirror, dest_path)       
        print "executing: %s" % cmd
        rc = sub_process.call(cmd, shell=True)

 
