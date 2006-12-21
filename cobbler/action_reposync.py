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
            repo_path = os.path.join(self.settings.webdir, "repo_mirror", repo.name)
            mirror = repo.mirror
            if not os.path.isdir(repo_path):
                try:
                    os.makedirs(repo_path)
                except OSError, oe:
                    if not oe.errno == 17: # already exists, constant for this?
                        raise cexceptions.CobblerException("no_create", repo_path)
            self.do_rsync_repo(repo)

        return True
   
    def do_rsync_repo(self,repo):
        if not repo.keep_updated:
            print "- %s is set to not be updated"
            return True
        dest_path = os.path.join(self.settings.webdir, "repo_mirror", repo.name)
        spacer = ""
        if repo.mirror.find("rsync://") != -1:
            spacer = "-e ssh"
        if not repo.mirror.endswith("/"):
            repo.mirror = "%s/" % repo.mirror
        cmd = "rsync -av %s --delete --delete-excluded --exclude-from=/etc/cobbler/rsync.exclude %s %s" % (spacer, repo.mirror, dest_path)       
        print "executing: %s" % cmd
        rc = sub_process.call(cmd, shell=True)
        arg = {}
        print "- walking: %s" % dest_path
        os.path.walk(dest_path, self.createrepo_walker, arg)
        if repo.local_filename is not None and repo.local_filename != "":
            # this is a rather primative configuration in terms of yum options, but allows
            # for repos that were added with a value for --local-filename to provision a system
            # using a kickstart that will write the yum config for that repo (named whatever
            # was used for local_filename) in /etc/yum.repos.d ... see code in action_sync.py
            # that relies on this and for more info about how this is added to %post kickstart
            # templating.
            config_file = open(os.path.join(dest_path,"config.repo"),"w+")
            config_file.write("[%s]\n" % repo.local_filename)
            config_file.write("baseurl=http://%s/cobbler/repo_mirror/%s\n" % (self.settings.server, repo.name))
            config_file.write("enabled=1\n")
            config_file.write("gpgcheck=0\n")
            config_file.close()
        

    def createrepo_walker(self, arg, dirname, fname):
        target_dir = os.path.dirname(dirname).split("/")[-1]
        print "- scanning: %s" % target_dir
        if target_dir.lower() in [ "i386", "x86_64", "ia64" ]:
            try:
                cmd = "createrepo %s" % dirname
                print cmd
                sub_process.call(cmd, shell=True)
            except:
                print "- createrepo failed.  Is it installed?"
            fnames = []  # we're in the right place                  
            
