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
import logging
import os
import os.path
import pipes
import stat
import shutil
from typing import Optional, Union

from cobbler import utils
from cobbler import download_manager
from cobbler.enums import RepoArchs, RepoBreeds, MirrorType
from cobbler.utils import os_release
from cobbler.cexceptions import CX

HAS_LIBREPO = False
try:
    import librepo
    HAS_LIBREPO = True
except ModuleNotFoundError:
    pass


def repo_walker(top, func, arg):
    """
    Directory tree walk with callback function.

    For each directory in the directory tree rooted at top (including top itself, but excluding '.' and '..'), call
    func(arg, dirname, fnames). dirname is the name of the directory, and fnames a list of the names of the files and
    subdirectories in dirname (excluding '.' and '..').  func may modify the fnames list in-place (e.g. via del or slice
    assignment), and walk will only recurse into the subdirectories whose names remain in fnames; this can be used to
    implement a filter, or to impose a specific order of visiting.  No semantics are defined for, or required of, arg,
    beyond that arg is always passed to func. It can be used, e.g., to pass a filename pattern, or a mutable object
    designed to accumulate statistics. Passing None for arg is common.

    :param top: The directory that should be taken as root. The root dir will also be included in the processing.
    :param func: The function that should be executed.
    :param arg: The arguments for that function.
    """
    try:
        names = os.listdir(top)
    except os.error:
        return
    func(arg, top, names)
    for name in names:
        name = os.path.join(top, name)
        try:
            st = os.lstat(name)
        except os.error:
            continue
        if stat.S_ISDIR(st.st_mode):
            repo_walker(name, func, arg)


