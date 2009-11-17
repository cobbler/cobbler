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
import sys
HAS_YUM = True
try:
    import yum
except:
    HAS_YUM = False

import utils
from cexceptions import *
import traceback
import errno
from utils import _
import clogger

class RepoSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    # ==================================================================================

    def __init__(self,config,tries=1,nofail=False,logger=None):
        """
        Constructor
        """
        self.verbose   = True
        self.api       = config.api
        self.config    = config
        self.distros   = config.distros()
        self.profiles  = config.profiles()
        self.systems   = config.systems()
        self.settings  = config.settings()
        self.repos     = config.repos()
        self.rflags    = self.settings.reposync_flags
        self.tries     = tries
        self.nofail    = nofail
        self.logger    = logger

        if logger is None:
           self.logger = clogger.Logger()

        self.logger.info("hello, reposync")


    # ===================================================================

    def run(self, name=None, verbose=True):
        """
        Syncs the current repo configuration file with the filesystem.
        """
            
        self.logger.info("run, reposync, run!")
        
        try:
            self.tries = int(self.tries)
        except:
            utils.die(self.logger,"retry value must be an integer")

        self.verbose = verbose

        report_failure = False
        for repo in self.repos:

            env = repo.environment

            for k in env.keys():
                self.logger.info("environment: %s=%s" % (k,env[k]))
                if env[k] is not None:
                    os.putenv(k,env[k])

            if name is not None and repo.name != name:
                # invoked to sync only a specific repo, this is not the one
                continue
            elif name is None and not repo.keep_updated:
                # invoked to run against all repos, but this one is off
                self.logger.info("%s is set to not be updated" % repo.name)
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
                    self.sync(repo) 
                    success = True
                except:
                    utils.log_exc(self.logger)
                    self.logger.warning("reposync failed, tries left: %s" % (x-2))

            if not success:
                report_failure = True
                if not self.nofail:
                    utils.die(self.logger,"reposync failed, retry limit reached, aborting")
                else:
                    self.logger.error("reposync failed, retry limit reached, skipping")

            self.update_permissions(repo_path)

        if report_failure:
            utils.die(self.logger,"overall reposync failed, at least one repo failed to synchronize")

        return True

    # ==================================================================================

    def sync(self, repo):
      
        """
        Conditionally sync a repo, based on type.
        """

        if repo.breed == "rhn":
            return self.rhn_sync(repo)
        elif repo.breed == "yum":
            return self.yum_sync(repo)
        #elif repo.breed == "apt":
        #    return self.apt_sync(repo)
        elif repo.breed == "rsync":
            return self.rsync_sync(repo)
        else:
            utils.die(self.logger,"unable to sync repo (%s), unknown or unsupported repo type (%s)" % (repo.name, repo.breed))

    # ====================================================================================

    def createrepo_walker(self, repo, dirname, fnames):
        """
        Used to run createrepo on a copied Yum mirror.
        """
        if os.path.exists(dirname) or repo['breed'] == 'rsync':
            utils.remove_yum_olddata(dirname)

            # add any repo metadata we can use
            mdoptions = []
            if os.path.isfile("%s/repodata/repomd.xml" % (dirname)):
                if not HAS_YUM:
                   utils.die(self.logger,"yum is required to use this feature")

                rmd = yum.repoMDObject.RepoMD('', "%s/repodata/repomd.xml" % (dirname))
                if rmd.repoData.has_key("group"):
                    groupmdfile = rmd.getData("group").location[1]
                    mdoptions.append("-g %s" % groupmdfile)
                if rmd.repoData.has_key("prestodelta"):
                    # need createrepo >= 0.9.7 to add deltas
                    if utils.check_dist() == "redhat" or utils.check_dist() == "suse":
                        cmd = "/usr/bin/rpmquery --queryformat=%{VERSION} createrepo"
                        createrepo_ver = utils.subprocess_get(self.logger, cmd)
                        if createrepo_ver >= "0.9.7":
                            mdoptions.append("--deltas")
                        else:
                            utils.die(self.logger,"this repo has presto metadata; you must upgrade createrepo to >= 0.9.7 first and then need to resync the repo through cobbler.")

            blended = utils.blender(self.api, False, repo)
            flags = blended.get("createrepo_flags","(ERROR: FLAGS)")
            try:
                # BOOKMARK
                cmd = "createrepo %s %s %s" % (" ".join(mdoptions), flags, dirname)
                utils.subprocess_call(self.logger, cmd)
            except:
                utils.log_exc(self.logger)
                self.logger.error("createrepo failed.")
            del fnames[:] # we're in the right place

    # ====================================================================================

    def rsync_sync(self, repo):

        """
        Handle copying of rsync:// and rsync-over-ssh repos.
        """

        repo_mirror = repo.mirror

        if not repo.mirror_locally:
            utils.die(self.logger,"rsync:// urls must be mirrored locally, yum cannot access them directly")

        if repo.rpm_list != "":
            self.logger.warning("--rpm-list is not supported for rsync'd repositories")

        # FIXME: don't hardcode
        dest_path = os.path.join("/var/www/cobbler/repo_mirror", repo.name)

        spacer = ""
        if not repo.mirror.startswith("rsync://") and not repo.mirror.startswith("/"):
            spacer = "-e ssh"
        if not repo.mirror.endswith("/"):
            repo.mirror = "%s/" % repo.mirror

        # FIXME: wrapper for subprocess that logs to logger
        cmd = "rsync -rltDv %s --delete --exclude-from=/etc/cobbler/rsync.exclude %s %s" % (spacer, repo.mirror, dest_path)
        rc = utils.subprocess_call(self.logger, cmd)

        if rc !=0:
            utils.die(self.logger,"cobbler reposync failed")
        os.path.walk(dest_path, self.createrepo_walker, repo)
        self.create_local_file(dest_path, repo)

    # ====================================================================================
    
    def rhn_sync(self, repo):

        """
        Handle mirroring of RHN repos.
        """

        repo_mirror = repo.mirror

        # FIXME? warn about not having yum-utils.  We don't want to require it in the package because
        # RHEL4 and RHEL5U0 don't have it.

        if not os.path.exists("/usr/bin/reposync"):
            utils.die(self.logger,"no /usr/bin/reposync found, please install yum-utils")

        cmd = ""                  # command to run
        has_rpm_list = False      # flag indicating not to pull the whole repo

        # detect cases that require special handling

        if repo.rpm_list != "":
            has_rpm_list = True

        # create yum config file for use by reposync
        # FIXME: don't hardcode
        dest_path = os.path.join("/var/www/cobbler/repo_mirror", repo.name)
        temp_path = os.path.join(dest_path, ".origin")

        if not os.path.isdir(temp_path) and repo.mirror_locally:
            # FIXME: there's a chance this might break the RHN D/L case
            os.makedirs(temp_path)
         
        # how we invoke yum-utils depends on whether this is RHN content or not.

       
        # this is the somewhat more-complex RHN case.
        # NOTE: this requires that you have entitlements for the server and you give the mirror as rhn://$channelname
        if not repo.mirror_locally:
            utils.die("rhn:// repos do not work with --mirror-locally=1")

        if has_rpm_list:
            self.logger.warning("warning: --rpm-list is not supported for RHN content")
        rest = repo.mirror[6:] # everything after rhn://
        cmd = "/usr/bin/reposync %s -r %s --download_path=%s" % (self.rflags, rest, "/var/www/cobbler/repo_mirror")
        if repo.name != rest:
            args = { "name" : repo.name, "rest" : rest }
            utils.die(self.logger,"ERROR: repository %(name)s needs to be renamed %(rest)s as the name of the cobbler repository must match the name of the RHN channel" % args)

        if repo.arch == "i386":
            # counter-intuitive, but we want the newish kernels too
            repo.arch = "i686"

        if repo.arch != "":
            cmd = "%s -a %s" % (cmd, repo.arch)

        # now regardless of whether we're doing yumdownloader or reposync
        # or whether the repo was http://, ftp://, or rhn://, execute all queued
        # commands here.  Any failure at any point stops the operation.

        if repo.mirror_locally:
            rc = utils.subprocess_call(self.logger, cmd)
            if rc !=0:
                utils.die(self.logger,"cobbler reposync failed")

        # some more special case handling for RHN.
        # create the config file now, because the directory didn't exist earlier

        temp_file = self.create_local_file(temp_path, repo, output=False)

        # now run createrepo to rebuild the index

        if repo.mirror_locally:
            os.path.walk(dest_path, self.createrepo_walker, repo)

        # create the config file the hosts will use to access the repository.

        self.create_local_file(dest_path, repo)

    # ====================================================================================

    def yum_sync(self, repo):

        """
        Handle copying of http:// and ftp:// yum repos.
        """

        repo_mirror = repo.mirror

        # warn about not having yum-utils.  We don't want to require it in the package because
        # RHEL4 and RHEL5U0 don't have it.

        if not os.path.exists("/usr/bin/reposync"):
            utils.die(self.logger,"no /usr/bin/reposync found, please install yum-utils")

        cmd = ""                  # command to run
        has_rpm_list = False      # flag indicating not to pull the whole repo

        # detect cases that require special handling

        if repo.rpm_list != "" and repo.rpm_list != []:
            has_rpm_list = True

        # create yum config file for use by reposync
        dest_path = os.path.join("/var/www/cobbler/repo_mirror", repo.name)
        temp_path = os.path.join(dest_path, ".origin")

        if not os.path.isdir(temp_path) and repo.mirror_locally:
            # FIXME: there's a chance this might break the RHN D/L case
            os.makedirs(temp_path)
         
        # create the config file that yum will use for the copying

        if repo.mirror_locally:
            temp_file = self.create_local_file(temp_path, repo, output=False)

        if not has_rpm_list and repo.mirror_locally:
            # if we have not requested only certain RPMs, use reposync
            cmd = "/usr/bin/reposync %s --config=%s --repoid=%s --download_path=%s" % (self.rflags, temp_file, repo.name, "/var/www/cobbler/repo_mirror")
            if repo.arch != "":
                if repo.arch == "x86":
                   repo.arch = "i386" # FIX potential arch errors
                if repo.arch == "i386":
                   # counter-intuitive, but we want the newish kernels too
                   cmd = "%s -a i686" % (cmd)
                else:
                   cmd = "%s -a %s" % (cmd, repo.arch)

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
            cmd = "/usr/bin/yumdownloader %s %s --disablerepo=* --enablerepo=%s -c %s --destdir=%s %s" % (extra_flags, use_source, repo.name, temp_file, dest_path, " ".join(repo.rpm_list))

        # now regardless of whether we're doing yumdownloader or reposync
        # or whether the repo was http://, ftp://, or rhn://, execute all queued
        # commands here.  Any failure at any point stops the operation.

        if repo.mirror_locally:
            rc = utils.subprocess_call(self.logger, cmd)
            if rc !=0:
                utils.die(self.logger,"cobbler reposync failed")

        repodata_path = os.path.join(dest_path, "repodata")

        if not os.path.exists("/usr/bin/wget"):
            utils.die(self.logger,"no /usr/bin/wget found, please install wget")

        # grab repomd.xml and use it to download any metadata we can use
        cmd2 = "/usr/bin/wget -q %s/repodata/repomd.xml -O /dev/null" % (repo_mirror)
        rc = utils.subprocess_call(self.logger,cmd2)
        if rc == 0:
            if not os.path.isdir(repodata_path):
                os.makedirs(repodata_path)
            cmd2 = "/usr/bin/wget -q %s/repodata/repomd.xml -O %s/repomd.xml" % (repo_mirror, repodata_path)
            rc = utils.subprocess_call(self.logger,cmd2)
            if rc !=0:
                utils.die(self.logger,"wget failed")
            rmd = yum.repoMDObject.RepoMD('', "%s/repomd.xml" % (repodata_path))
            for mdtype in rmd.repoData.keys():
                # don't download metadata files that are created by default
                if mdtype not in ["primary", "primary_db", "filelists", "filelists_db", "other", "other_db"]:
                    mdfile = rmd.getData(mdtype).location[1]
                    cmd3 = "/usr/bin/wget -q %s/%s -O %s/%s" % (repo_mirror, mdfile, dest_path, mdfile)
                    utils.subprocess_call(self.logger,cmd3)
                    if rc !=0:
                        utils.die(self.logger,"wget failed")

        # now run createrepo to rebuild the index
        # only needed if we didn't use yum's reposync already.

        if not has_rpm_list and repo.mirror_locally:
            os.path.walk(dest_path, self.createrepo_walker, repo)

        # create the config file the hosts will use to access the repository.

        self.create_local_file(dest_path, repo)

    # ====================================================================================
 

