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

    # ==================================================================================

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
    
    # ==================================================================================

    def run(self,verbose=True):
        """
        Syncs the current repo configuration file with the filesystem.
        """

        self.verbose = verbose
        for repo in self.repos:
            repo_path = os.path.join(self.settings.webdir, "repo_mirror", repo.name)
            mirror = repo.mirror
            if not os.path.isdir(repo_path) and not repo.mirror.lower().startswith("rhn://"):
                os.makedirs(repo_path)
            # if path contains http:// or ftp://, use with yum's reposync.
            # else do rsync
            lower = mirror.lower()
            if lower.startswith("http://") or lower.startswith("ftp://") or lower.startswith("rhn://"):
                self.do_reposync(repo)
            else:
                self.do_rsync(repo)

        return True
    
    # ==================================================================================
  
    def do_reposync(self,repo):

        """
        Handle copying of http:// and ftp:// repos.
        FIXME: support for mirrorlist?
        """

        # warn about not having yum-utils.  We don't want to require it in the package because
        # RHEL4 and RHEL5U0 don't have it.

        if not os.path.exists("/usr/bin/reposync"):
            raise cexceptions.CobblerException("no /usr/bin/reposync found, please install yum-utils")

        cmds = []                 # queues up commands to run
        is_rhn = False            # RHN repositories require extra black magic
        has_rpm_list = False      # flag indicating not to pull the whole repo

        # detect cases that require special handling

        if repo.mirror.lower().startswith("rhn://"):
            is_rhn = True
        if repo.rpm_list != "":
            has_rpm_list = True

        # user might have disabled repo updates in the config file for whatever reason.
        # if so, don't update this one.

        if not repo.keep_updated:
            print "- %s is set to not be updated" % repo.name
            return True

        # create yum config file for use by reposync
        store_path = os.path.join(self.settings.webdir, "repo_mirror")
        dest_path = os.path.join(store_path, repo.name)
        temp_path = os.path.join(store_path, ".origin")
        if not os.path.isdir(temp_path) and not is_rhn:
            # if doing the rhn sync, reposync will make the directory
            # otherwise, we need to do it explicitly
            os.makedirs(temp_path)
         
        # how we invoke yum-utils depends on whether this is RHN content or not.

        if not is_rhn:

            # this is the simple non-RHN case.
            # create the config file that yum will use for the copying

            temp_file = self.create_local_file(repo, temp_path, output=False)

            if not has_rpm_list:

                # if we have not requested only certain RPMs, use reposync
                cmd = "/usr/bin/reposync --config=%s --repoid=%s --download_path=%s" % (temp_file, repo.name, store_path)
                print "- %s" % cmd
                cmds.append(cmd)

            else:

                # create the output directory if it doesn't exist
                if not os.path.exists(dest_path):
                   os.makedirs(dest_path)

                # if we only want certain RPMs, use yumdownloader (likely more than once)
                # FIXME: yumdownloader has a current bug where --resolve blows up
                # removing --resolve until I get the email from bugzilla saying it's fixed.
                cmd = "/usr/bin/yumdownloader -c %s --destdir=%s %s" %(temp_file, dest_path, " ".join(repo.rpm_list))
                print "- %s" % cmd
                cmds.append(cmd)
        else:

            # this is the somewhat more-complex RHN case.
            # NOTE: this requires that you have entitlements for the server and you give the mirror as rhn://$channelname

            if has_rpm_list:
                print "- warning: --rpm-list is not supported for RHN content"
            rest = repo.mirror[6:] # everything after rhn://
            cmd = "/usr/bin/reposync -r %s --download_path=%s" % (rest, store_path)
            print "- %s" % cmd
            cmds.append(cmd)

            # downloads using -r use the value given for -r as part of the output dir, 
            # so create a symlink with the name the user
            # gave such that everything still works as intended and the sync code still works
            # this doesn't happen for the http:// and ftp:// mirrors.

            if not os.path.exists(dest_path):
                from1 = os.path.join(self.settings.webdir, "repo_mirror", rest)
                print "- symlink: %s -> %s" % (from1, dest_path)
                os.symlink(from1, dest_path)
 
        # now regardless of whether we're doing yumdownloader or reposync
        # or whether the repo was http://, ftp://, or rhn://, execute all queued
        # commands here.  Any failure at any point stops the operation.

        for cmd in cmds:
            rc = sub_process.call(cmd, shell=True)
            if rc !=0:
                raise cexceptions.CobblerException("cobbler reposync failed")

        # some more special case handling for RHN.
        # create the config file now, because the directory didn't exist earlier

        if is_rhn:
            temp_file = self.create_local_file(repo, temp_path, output=False)

        # now run createrepo to rebuild the index

        arg = None
        os.path.walk(dest_path, self.createrepo_walker, arg)

        # create the config file the hosts will use to access the repository.

        self.create_local_file(repo, dest_path)
 

    # ==================================================================================

    def do_rsync(self,repo):

        """
        Handle copying of rsync:// and rsync-over-ssh repos.
        """

        if not repo.keep_updated:
            print "- %s is set to not be updated" % repo.name
            return True
        if repo.rpm_list != "":
            print "- warning: --rpm-list is not supported for rsync'd repositories"
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
    
    # ==================================================================================

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

    # ==================================================================================

    def createrepo_walker(self, arg, dirname, fname):
        """
        Used to run createrepo on a copied mirror.
        """
        target_dir = os.path.dirname(dirname).split("/")[-1]
        print "- scanning: %s" % target_dir
        if target_dir.lower() in [ "i386", "x86_64", "ia64" ] or (arg is None):
            utils.remove_yum_olddata(dirname)
            try:
                cmd = "createrepo %s" % dirname
                print cmd
                sub_process.call(cmd, shell=True)
            except:
                print "- createrepo failed.  Is it installed?"
            fnames = []  # we're in the right place                  
            