class RepoSync:
    """
    Handles conversion of internal state to the tftpboot tree layout.
    """

    # ==================================================================================

    def __init__(self, api, tries: int = 1, nofail: bool = False):
        """
        Constructor

        :param api: The object which holds all information in Cobbler.
        :param tries: The number of tries before the operation fails.
        :param nofail: This sets the strictness of the reposync result handling.
        """
        self.verbose = True
        self.api = api
        self.settings = api.settings()
        self.repos = api.repos()
        self.rflags = self.settings.reposync_flags
        self.tries = tries
        self.nofail = nofail
        self.logger = logging.getLogger()
        self.dlmgr = download_manager.DownloadManager(self.api)

        self.logger.info("hello, reposync")

    # ===================================================================

    def run(self, name: Optional[str] = None, verbose: bool = True):
        """
        Syncs the current repo configuration file with the filesystem.

        :param name: The name of the repository to synchronize.
        :param verbose: If the action should be logged verbose or not.
        """

        self.logger.info("run, reposync, run!")

        self.verbose = verbose
        report_failure = False
        for repo in self.repos:
            if name is not None and repo.name != name:
                # Invoked to sync only a specific repo, this is not the one
                continue
            elif name is None and not repo.keep_updated:
                # Invoked to run against all repos, but this one is off
                self.logger.info("%s is set to not be updated" % repo.name)
                continue

            repo_mirror = os.path.join(self.settings.webdir, "repo_mirror")
            repo_path = os.path.join(repo_mirror, repo.name)

            if not os.path.isdir(repo_path) and not repo.mirror.lower().startswith("rhn://"):
                os.makedirs(repo_path)

            # Set the environment keys specified for this repo and save the old one if they modify an existing variable.

            env = repo.environment
            old_env = {}

            for k in list(env.keys()):
                self.logger.debug("setting repo environment: %s=%s" % (k, env[k]))
                if env[k] is not None:
                    if os.getenv(k):
                        old_env[k] = os.getenv(k)
                    else:
                        os.environ[k] = env[k]

            # Which may actually NOT reposync if the repo is set to not mirror locally but that's a technicality.

            for x in range(self.tries + 1, 1, -1):
                success = False
                try:
                    self.sync(repo)
                    success = True
                    break
                except:
                    utils.log_exc()
                    self.logger.warning("reposync failed, tries left: %s" % (x - 2))

            # Cleanup/restore any environment variables that were added or changed above.

            for k in list(env.keys()):
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
                    raise CX("reposync failed, retry limit reached, aborting")
                else:
                    self.logger.error("reposync failed, retry limit reached, skipping")

            self.update_permissions(repo_path)

        if report_failure:
            raise CX("overall reposync failed, at least one repo failed to synchronize")

    # ==================================================================================

    def sync(self, repo):

        """
        Conditionally sync a repo, based on type.

        :param repo: The repo to sync.
        """

        if repo.breed == RepoBreeds.RHN:
            self.rhn_sync(repo)
        elif repo.breed == RepoBreeds.YUM:
            self.yum_sync(repo)
        elif repo.breed == RepoBreeds.APT:
            self.apt_sync(repo)
        elif repo.breed == RepoBreeds.RSYNC:
            self.rsync_sync(repo)
        elif repo.breed == RepoBreeds.WGET:
            self.wget_sync(repo)
        else:
            raise CX("unable to sync repo (%s), unknown or unsupported repo type (%s)" % (repo.name, repo.breed.value))

    # ====================================================================================

    def librepo_getinfo(self, dirname: str) -> dict:

        """
        Used to get records from a repomd.xml file of downloaded rpmmd repository.

        :param dirname: The local path of rpmmd repository.
        :return: The dict representing records from a repomd.xml file of rpmmd repository.
        """

        h = librepo.Handle()
        r = librepo.Result()
        h.setopt(librepo.LRO_REPOTYPE, librepo.LR_YUMREPO)
        h.setopt(librepo.LRO_URLS, [dirname])
        h.setopt(librepo.LRO_LOCAL, True)
        h.setopt(librepo.LRO_CHECKSUM, True)
        h.setopt(librepo.LRO_IGNOREMISSING, True)

        try:
            h.perform(r)
        except librepo.LibrepoException as e:
            raise CX("librepo error: " + dirname + " - " + e.args[1]) from e

        rmd = r.getinfo(librepo.LRR_RPMMD_REPOMD)['records']
        return rmd

    # ====================================================================================

    def createrepo_walker(self, repo, dirname: str, fnames):
        """
        Used to run createrepo on a copied Yum mirror.

        :param repo: The repository object to run for.
        :param dirname: The directory to run in.
        :param fnames: Not known what this is for.
        """
        if os.path.exists(dirname) or repo.breed == RepoBreeds.RSYNC:
            utils.remove_yum_olddata(dirname)

            # add any repo metadata we can use
            mdoptions = []
            origin_path = os.path.join(dirname, ".origin")
            repodata_path = os.path.join(origin_path, "repodata")

            if os.path.isfile(os.path.join(repodata_path, "repomd.xml")):
                rd = self.librepo_getinfo(origin_path)

                if "group" in rd:
                    groupmdfile = rd['group']['location_href']
                    mdoptions.append("-g %s" % os.path.join(origin_path, groupmdfile))
                if "prestodelta" in rd:
                    # need createrepo >= 0.9.7 to add deltas
                    if utils.get_family() in ("redhat", "suse"):
                        cmd = "/usr/bin/rpmquery --queryformat=%{VERSION} createrepo"
                        createrepo_ver = utils.subprocess_get(cmd)
                        if not createrepo_ver[0:1].isdigit():
                            cmd = "/usr/bin/rpmquery --queryformat=%{VERSION} createrepo_c"
                            createrepo_ver = utils.subprocess_get(cmd)
                        if utils.compare_versions_gt(createrepo_ver, "0.9.7"):
                            mdoptions.append("--deltas")
                        else:
                            self.logger.error("this repo has presto metadata; you must upgrade createrepo to >= 0.9.7 "
                                              "first and then need to resync the repo through Cobbler.")

            blended = utils.blender(self.api, False, repo)
            flags = blended.get("createrepo_flags", "(ERROR: FLAGS)")
            try:
                cmd = "createrepo %s %s %s" % (" ".join(mdoptions), flags, pipes.quote(dirname))
                utils.subprocess_call(cmd)
            except:
                utils.log_exc()
                self.logger.error("createrepo failed.")
            del fnames[:]  # we're in the right place

    # ====================================================================================

    def wget_sync(self, repo):

        """
        Handle mirroring of directories using wget

        :param repo: The repo object to sync via wget.
        """

        mirror_program = "/usr/bin/wget"
        if not os.path.exists(mirror_program):
            raise CX("no %s found, please install it" % mirror_program)

        if repo.mirror_type != MirrorType.BASEURL:
            raise CX("mirrorlist and metalink mirror types is not supported for wget'd repositories")

        if repo.rpm_list != "" and repo.rpm_list != []:
            self.logger.warning("--rpm-list is not supported for wget'd repositories")

        dest_path = os.path.join(self.settings.webdir, "repo_mirror", repo.name)

        # FIXME: wrapper for subprocess that logs to logger
        cmd = ["wget", "-N", "-np", "-r", "-l", "inf", "-nd", "-P", pipes.quote(dest_path), pipes.quote(repo.mirror)]
        rc = utils.subprocess_call(cmd)

        if rc != 0:
            raise CX("cobbler reposync failed")
        repo_walker(dest_path, self.createrepo_walker, repo)
        self.create_local_file(dest_path, repo)

    # ====================================================================================

    def rsync_sync(self, repo):

        """
        Handle copying of rsync:// and rsync-over-ssh repos.

        :param repo: The repo to sync via rsync.
        """

        if not repo.mirror_locally:
            raise CX("rsync:// urls must be mirrored locally, yum cannot access them directly")

        if repo.mirror_type != MirrorType.BASEURL:
            raise CX("mirrorlist and metalink mirror types is not supported for rsync'd repositories")

        if repo.rpm_list != "" and repo.rpm_list != []:
            self.logger.warning("--rpm-list is not supported for rsync'd repositories")

        dest_path = os.path.join(self.settings.webdir, "repo_mirror", repo.name)

        spacer = ""
        if not repo.mirror.startswith("rsync://") and not repo.mirror.startswith("/"):
            spacer = "-e ssh"
        if not repo.mirror.endswith("/"):
            repo.mirror = "%s/" % repo.mirror

        flags = ''
        for x in repo.rsyncopts:
            if repo.rsyncopts[x]:
                flags += " %s %s" % (x, repo.rsyncopts[x])
            else:
                flags += " %s" % x

        if flags == '':
            flags = self.settings.reposync_rsync_flags

        cmd = "rsync %s --delete-after %s --delete --exclude-from=/etc/cobbler/rsync.exclude %s %s" \
              % (flags, spacer, pipes.quote(repo.mirror), pipes.quote(dest_path))
        rc = utils.subprocess_call(cmd)

        if rc != 0:
            raise CX("cobbler reposync failed")

        # If ran in archive mode then repo should already contain all repodata and does not need createrepo run
        archive = False
        if '--archive' in flags:
            archive = True
        else:
            # split flags and skip all --{options} as we need to look for combined flags like -vaH
            fl = flags.split()
            for f in fl:
                if f.startswith('--'):
                    pass
                else:
                    if 'a' in f:
                        archive = True
                        break
        if not archive:
            repo_walker(dest_path, self.createrepo_walker, repo)

        self.create_local_file(dest_path, repo)

    # ====================================================================================

    def reposync_cmd(self) -> str:

        """
        Determine reposync command

        :return: The path to the reposync command. If dnf exists it is used instead of reposync.
        """

        if not HAS_LIBREPO:
            raise CX("no librepo found, please install python3-librepo")

        if os.path.exists("/usr/bin/dnf"):
            cmd = "/usr/bin/dnf reposync"
        elif os.path.exists("/usr/bin/reposync"):
            cmd = "/usr/bin/reposync"
        else:
            # Warn about not having yum-utils.  We don't want to require it in the package because Fedora 22+ has moved
            # to dnf.
            raise CX("no /usr/bin/reposync found, please install yum-utils")
        return cmd

    # ====================================================================================

    def rhn_sync(self, repo):

        """
        Handle mirroring of RHN repos.

        :param repo: The repo object to synchronize.
        """

        # reposync command
        cmd = self.reposync_cmd()

        # flag indicating not to pull the whole repo
        has_rpm_list = False

        # detect cases that require special handling
        if repo.rpm_list != "" and repo.rpm_list != []:
            has_rpm_list = True

        # Create yum config file for use by reposync
        # FIXME: don't hardcode
        repos_path = os.path.join(self.settings.webdir, "repo_mirror")
        dest_path = os.path.join(repos_path, repo.name)
        temp_path = os.path.join(dest_path, ".origin")

        if not os.path.isdir(temp_path):
            # FIXME: there's a chance this might break the RHN D/L case
            os.makedirs(temp_path)

        # how we invoke reposync depends on whether this is RHN content or not.

        # This is the somewhat more-complex RHN case.
        # NOTE: this requires that you have entitlements for the server and you give the mirror as rhn://$channelname
        if not repo.mirror_locally:
            raise CX("rhn:// repos do not work with --mirror-locally=False")

        if has_rpm_list:
            self.logger.warning("warning: --rpm-list is not supported for RHN content")
        rest = repo.mirror[6:]  # everything after rhn://
        cmd = "%s %s --repo=%s -p %s" % (cmd,
                                         self.rflags,
                                         pipes.quote(rest),
                                         pipes.quote(repos_path))
        if repo.name != rest:
            args = {"name": repo.name, "rest": rest}
            raise CX("ERROR: repository %(name)s needs to be renamed %(rest)s as the name of the cobbler repository "
                     "must match the name of the RHN channel" % args)

        arch = repo.arch.value

        if arch == "i386":
            # Counter-intuitive, but we want the newish kernels too
            arch = "i686"

        if arch != "none":
            cmd = "%s -a %s" % (cmd, arch)

        # Now regardless of whether we're doing yumdownloader or reposync or whether the repo was http://, ftp://, or
        # rhn://, execute all queued commands here. Any failure at any point stops the operation.

        if repo.mirror_locally:
            utils.subprocess_call(cmd)

        # Some more special case handling for RHN. Create the config file now, because the directory didn't exist
        # earlier.

        self.create_local_file(temp_path, repo, output=False)

        # Now run createrepo to rebuild the index

        if repo.mirror_locally:
            repo_walker(dest_path, self.createrepo_walker, repo)

        # Create the config file the hosts will use to access the repository.

        self.create_local_file(dest_path, repo)

    # ====================================================================================

    def gen_urlgrab_ssl_opts(self, yumopts) -> Union[str, bool]:
        """
        This function translates yum repository options into the appropriate options for python-requests

        :param yumopts: The options to convert.
        :return: A tuple with the cert and a boolean if it should be verified or not.
        """
        # use SSL options if specified in yum opts
        cert = None
        sslcacert = None
        verify = False
        if 'sslcacert' in yumopts:
            sslcacert = yumopts['sslcacert']
        if 'sslclientkey' and 'sslclientcert' in yumopts:
            cert = (sslcacert, yumopts['sslclientcert'], yumopts['sslclientkey'])
        # Note that the default of requests is to verify the peer and host but the default here is NOT to verify them
        # unless sslverify is explicitly set to 1 in yumopts.
        if 'sslverify' in yumopts:
            if yumopts['sslverify'] == 1:
                verify = True
            else:
                verify = False

        return (cert, verify)

    # ====================================================================================

    def yum_sync(self, repo):

        """
        Handle copying of http:// and ftp:// yum repos.

        :param repo: The yum reporitory to sync.
        """

        # create the config file the hosts will use to access the repository.
        repos_path = os.path.join(self.settings.webdir, "repo_mirror")
        dest_path = os.path.join(repos_path, repo.name)
        self.create_local_file(dest_path, repo)

        if not repo.mirror_locally:
            return

        # command to run
        cmd = self.reposync_cmd()
        # flag indicating not to pull the whole repo
        has_rpm_list = False

        # detect cases that require special handling
        if repo.rpm_list != "" and repo.rpm_list != []:
            has_rpm_list = True

        # create yum config file for use by reposync
        temp_path = os.path.join(dest_path, ".origin")

        if not os.path.isdir(temp_path):
            # FIXME: there's a chance this might break the RHN D/L case
            os.makedirs(temp_path)

        temp_file = self.create_local_file(temp_path, repo, output=False)

        arch = repo.arch.value
        if arch == "i386":
            # Counter-intuitive, but we want the newish kernels too
            arch = "i686"

        if not has_rpm_list:
            # If we have not requested only certain RPMs, use reposync
            cmd = "%s %s --config=%s --repoid=%s -p %s" \
                  % (cmd, self.rflags, temp_file, pipes.quote(repo.name),
                     pipes.quote(repos_path))
            if arch != "none":
                cmd = "%s -a %s" % (cmd, arch)

        else:
            # Create the output directory if it doesn't exist
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)

            use_source = ""
            if arch == "src":
                use_source = "--source"

            # Older yumdownloader sometimes explodes on --resolvedeps if this happens to you, upgrade yum & yum-utils
            extra_flags = self.settings.yumdownloader_flags
            cmd = "/usr/bin/dnf download"
            cmd = "%s %s %s --disablerepo=* --enablerepo=%s -c %s --destdir=%s %s" \
                  % (cmd, extra_flags, use_source, pipes.quote(repo.name), temp_file, pipes.quote(dest_path),
                     " ".join(repo.rpm_list))

        # Now regardless of whether we're doing yumdownloader or reposync or whether the repo was http://, ftp://, or
        # rhn://, execute all queued commands here.  Any failure at any point stops the operation.

        rc = utils.subprocess_call(cmd)
        if rc != 0:
            raise CX("cobbler reposync failed")

        # download any metadata we can use
        proxy = None
        if repo.proxy != '<<None>>' and repo.proxy != '':
            proxy = repo.proxy
        (cert, verify) = self.gen_urlgrab_ssl_opts(repo.yumopts)

        repodata_path = os.path.join(dest_path, "repodata")
        repomd_path = os.path.join(repodata_path, "repomd.xml")
        if os.path.exists(repodata_path) and not os.path.isfile(repomd_path):
            shutil.rmtree(repodata_path, ignore_errors=False, onerror=None)

        repodata_path = os.path.join(temp_path, "repodata")
        if os.path.exists(repodata_path):
            self.logger.info("Deleted old repo metadata for %s", repodata_path)
            shutil.rmtree(repodata_path, ignore_errors=False, onerror=None)

        h = librepo.Handle()
        r = librepo.Result()
        h.setopt(librepo.LRO_REPOTYPE, librepo.LR_YUMREPO)
        h.setopt(librepo.LRO_CHECKSUM, True)
        h.setopt(librepo.LRO_DESTDIR, temp_path)

        if repo.mirror_type == MirrorType.METALINK:
            h.setopt(librepo.LRO_METALINKURL, repo.mirror)
        elif repo.mirror_type == MirrorType.MIRRORLIST:
            h.setopt(librepo.LRO_MIRRORLISTURL, repo.mirror)
        elif repo.mirror_type == MirrorType.BASEURL:
            h.setopt(librepo.LRO_URLS, [repo.mirror])

        if verify:
            h.setopt(librepo.LRO_SSLVERIFYPEER, True)
            h.setopt(librepo.LRO_SSLVERIFYHOST, True)

        if cert:
            sslcacert, sslclientcert, sslclientkey = cert
            h.setopt(librepo.LRO_SSLCACERT, sslcacert)
            h.setopt(librepo.LRO_SSLCLIENTCERT, sslclientcert)
            h.setopt(librepo.LRO_SSLCLIENTKEY, sslclientkey)

        if proxy:
            h.setopt(librepo.LRO_PROXY, proxy)
            h.setopt(librepo.LRO_PROXYTYPE, librepo.PROXY_HTTP)

        try:
            h.perform(r)
        except librepo.LibrepoException as e:
            raise CX("librepo error: " + temp_path + " - " + e.args[1]) from e

        # now run createrepo to rebuild the index
        if repo.mirror_locally:
            repo_walker(dest_path, self.createrepo_walker, repo)

    # ====================================================================================

    def apt_sync(self, repo):
        """
        Handle copying of http:// and ftp:// debian repos.

        :param repo: The apt repository to sync.
        """

        # Warn about not having mirror program.
        mirror_program = "/usr/bin/debmirror"
        if not os.path.exists(mirror_program):
            raise CX("no %s found, please install it" % mirror_program)

        # detect cases that require special handling
        if repo.rpm_list != "" and repo.rpm_list != []:
            raise CX("has_rpm_list not yet supported on apt repos")

        if repo.arch == RepoArchs.NONE:
            raise CX("Architecture is required for apt repositories")

        if repo.mirror_type != MirrorType.BASEURL:
            raise CX("mirrorlist and metalink mirror types is not supported for apt repositories")

        # built destination path for the repo
        dest_path = os.path.join(self.settings.webdir, "repo_mirror", repo.name)

        if repo.mirror_locally:
            # NOTE: Dropping @@suite@@ replace as it is also dropped from "from manage_import_debian"_ubuntu.py due that
            # repo has no os_version attribute. If it is added again it will break the Web UI!
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

            mirror_data = "--method=%s --host=%s --root=%s --dist=%s --section=%s" \
                          % (pipes.quote(method), pipes.quote(host), pipes.quote(mirror), pipes.quote(dists),
                             pipes.quote(components))

            rflags = "--nocleanup"
            for x in repo.yumopts:
                if repo.yumopts[x]:
                    rflags += " %s=%s" % (x, repo.yumopts[x])
                else:
                    rflags += " %s" % x
            cmd = "%s %s %s %s" % (mirror_program, rflags, mirror_data, pipes.quote(dest_path))
            if repo.arch == RepoArchs.SRC:
                cmd = "%s --source" % cmd
            else:
                arch = repo.arch.value
                if arch == "x86_64":
                    arch = "amd64"  # FIX potential arch errors
                cmd = "%s --nosource -a %s" % (cmd, arch)

            # Set's an environment variable for subprocess, otherwise debmirror will fail as it needs this variable to
            # exist.
            # FIXME: might this break anything? So far it doesn't
            os.putenv("HOME", "/var/lib/cobbler")

            rc = utils.subprocess_call(cmd)
            if rc != 0:
                raise CX("cobbler reposync failed")

    def create_local_file(self, dest_path: str, repo, output: bool = True) -> str:
        """
        Creates Yum config files for use by reposync

        Two uses:
        (A) output=True, Create local files that can be used with yum on provisioned clients to make use of this mirror.
        (B) output=False, Create a temporary file for yum to feed into yum for mirroring

        :param dest_path: The destination path to create the file at.
        :param repo: The repository object to create a file for.
        :param output: See described above.
        :return: The name of the file which was written.
        """

        # The output case will generate repo configuration files which are usable for the installed systems. They need
        # to be made compatible with --server-override which means they are actually templates, which need to be
        # rendered by a Cobbler-sync on per profile/system basis.

        if output:
            fname = os.path.join(dest_path, "config.repo")
        else:
            fname = os.path.join(dest_path, "%s.repo" % repo.name)
        self.logger.debug("creating: %s" % fname)
        if not os.path.exists(dest_path):
            utils.mkdir(dest_path)
        config_file = open(fname, "w+")
        if not output:
            config_file.write("[main]\nreposdir=/dev/null\n")
        config_file.write("[%s]\n" % repo.name)
        config_file.write("name=%s\n" % repo.name)

        optenabled = False
        optgpgcheck = False
        if output:
            if repo.mirror_locally:
                line = "baseurl=http://${http_server}/cobbler/repo_mirror/%s\n" % repo.name
            else:
                mstr = repo.mirror
                if mstr.startswith("/"):
                    mstr = "file://%s" % mstr
                line = "%s=%s\n" % (repo.mirror_type.value, mstr)

            config_file.write(line)
            # User may have options specific to certain yum plugins add them to the file
            for x in repo.yumopts:
                if x == "enabled":
                    optenabled = True
                if x == "gpgcheck":
                    optgpgcheck = True
        else:
            mstr = repo.mirror
            if mstr.startswith("/"):
                mstr = "file://%s" % mstr
            line = repo.mirror_type.value + "=%s\n" % mstr
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
            if 'exclude' in list(repo.yumopts.keys()):
                self.logger.debug("excluding: %s" % repo.yumopts['exclude'])
                config_file.write("exclude=%s\n" % repo.yumopts['exclude'])

        if not optenabled:
            config_file.write("enabled=1\n")
        config_file.write("priority=%s\n" % repo.priority)
        # FIXME: potentially might want a way to turn this on/off on a per-repo basis
        if not optgpgcheck:
            config_file.write("gpgcheck=0\n")
        # user may have options specific to certain yum plugins
        # add them to the file
        for x in repo.yumopts:
            if not (output and repo.mirror_locally and x.startswith("ssl")):
                config_file.write("%s=%s\n" % (x, repo.yumopts[x]))
        config_file.close()
        return fname

    # ==================================================================================

    def update_permissions(self, repo_path):
        """
        Verifies that permissions and contexts after an rsync are as expected.
        Sending proper rsync flags should prevent the need for this, though this is largely a safeguard.

        :param repo_path: The path to update the permissions of.
        """
        # all_path = os.path.join(repo_path, "*")
        owner = "root:apache"

        (dist, _) = os_release()
        if dist == "suse":
            owner = "root:www"
        elif dist in ("debian", "ubuntu"):
            owner = "root:www-data"

        cmd1 = "chown -R " + owner + " %s" % repo_path

        utils.subprocess_call(cmd1)

        cmd2 = "chmod -R 755 %s" % repo_path
        utils.subprocess_call(cmd2)
