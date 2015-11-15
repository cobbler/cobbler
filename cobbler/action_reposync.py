"""
Builds out and synchronizes yum repo mirrors.
Initial support for rsync, perhaps reposync coming later.

Copyright 2006-2007, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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
import urlgrabber

HAS_YUM = True
try:
    import yum
except:
    HAS_YUM = False

import clogger
import utils


class RepoSync:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    # ==================================================================================

    def __init__(self, collection_mgr, tries=1, nofail=False, logger=None):
        """
        Constructor
        """
        self.verbose = True
        self.api = collection_mgr.api
        self.collection_mgr = collection_mgr
        self.distros = collection_mgr.distros()
        self.profiles = collection_mgr.profiles()
        self.systems = collection_mgr.systems()
        self.settings = collection_mgr.settings()
        self.repos = collection_mgr.repos()
        self.rflags = self.settings.reposync_flags
        self.tries = tries
        self.nofail = nofail
        self.logger = logger

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
            utils.die(self.logger, "retry value must be an integer")

        self.verbose = verbose

        report_failure = False
        for repo in self.repos:
            if name is not None and repo.name != name:
                # invoked to sync only a specific repo, this is not the one
                continue
            elif name is None and not repo.keep_updated:
                # invoked to run against all repos, but this one is off
                self.logger.info("%s is set to not be updated" % repo.name)
                continue

            repo_mirror = os.path.join(self.settings.webdir, "repo_mirror")
            repo_path = os.path.join(repo_mirror, repo.name)

            if not os.path.isdir(repo_path) and not repo.mirror.lower().startswith("rhn://"):
                os.makedirs(repo_path)

            # set the environment keys specified for this repo
            # save the old ones if they modify an existing variable

            env = repo.environment
            old_env = {}

            for k in env.keys():
                self.logger.debug("setting repo environment: %s=%s" % (k, env[k]))
                if env[k] is not None:
                    if os.getenv(k):
                        old_env[k] = os.getenv(k)
                    else:
                        os.environ[k] = env[k]

            # which may actually NOT reposync if the repo is set to not mirror locally
            # but that's a technicality

            for x in range(self.tries + 1, 1, -1):
                success = False
                try:
                    self.sync(repo)
                    success = True
                    break
                except:
                    utils.log_exc(self.logger)
                    self.logger.warning("reposync failed, tries left: %s" % (x - 2))

            # cleanup/restore any environment variables that were
            # added or changed above

            for k in env.keys():
                if env[k] is not None:
                    if k in old_env:
                        self.logger.debug("resetting repo environment: %s=%s" % (k, old_env[k]))
                        os.environ[k] = old_env[k]
                    else:
                        self.logger.debug("removing repo environment: %s=%s" % (k, env[k]))
                        del os.environ[k]

            if not success:
                report_failure = True
                if not self.nofail:
                    utils.die(self.logger, "reposync failed, retry limit reached, aborting")
                else:
                    self.logger.error("reposync failed, retry limit reached, skipping")

            self.update_permissions(repo_path)

        if report_failure:
            utils.die(self.logger, "overall reposync failed, at least one repo failed to synchronize")

    # ==================================================================================

    def sync(self, repo):

        """
        Conditionally sync a repo, based on type.
        """

        if repo.breed == "rhn":
            self.rhn_sync(repo)
        elif repo.breed == "yum":
            self.yum_sync(repo)
        elif repo.breed == "apt":
            self.apt_sync(repo)
        elif repo.breed == "rsync":
            self.rsync_sync(repo)
        elif repo.breed == "wget":
            self.wget_sync(repo)
        else:
            utils.die(self.logger, "unable to sync repo (%s), unknown or unsupported repo type (%s)" % (repo.name, repo.breed))

    # ====================================================================================

    def createrepo_walker(self, repo, dirname, fnames):
        """
        Used to run createrepo on a copied Yum mirror.
        """
        if os.path.exists(dirname) or repo['breed'] == 'rsync':
            utils.remove_yum_olddata(dirname)

            # add any repo metadata we can use
            mdoptions = []
            if os.path.isfile("%s/.origin/repomd.xml" % (dirname)):
                if not HAS_YUM:
                    utils.die(self.logger, "yum is required to use this feature")

                rmd = yum.repoMDObject.RepoMD('', "%s/.origin/repomd.xml" % (dirname))
                if "group" in rmd.repoData:
                    groupmdfile = rmd.getData("group").location[1]
                    mdoptions.append("-g %s" % groupmdfile)
                if "prestodelta" in rmd.repoData:
                    # need createrepo >= 0.9.7 to add deltas
                    if utils.get_family() in ("redhat", "suse"):
                        cmd = "/usr/bin/rpmquery --queryformat=%{VERSION} createrepo"
                        createrepo_ver = utils.subprocess_get(self.logger, cmd)
                        if utils.compare_versions_gt(createrepo_ver, "0.9.7"):
                            mdoptions.append("--deltas")
                        else:
                            self.logger.error("this repo has presto metadata; you must upgrade createrepo to >= 0.9.7 first and then need to resync the repo through cobbler.")

            blended = utils.blender(self.api, False, repo)
            flags = blended.get("createrepo_flags", "(ERROR: FLAGS)")
            try:
                # BOOKMARK
                cmd = "createrepo %s %s %s" % (" ".join(mdoptions), flags, dirname)
                utils.subprocess_call(self.logger, cmd)
            except:
                utils.log_exc(self.logger)
                self.logger.error("createrepo failed.")
            del fnames[:]           # we're in the right place

    # ====================================================================================

    def wget_sync(self, repo):

        """
        Handle mirroring of directories using wget
        """

        repo_mirror = repo.mirror

        if repo.rpm_list != "" and repo.rpm_list != []:
            self.logger.warning("--rpm-list is not supported for wget'd repositories")

        # FIXME: don't hardcode
        dest_path = os.path.join(self.settings.webdir + "/repo_mirror", repo.name)

        # FIXME: wrapper for subprocess that logs to logger
        cmd = "wget -N -np -r -l inf -nd -P %s %s" % (dest_path, repo_mirror)
        rc = utils.subprocess_call(self.logger, cmd)

        if rc != 0:
            utils.die(self.logger, "cobbler reposync failed")
        os.path.walk(dest_path, self.createrepo_walker, repo)
        self.create_local_file(dest_path, repo)

    # ====================================================================================

    def rsync_sync(self, repo):

        """
        Handle copying of rsync:// and rsync-over-ssh repos.
        """

        if not repo.mirror_locally:
            utils.die(self.logger, "rsync:// urls must be mirrored locally, yum cannot access them directly")

        if repo.rpm_list != "" and repo.rpm_list != []:
            self.logger.warning("--rpm-list is not supported for rsync'd repositories")

        # FIXME: don't hardcode
        dest_path = os.path.join(self.settings.webdir + "/repo_mirror", repo.name)

        spacer = ""
        if not repo.mirror.startswith("rsync://") and not repo.mirror.startswith("/"):
            spacer = "-e ssh"
        if not repo.mirror.endswith("/"):
            repo.mirror = "%s/" % repo.mirror

        # FIXME: wrapper for subprocess that logs to logger
        cmd = "rsync -rltDv --copy-unsafe-links --delete-after %s --delete --exclude-from=/etc/cobbler/rsync.exclude %s %s" % (spacer, repo.mirror, dest_path)
        rc = utils.subprocess_call(self.logger, cmd)

        if rc != 0:
            utils.die(self.logger, "cobbler reposync failed")
        os.path.walk(dest_path, self.createrepo_walker, repo)
        self.create_local_file(dest_path, repo)

    # ====================================================================================

    def reposync_cmd(self):

        """
        Determine reposync command
        """

        cmd = None                # reposync command
        if os.path.exists("/usr/bin/dnf"):
            cmd = "/usr/bin/dnf reposync"
        elif os.path.exists("/usr/bin/reposync"):
            cmd = "/usr/bin/reposync"
        else:
            # warn about not having yum-utils.  We don't want to require it in the package because
            # Fedora 22+ has moved to dnf.

            utils.die(self.logger, "no /usr/bin/reposync found, please install yum-utils")
        return cmd

    # ====================================================================================

    def rhn_sync(self, repo):

        """
        Handle mirroring of RHN repos.
        """

        cmd = self.reposync_cmd()  # reposync command

        has_rpm_list = False       # flag indicating not to pull the whole repo

        # detect cases that require special handling

        if repo.rpm_list != "" and repo.rpm_list != []:
            has_rpm_list = True

        # create yum config file for use by reposync
        # FIXME: don't hardcode
        dest_path = os.path.join(self.settings.webdir + "/repo_mirror", repo.name)
        temp_path = os.path.join(dest_path, ".origin")

        if not os.path.isdir(temp_path):
            # FIXME: there's a chance this might break the RHN D/L case
            os.makedirs(temp_path)

        # how we invoke reposync depends on whether this is RHN content or not.

        # this is the somewhat more-complex RHN case.
        # NOTE: this requires that you have entitlements for the server and you give the mirror as rhn://$channelname
        if not repo.mirror_locally:
            utils.die(self.logger, "rhn:// repos do not work with --mirror-locally=1")

        if has_rpm_list:
            self.logger.warning("warning: --rpm-list is not supported for RHN content")
        rest = repo.mirror[6:]      # everything after rhn://
        cmd = "%s %s --repo=%s --download_path=%s" % (cmd, self.rflags, rest, self.settings.webdir + "/repo_mirror")
        if repo.name != rest:
            args = {"name": repo.name, "rest": rest}
            utils.die(self.logger, "ERROR: repository %(name)s needs to be renamed %(rest)s as the name of the cobbler repository must match the name of the RHN channel" % args)

        if repo.arch == "i386":
            # counter-intuitive, but we want the newish kernels too
            repo.arch = "i686"

        if repo.arch != "":
            cmd = "%s -a %s" % (cmd, repo.arch)

        # now regardless of whether we're doing yumdownloader or reposync
        # or whether the repo was http://, ftp://, or rhn://, execute all queued
        # commands here.  Any failure at any point stops the operation.

        if repo.mirror_locally:
            utils.subprocess_call(self.logger, cmd)

        # some more special case handling for RHN.
        # create the config file now, because the directory didn't exist earlier

        self.create_local_file(temp_path, repo, output=False)

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

        # create the config file the hosts will use to access the repository.
        repo_mirror = repo.mirror
        dest_path = os.path.join(self.settings.webdir + "/repo_mirror", repo.name)
        self.create_local_file(dest_path, repo)

        if not repo.mirror_locally:
            return

        cmd = self.reposync_cmd()  # command to run
        has_rpm_list = False       # flag indicating not to pull the whole repo

        # detect cases that require special handling

        if repo.rpm_list != "" and repo.rpm_list != []:
            has_rpm_list = True

        # create yum config file for use by reposync
        temp_path = os.path.join(dest_path, ".origin")

        if not os.path.isdir(temp_path):
            # FIXME: there's a chance this might break the RHN D/L case
            os.makedirs(temp_path)

        temp_file = self.create_local_file(temp_path, repo, output=False)

        if not has_rpm_list:
            # if we have not requested only certain RPMs, use reposync
            cmd = "%s %s --config=%s --repoid=%s --download_path=%s" % (cmd, self.rflags, temp_file, repo.name, self.settings.webdir + "/repo_mirror")
            if repo.arch != "":
                if repo.arch == "x86":
                    repo.arch = "i386"      # FIX potential arch errors
                if repo.arch == "i386":
                    # counter-intuitive, but we want the newish kernels too
                    cmd = "%s -a i686" % (cmd)
                else:
                    cmd = "%s -a %s" % (cmd, repo.arch)

        else:

            # create the output directory if it doesn't exist
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)

            use_source = ""
            if repo.arch == "src":
                use_source = "--source"

            # older yumdownloader sometimes explodes on --resolvedeps
            # if this happens to you, upgrade yum & yum-utils
            extra_flags = self.settings.yumdownloader_flags
            cmd = ""
            if os.path.exists("/usr/bin/dnf"):
                cmd = "/usr/bin/dnf download"
            else:
                cmd = "/usr/bin/yumdownloader"
            cmd = "%s %s %s --disablerepo=* --enablerepo=%s -c %s --destdir=%s %s" % (cmd, extra_flags, use_source, repo.name, temp_file, dest_path, " ".join(repo.rpm_list))

        # now regardless of whether we're doing yumdownloader or reposync
        # or whether the repo was http://, ftp://, or rhn://, execute all queued
        # commands here.  Any failure at any point stops the operation.

        rc = utils.subprocess_call(self.logger, cmd)
        if rc != 0:
            utils.die(self.logger, "cobbler reposync failed")

        repodata_path = os.path.join(dest_path, "repodata")

        # grab repomd.xml and use it to download any metadata we can use
        proxies = {}
        if repo.proxy == '<<inherit>>':
            proxies['http'] = self.settings.proxy_url_ext
        elif repo.proxy != '<<None>>' and repo.proxy != '':
            proxies['http'] = repo.proxy
            proxies['https'] = repo.proxy

        src = repo_mirror + "/repodata/repomd.xml"
        dst = temp_path + "/repomd.xml"
        try:
            urlgrabber.grabber.urlgrab(src, filename=dst, proxies=proxies)
        except Exception as e:
            utils.die(self.logger, "failed to fetch " + src + " " + e.args)

        # create our repodata directory now, as any extra metadata we're
        # about to download probably lives there
        if not os.path.isdir(repodata_path):
            os.makedirs(repodata_path)
        rmd = yum.repoMDObject.RepoMD('', "%s/repomd.xml" % (temp_path))
        for mdtype in rmd.repoData.keys():
            # don't download metadata files that are created by default
            if mdtype not in ["primary", "primary_db", "filelists", "filelists_db", "other", "other_db"]:
                mdfile = rmd.getData(mdtype).location[1]
                src = repo_mirror + "/" + mdfile
                dst = dest_path + "/" + mdfile
                try:
                    urlgrabber.grabber.urlgrab(src, filename=dst, proxies=proxies)
                except Exception as e:
                    utils.die(self.logger, "failed to fetch " + src + " " + e.args)

        # now run createrepo to rebuild the index
        if repo.mirror_locally:
            os.path.walk(dest_path, self.createrepo_walker, repo)

    # ====================================================================================

    def apt_sync(self, repo):

        """
        Handle copying of http:// and ftp:// debian repos.
        """

        # warn about not having mirror program.

        mirror_program = "/usr/bin/debmirror"
        if not os.path.exists(mirror_program):
            utils.die(self.logger, "no %s found, please install it" % (mirror_program))

        cmd = ""                  # command to run

        # detect cases that require special handling

        if repo.rpm_list != "" and repo.rpm_list != []:
            utils.die(self.logger, "has_rpm_list not yet supported on apt repos")

        if not repo.arch:
            utils.die(self.logger, "Architecture is required for apt repositories")

        # built destination path for the repo
        dest_path = os.path.join("/var/www/cobbler/repo_mirror", repo.name)

        if repo.mirror_locally:
            # NOTE: Dropping @@suite@@ replace as it is also dropped from
            # from manage_import_debian_ubuntu.py due that repo has no os_version
            # attribute. If it is added again it will break the Web UI!
            # mirror = repo.mirror.replace("@@suite@@",repo.os_version)
            mirror = repo.mirror

            idx = mirror.find("://")
            method = mirror[:idx]
            mirror = mirror[idx + 3:]

            idx = mirror.find("/")
            host = mirror[:idx]
            mirror = mirror[idx:]

            dists = ",".join(repo.apt_dists)
            components = ",".join(repo.apt_components)

            mirror_data = "--method=%s --host=%s --root=%s --dist=%s --section=%s" % (method, host, mirror, dists, components)

            rflags = "--nocleanup"
            for x in repo.yumopts:
                if repo.yumopts[x]:
                    rflags += " %s %s" % (x, repo.yumopts[x])
                else:
                    rflags += " %s" % x
            cmd = "%s %s %s %s" % (mirror_program, rflags, mirror_data, dest_path)
            if repo.arch == "src":
                cmd = "%s --source" % cmd
            else:
                arch = repo.arch
                if arch == "x86":
                    arch = "i386"       # FIX potential arch errors
                if arch == "x86_64":
                    arch = "amd64"      # FIX potential arch errors
                cmd = "%s --nosource -a %s" % (cmd, arch)

            # Set's an environment variable for subprocess, otherwise debmirror will fail
            # as it needs this variable to exist.
            # FIXME: might this break anything? So far it doesn't
            os.putenv("HOME", "/var/lib/cobbler")

            rc = utils.subprocess_call(self.logger, cmd)
            if rc != 0:
                utils.die(self.logger, "cobbler reposync failed")

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
            fname = os.path.join(dest_path, "config.repo")
        else:
            fname = os.path.join(dest_path, "%s.repo" % repo.name)
        self.logger.debug("creating: %s" % fname)
        if not os.path.exists(dest_path):
            utils.mkdir(dest_path)
        config_file = open(fname, "w+")
        config_file.write("[%s]\n" % repo.name)
        config_file.write("name=%s\n" % repo.name)
        if 'exclude' in repo.yumopts.keys():
            self.logger.debug("excluding: %s" % repo.yumopts['exclude'])
        optenabled = False
        optgpgcheck = False
        if output:
            if repo.mirror_locally:
                line = "baseurl=http://${http_server}/cobbler/repo_mirror/%s\n" % (repo.name)
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
            line = line.replace("@@server@@", http_server)
            config_file.write(line)

            config_proxy = None
            if repo.proxy == '<<inherit>>':
                config_proxy = self.settings.proxy_url_ext
            elif repo.proxy != '' and repo.proxy != '<<None>>':
                config_proxy = repo.proxy

            if config_proxy is not None:
                config_file.write("proxy=%s\n" % config_proxy)

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
        owner = "root:apache"
        if os.path.exists("/etc/SuSE-release"):
            owner = "root:www"
        elif os.path.exists("/etc/debian_version"):
            owner = "root:www-data"

        cmd1 = "chown -R " + owner + " %s" % repo_path

        utils.subprocess_call(self.logger, cmd1)

        cmd2 = "chmod -R 755 %s" % repo_path
        utils.subprocess_call(self.logger, cmd2)