#    def apt_sync(self, repo):
#
#        """
#        Handle copying of http:// and ftp:// debian repos.
#        """
#
#        repo_mirror = repo.mirror
#
#        # warn about not having mirror program.
#
#        mirror_program = "/usr/bin/debmirror"
#        if not os.path.exists(mirror_program):
#            utils.die(self.logger,"no %s found, please install it"%(mirror_program))
#
#        cmd = ""                  # command to run
#        has_rpm_list = False      # flag indicating not to pull the whole repo
#
#        # detect cases that require special handling
#
#        if repo.rpm_list != "":
#            utils.die(self.logger,"has_rpm_list not yet supported on apt repos")
#
#        if not repo.arch:
#            utils.die(self.logger,"Architecture is required for apt repositories")
#
#        # built destination path for the repo
#        dest_path = os.path.join("/var/www/cobbler/repo_mirror", repo.name)
#         
#        if repo.mirror_locally:
#            mirror = repo.mirror.replace("@@suite@@",repo.os_version)
#
#            idx = mirror.find("://")
#            method = mirror[:idx]
#            mirror = mirror[idx+3:]
#
#            idx = mirror.find("/")
#            host = mirror[:idx]
#            mirror = mirror[idx+1:]
#
#            idx = mirror.rfind("/dists/")
#            suite = mirror[idx+7:]
#            mirror = mirror[:idx]
#
#            mirror_data = "--method=%s --host=%s --root=%s --dist=%s " % ( method , host , mirror , suite )
#
#            # FIXME : flags should come from repo instead of being hardcoded
#
#            rflags = "--passive --nocleanup"
#            for x in repo.yumopts:
#                if repo.yumopts[x]:
#                    rflags += " %s %s" % ( x , repo.yumopts[x] ) 
#                else:
#                    rflags += " %s" % x 
#            cmd = "%s %s %s %s" % (mirror_program, rflags, mirror_data, dest_path)
#            if repo.arch == "src":
#                cmd = "%s --source" % cmd
#            else:
#                arch = repo.arch
#                if arch == "x86":
#                   arch = "i386" # FIX potential arch errors
#                if arch == "x86_64":
#                   arch = "amd64" # FIX potential arch errors
#                cmd = "%s --nosource -a %s" % (cmd, arch)
#                    
#            rc = utils.subprocess_call(self.logger, cmd)
#            if rc !=0:
#                utils.die(self.logger,"cobbler reposync failed")
 

        
    # ==================================================================================

    def create_local_file(self, dest_path, repo, output=True):
        """

        Creates Yum config files for use by reposync

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
        self.logger.debug("creating: %s" % fname)
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
                mstr = repo.mirror
                if mstr.startswith("/"):
                    mstr = "file://%s" % mstr
                line = "baseurl=%s\n" % mstr
  
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
            mstr = repo.mirror
            if mstr.startswith("/"):
                mstr = "file://%s" % mstr
            line = "baseurl=%s\n" % mstr
            if self.settings.http_port not in (80, '80'):
                http_server = "%s:%s" % (self.settings.server, self.settings.http_port)
            else:
                http_server = self.settings.server
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
        utils.subprocess_call(self.logger, cmd1)

        cmd2 = "chmod -R 755 %s" % repo_path
        utils.subprocess_call(self.logger, cmd2)

        if self.config.api.is_selinux_enabled():
            cmd3 = "chcon --reference /var/www %s >/dev/null 2>/dev/null" % repo_path
            utils.subprocess_call(self.logger, cmd3)


            
