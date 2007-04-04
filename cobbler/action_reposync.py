"""
Builds out and synchronizes yum repo mirrors.
Initial support for rsync, perhaps reposync coming later.

Copyright 2006-2007, Red Hat, Inc
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

    def run(self,verbose=True):
        """
        Syncs the current repo configuration file with the filesystem.
        """

        self.verbose = verbose
        for repo in self.repos:
            print "considering: %s" % repo
            repo_path = os.path.join(self.settings.webdir, "repo_mirror", repo.name)
            mirror = repo.mirror
            if not os.path.isdir(repo_path):
                os.makedirs(repo_path)
            # if path contains http:// or ftp://, use with yum's reposync.
            # else do rsync
            if mirror.lower().find("http://") != -1 or mirror.lower().find("ftp://") != -1:
                self.do_reposync(repo)
            else:
                self.do_rsync(repo)

        return True
  
    def do_reposync(self,repo):

        """
        Handle copying of http:// and ftp:// repos.
        FIXME: support for mirrorlist?
        """

        if not repo.keep_updated:
            print "- %s is set to not be updated" % repo.name
            return True

        # create yum config file for use by reposync
        store_path = os.path.join(self.settings.webdir, "repo_mirror")
        dest_path = os.path.join(store_path, repo.name)
        temp_path = os.path.join(store_path, ".origin")
        if not os.path.isdir(temp_path):
            os.makedirs(temp_path)
        temp_file = self.create_local_file(repo, temp_path, output=False)
 
        cmd = "/usr/bin/reposync --config=%s --repoid=%s --tempcache --download_path=%s" % (temp_file, repo.name, store_path)
        print "- %s" % cmd
        rc = sub_process.call(cmd, shell=True)
        if rc !=0:
            raise cexceptions.CobblerException("cobbler reposync failed")
        arg = None
        os.path.walk(dest_path, self.createrepo_walker, arg)

        self.create_local_file(repo, dest_path)
 
    def do_rsync(self,repo):

        """
        Handle copying of rsync:// and rsync-over-ssh repos.
        """

        if not repo.keep_updated:
            print "- %s is set to not be updated" % repo.name
            return True
        dest_path = os.path.join(self.settings.webdir, "repo_mirror", repo.name)
        spacer = ""
        if not repo.mirror.startswith("rsync://") and not repo.mirror.startswith("/"):
            spacer = "-e ssh"
        if not repo.mirror.endswith("/"):
            repo.mirror = "%s/" % repo.mirror
        cmd = "rsync -av %s --delete --delete-excluded --exclude-from=/etc/cobbler/rsync.exclude %s %s" % (spacer, repo.mirror, dest_path)       
        print "- %s" % cmd
        rc = sub_process.call(cmd, shell=True)
        if rc !=0:
            raise cexceptions.CobblerException("cobbler reposync failed")
        arg = {}
        print "- walking: %s" % dest_path
        os.path.walk(dest_path, self.createrepo_walker, arg)
        self.create_local_file(repo, dest_path)

    def create_local_file(self, repo, dest_path, output=True):
        """
        Two uses:
        (A) Create local files that can be used with yum on provisioned clients to make use of thisi mirror.
        (B) Create a temporary file for yum to feed into reposync
        """

        if output:
            fname = os.path.join(dest_path,"config.repo")
        else:
            fname = os.path.join(dest_path, "%s.repo" % repo.name)
        print "- creating: %s" % fname
        config_file = open(fname, "w+")
        config_file.write("[%s]\n" % repo.name)
        config_file.write("name=%s\n" % repo.name)
        if output:
            config_file.write("baseurl=http://%s/cobbler/repo_mirror/%s\n" % (self.settings.server, repo.name))
        else:
            config_file.write("baseurl=%s\n" % repo.mirror)
        config_file.write("enabled=1\n")
        config_file.write("gpgcheck=0\n")
        config_file.close()
        return fname 

    def createrepo_walker(self, arg, dirname, fname):
        """
        Used to run createrepo on a copied mirror.
        """
        target_dir = os.path.dirname(dirname).split("/")[-1]
        print "- scanning: %s" % target_dir
        if target_dir.lower() in [ "i386", "x86_64", "ia64" ] or (arg is None):
            try:
                cmd = "createrepo %s" % dirname
                print cmd
                sub_process.call(cmd, shell=True)
            except:
                print "- createrepo failed.  Is it installed?"
            fnames = []  # we're in the right place                  
            
