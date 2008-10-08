"""
Builds out and synchronizes yum repo mirrors.
Initial support for rsync, perhaps reposync coming later.

Copyright 2006-2007, Red Hat, Inc
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
import time
import yaml # Howell-Clark version
import sub_process
import sys

import utils
from cexceptions import *
import traceback
import errno

from utils import _

class RepoSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    # ==================================================================================

    def __init__(self,config,tries=1,nofail=False):
        """
        Constructor
        """
        self.verbose   = True
        self.config    = config
        self.distros   = config.distros()
        self.profiles  = config.profiles()
        self.systems   = config.systems()
        self.settings  = config.settings()
        self.repos     = config.repos()
        self.rflags    = self.settings.yumreposync_flags
        self.tries     = tries
        self.nofail    = nofail

    # ===================================================================

    def run(self, name=None, verbose=True):
        """
        Syncs the current repo configuration file with the filesystem.
        """
            
        try:
            self.tries = int(self.tries)
        except:
            raise CX(_("retry value must be an integer"))

        self.verbose = verbose

        report_failure = False
        for repo in self.repos:

            if name is not None and repo.name != name:
                # invoked to sync only a specific repo, this is not the one
                continue
            elif name is None and not repo.keep_updated:
                # invoked to run against all repos, but this one is off
                print _("- %s is set to not be updated") % repo.name
                continue

            repo_mirror = os.path.join(self.settings.webdir, "repo_mirror")
            repo_path = os.path.join(repo_mirror, repo.name)
            mirror = repo.mirror

            if not os.path.isdir(repo_path) and not repo.mirror.lower().startswith("rhn://"):
                os.makedirs(repo_path)
            
            # which may actually NOT reposync if the repo is set to not mirror locally
            # but that's a technicality

            for x in range(self.tries+1,1,-1):
                success = False
                try:
                    repo.sync(repo_mirror,self) 
                    success = True
                except:
                    traceback.print_exc()
                    print _("- reposync failed, tries left: %s") % (x-2)

            if not success:
                report_failure = True
                if not self.nofail:
                    raise CX(_("reposync failed, retry limit reached, aborting"))
                else:
                    print _("- reposync failed, retry limit reached, skipping")

            self.update_permissions(repo_path)

        if report_failure:
            raise CX(_("overall reposync failed, at least one repo failed to synchronize"))

        return True
    
    # ==================================================================================

    def create_local_file(self, repo, dest_path, output=True):
        """
        Two uses:
        (A) output=True, Create local files that can be used with yum on provisioned clients to make use of this mirror.
        (B) output=False, Create a temporary file for yum to feed into yum for mirroring
        """
    
        # the output case will generate repo configuration files which are usable
        # for the installed systems.  They need to be made compatible with --server-override
        # which means they are actually templates, which need to be rendered by a cobbler-sync
        # on per profile/system basis.

        if output:
            fname = os.path.join(dest_path,"config.repo")
        else:
            fname = os.path.join(dest_path, "%s.repo" % repo.name)
        print _("- creating: %s") % fname
        if not os.path.exists(dest_path):
            utils.mkdir(dest_path)
        config_file = open(fname, "w+")
        config_file.write("[%s]\n" % repo.name)
        config_file.write("name=%s\n" % repo.name)
        optenabled = False
        optgpgcheck = False
        if output:
            if repo.mirror_locally:
                line = "baseurl=http://${server}/cobbler/repo_mirror/%s\n" % (repo.name)
            else:
                line = "baseurl=%s\n" % (repo.mirror)
  
            config_file.write(line)
            # user may have options specific to certain yum plugins
            # add them to the file
            for x in repo.yumopts:
                config_file.write("%s=%s\n" % (x, repo.yumopts[x]))
                if x == "enabled":
                    optenabled = True
                if x == "gpgcheck":
                    optgpgcheck = True
        else:
            line = "baseurl=%s\n" % repo.mirror
            http_server = "%s:%s" % (self.settings.server, self.settings.http_port)
            line = line.replace("@@server@@",http_server)
            config_file.write(line)
        if not optenabled:
            config_file.write("enabled=1\n")
        config_file.write("priority=%s\n" % repo.priority)
        # FIXME: potentially might want a way to turn this on/off on a per-repo basis
        if not optgpgcheck:
            config_file.write("gpgcheck=0\n")
        config_file.close()
        return fname 

    # ==================================================================================

    def update_permissions(self, repo_path):
        """
        Verifies that permissions and contexts after an rsync are as expected.
        Sending proper rsync flags should prevent the need for this, though this is largely
        a safeguard.
        """
        # all_path = os.path.join(repo_path, "*")
        cmd1 = "chown -R root:apache %s" % repo_path
        sub_process.call(cmd1, shell=True)

        cmd2 = "chmod -R 755 %s" % repo_path
        sub_process.call(cmd2, shell=True)

        getenforce = "/usr/sbin/getenforce"
        if os.path.exists(getenforce):
            data = sub_process.Popen(getenforce, shell=True, stdout=sub_process.PIPE).communicate()[0]
            if data.lower().find("disabled") == -1:
                cmd3 = "chcon --reference /var/www %s >/dev/null 2>/dev/null" % repo_path
                sub_process.call(cmd3, shell=True)


            
