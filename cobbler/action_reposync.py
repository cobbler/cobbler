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
from cexceptions import *
import traceback
import errno

from utils import _

class RepoSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    # ==================================================================================

    def __init__(self,config):
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
        self.rflags     = self.settings.yumreposync_flags

    # ===================================================================

    def run(self, name=None, verbose=True):
        """
        Syncs the current repo configuration file with the filesystem.
        """

        self.verbose = verbose
        for repo in self.repos:
            if name is not None and repo.name != name:
                # invoked to sync only a specific repo, this is not the one
                continue
            elif name is None and not repo.keep_updated:
                # invoked to run against all repos, but this one is off
                print _("- %s is set to not be updated") % repo.name
                continue

            repo_path = os.path.join(self.settings.webdir, "repo_mirror", repo.name)
            mirror = repo.mirror

            if not os.path.isdir(repo_path) and not repo.mirror.lower().startswith("rhn://"):
                os.makedirs(repo_path)
            
            if repo.is_rsync_mirror():
                self.do_rsync(repo)
            else:
                # which may actually NOT reposync if the repo is set to not mirror locally
                # but that's a technicality
                self.do_reposync(repo)
            self.update_permissions(repo_path)

        return True
    
    # ==================================================================
  
    def do_reposync(self,repo):

        """
        Handle copying of http:// and ftp:// repos.
        """

        # warn about not having yum-utils.  We don't want to require it in the package because
        # RHEL4 and RHEL5U0 don't have it.

        if not os.path.exists("/usr/bin/reposync"):
            raise CX(_("no /usr/bin/reposync found, please install yum-utils"))

        cmds = []                 # queues up commands to run
        is_rhn = False            # RHN repositories require extra black magic
        has_rpm_list = False      # flag indicating not to pull the whole repo

        # detect cases that require special handling

        if repo.mirror.lower().startswith("rhn://"):
            is_rhn = True
        if repo.rpm_list != "":
            has_rpm_list = True

        # create yum config file for use by reposync
        store_path = os.path.join(self.settings.webdir, "repo_mirror")
        dest_path = os.path.join(store_path, repo.name)
        temp_path = os.path.join(store_path, ".origin")
        if not os.path.isdir(temp_path) and repo.mirror_locally:
            # FIXME: there's a chance this might break the RHN D/L case
            os.makedirs(temp_path)
         
        # how we invoke yum-utils depends on whether this is RHN content or not.

       

        if not is_rhn:

            # this is the simple non-RHN case.
            # create the config file that yum will use for the copying

            if repo.mirror_locally:
                temp_file = self.create_local_file(repo, temp_path, output=False)

            if not has_rpm_list and repo.mirror_locally:
                # if we have not requested only certain RPMs, use reposync
                cmd = "/usr/bin/reposync %s --config=%s --repoid=%s --download_path=%s" % (self.rflags, temp_file, repo.name, store_path)
                if repo.arch != "":
                    if repo.arch == "x86":
                       repo.arch = "i386" # FIX potential arch errors
                    cmd = "%s -a %s" % (cmd, repo.arch)
                    
                print _("- %s") % cmd
                cmds.append(cmd)

            elif repo.mirror_locally:

                # create the output directory if it doesn't exist
                if not os.path.exists(dest_path):
                   os.makedirs(dest_path)

                use_source = ""
                if repo.arch == "src":
                    use_source = "--source"
 
                # older yumdownloader sometimes explodes on --resolvedeps
                # if this happens to you, upgrade yum & yum-utils
                extra_flags = self.settings.yumdownloader_flags
                cmd = "/usr/bin/yumdownloader %s %s -c %s --destdir=%s %s" % (extra_flags, use_source, temp_file, dest_path, " ".join(repo.rpm_list))
                print _("- %s") % cmd
                cmds.append(cmd)
        else:

            # this is the somewhat more-complex RHN case.
            # NOTE: this requires that you have entitlements for the server and you give the mirror as rhn://$channelname
            if not repo.mirror_locally:
                raise CX(_("rhn:// repos do not work with --mirror-locally=1"))

            if has_rpm_list:
                print _("- warning: --rpm-list is not supported for RHN content")
            rest = repo.mirror[6:] # everything after rhn://
            cmd = "/usr/bin/reposync %s -r %s --download_path=%s" % (self.rflags, rest, store_path)
            if repo.name != rest:
                args = { "name" : repo.name, "rest" : rest }
                raise CX(_("ERROR: repository %(name)s needs to be renamed %(rest)s as the name of the cobbler repository must match the name of the RHN channel") % args)

            if repo.arch != "":
                cmd = "%s -a %s" % (cmd, repo.arch)

            cmds.append(cmd)

        # now regardless of whether we're doing yumdownloader or reposync
        # or whether the repo was http://, ftp://, or rhn://, execute all queued
        # commands here.  Any failure at any point stops the operation.

        for cmd in cmds:
            if repo.mirror_locally:
                rc = sub_process.call(cmd, shell=True)
                if rc !=0:
                    raise CX(_("cobbler reposync failed"))

        # some more special case handling for RHN.
        # create the config file now, because the directory didn't exist earlier

        if is_rhn:
            temp_file = self.create_local_file(repo, temp_path, output=False)

        # now run createrepo to rebuild the index

        if repo.mirror_locally:
            os.path.walk(dest_path, self.createrepo_walker, repo)

        # create the config file the hosts will use to access the repository.

        self.create_local_file(repo, dest_path)
 

    # ==================================================================================

    def do_rsync(self,repo):

        """
        Handle copying of rsync:// and rsync-over-ssh repos.
        """

        if not repo.mirror_locally:
            raise CX(_("rsync:// urls must be mirrored locally, yum cannot access them directly"))

        if repo.rpm_list != "":
            print _("- warning: --rpm-list is not supported for rsync'd repositories")
        dest_path = os.path.join(self.settings.webdir, "repo_mirror", repo.name)
        spacer = ""
        if not repo.mirror.startswith("rsync://") and not repo.mirror.startswith("/"):
            spacer = "-e ssh"
        if not repo.mirror.endswith("/"):
            repo.mirror = "%s/" % repo.mirror
        cmd = "rsync -rltDv %s --delete --delete-excluded --exclude-from=/etc/cobbler/rsync.exclude %s %s" % (spacer, repo.mirror, dest_path)       
        print _("- %s") % cmd
        rc = sub_process.call(cmd, shell=True)
        if rc !=0:
            raise CX(_("cobbler reposync failed"))
        print _("- walking: %s") % dest_path
        os.path.walk(dest_path, self.createrepo_walker, repo)
        self.create_local_file(repo, dest_path)
    
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

    def createrepo_walker(self, repo, dirname, fnames):
        """
        Used to run createrepo on a copied mirror.
        """
        if os.path.exists(dirname) or repo.is_rsync_mirror():
            utils.remove_yum_olddata(dirname)
            try:
                cmd = "createrepo %s %s" % (repo.createrepo_flags, dirname)
                print _("- %s") % cmd
                sub_process.call(cmd, shell=True)
            except:
                print _("- createrepo failed.  Is it installed?")
            del fnames[:] # we're in the right place

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


            
