"""
Copyright 2006-2009, Red Hat, Inc and Others
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

from ConfigParser import ConfigParser
import os
import random
import tempfile
import urlgrabber

from cobbler import action_acl
from cobbler import action_buildiso
from cobbler import action_check
from cobbler import action_dlcontent
from cobbler import action_hardlink
from cobbler import action_log
from cobbler import action_replicate
from cobbler import action_report
from cobbler import action_reposync
from cobbler import action_status
from cobbler import action_sync
from cobbler import autoinstall_manager
from cobbler import clogger
from cobbler import collection_manager
from cobbler import item_distro
from cobbler import item_file
from cobbler import item_image
from cobbler import item_mgmtclass
from cobbler import item_package
from cobbler import item_profile
from cobbler import item_repo
from cobbler import item_system
from cobbler import module_loader
from cobbler import power_manager
from cobbler import tftpgen
from cobbler import utils
from cobbler import yumgen
from cobbler.cexceptions import CX
from cobbler.utils import _


ERROR = 100
INFO = 10
DEBUG = 5

# FIXME: add --quiet depending on if not --verbose?
RSYNC_CMD = "rsync -a %s '%s' %s --progress"

# notes on locking:
# CobblerAPI is a singleton object
# the XMLRPC variants allow 1 simultaneous request
# therefore we flock on /etc/cobbler/settings for now
# on a request by request basis.


class CobblerAPI:
    """
    Python API module for Cobbler.
    See source for cobbler.py, or pydoc, for example usage.
    Cli apps and daemons should import api.py, and no other cobbler code.
    """
    __shared_state = {}
    __has_loaded = False

    def __init__(self, is_cobblerd=False):
        """
        Constructor
        """

        # FIXME: this should be switchable through some simple system

        self.__dict__ = CobblerAPI.__shared_state
        self.perms_ok = False
        if not CobblerAPI.__has_loaded:

            # NOTE: we do not log all API actions, because
            # a simple CLI invocation may call adds and such
            # to load the config, which would just fill up
            # the logs, so we'll do that logging at CLI
            # level (and remote.py web service level) instead.

            random.seed()
            self.is_cobblerd = is_cobblerd

            try:
                self.logger = clogger.Logger("/var/log/cobbler/cobbler.log")
            except CX:
                # return to CLI/other but perms are not valid
                # perms_ok is False
                return

            # FIXME: conslidate into 1 server instance

            self.selinux_enabled = utils.is_selinux_enabled()
            self.dist = utils.check_dist()
            self.os_version = utils.os_release()

            CobblerAPI.__has_loaded = True

            # load the modules first, or nothing else works...
            module_loader.load_modules()

            self._collection_mgr = collection_manager.CollectionManager(self)
            self.deserialize()

            # import signatures
            try:
                utils.load_signatures(self.settings().signature_path)
            except Exception as e:
                self.log("Failed to load signatures from %s: %s" % (self.settings().signature_path, e))
                return

            self.log("%d breeds and %d OS versions read from the signature file" % (
                len(utils.get_valid_breeds()), len(utils.get_valid_os_versions()))
            )

            self.authn = self.get_module_from_file(
                "authentication",
                "module",
                "authn_configfile"
            )
            self.authz = self.get_module_from_file(
                "authorization",
                "module",
                "authz_allowall"
            )

            # FIXME: pass more loggers around, and also see that those
            # using things via tasks construct their own yumgen/tftpgen
            # versus reusing this one, which has the wrong logger
            # (most likely) for background tasks.

            self.yumgen = yumgen.YumGen(self._collection_mgr)
            self.tftpgen = tftpgen.TFTPGen(self._collection_mgr, logger=self.logger)
            self.power_mgr = power_manager.PowerManager(self, self._collection_mgr)
            self.logger.debug("API handle initialized")
            self.perms_ok = True

    # ==========================================================

    def is_selinux_enabled(self):
        """
        Returns whether selinux is enabled on the cobbler server.
        We check this just once at cobbler API init time, because
        a restart is required to change this; this does /not/ check
        enforce/permissive, nor does it need to.
        """
        return self.selinux_enabled

    def is_selinux_supported(self):
        """
        Returns whether or not the OS is sufficient enough
        to run with SELinux enabled (currently EL 5 or later).
        """
        self.dist
        if self.dist == "redhat" and self.os_version < 5:
            # doesn't support public_content_t
            return False
        return True

    # ==========================================================

    def last_modified_time(self):
        """
        Returns the time of the last modification to cobbler, made by any
        API instance, regardless of the serializer type.
        """
        if not os.path.exists("/var/lib/cobbler/.mtime"):
            fd = os.open("/var/lib/cobbler/.mtime", os.O_CREAT | os.O_RDWR, 0200)
            os.write(fd, "0")
            os.close(fd)
            return 0
        fd = open("/var/lib/cobbler/.mtime")
        data = fd.read().strip()
        return float(data)

    # ==========================================================

    def log(self, msg, args=None, debug=False):
        if debug:
            logger = self.logger.debug
        else:
            logger = self.logger.info
        if args is None:
            logger("%s" % msg)
        else:
            logger("%s; %s" % (msg, str(args)))

    # ==========================================================

    def version(self, extended=False):
        """
        What version is cobbler?

        If extended == False, returns a float for backwards compatibility

        If extended == True, returns a dict:

            gitstamp      -- the last git commit hash
            gitdate       -- the last git commit date on the builder machine
            builddate     -- the time of the build
            version       -- something like "1.3.2"
            version_tuple -- something like [ 1, 3, 2 ]
        """
        config = ConfigParser()
        config.read("/etc/cobbler/version")
        data = {}
        data["gitdate"] = config.get("cobbler", "gitdate")
        data["gitstamp"] = config.get("cobbler", "gitstamp")
        data["builddate"] = config.get("cobbler", "builddate")
        data["version"] = config.get("cobbler", "version")
        # dont actually read the version_tuple from the version file
        data["version_tuple"] = []
        for num in data["version"].split("."):
            data["version_tuple"].append(int(num))

        if not extended:
            # for backwards compatibility and use with koan's comparisons
            elems = data["version_tuple"]
            return int(elems[0]) + 0.1 * int(elems[1]) + 0.001 * int(elems[2])
        else:
            return data

    # ==========================================================

    def __cmp(self, a, b):
        return cmp(a.name, b.name)

    def get_item(self, what, name):
        self.log("get_item", [what, name], debug=True)
        item = self._collection_mgr.get_items(what).get(name)
        self.log("done with get_item", [what, name], debug=True)
        return item             # self._collection_mgr.get_items(what).get(name)

    def get_items(self, what):
        self.log("get_items", [what], debug=True)
        items = self._collection_mgr.get_items(what)
        self.log("done with get_items", [what], debug=True)
        return items            # self._collection_mgr.get_items(what)

    def distros(self):
        """
        Return the current list of distributions
        """
        return self.get_items("distro")

    def profiles(self):
        """
        Return the current list of profiles
        """
        return self.get_items("profile")

    def systems(self):
        """
        Return the current list of systems
        """
        return self.get_items("system")

    def repos(self):
        """
        Return the current list of repos
        """
        return self.get_items("repo")

    def images(self):
        """
        Return the current list of images
        """
        return self.get_items("image")

    def settings(self):
        """
        Return the application configuration
        """
        return self._collection_mgr.settings()

    def mgmtclasses(self):
        """
        Return the current list of mgmtclasses
        """
        return self.get_items("mgmtclass")

    def packages(self):
        """
        Return the current list of packages
        """
        return self.get_items("package")

    def files(self):
        """
        Return the current list of files
        """
        return self.get_items("file")

    # =======================================================================

    def copy_item(self, what, ref, newname, logger=None):
        self.log("copy_item(%s)" % what, [ref.name, newname])
        self.get_items(what).copy(ref, newname, logger=logger)

    def copy_distro(self, ref, newname):
        self.copy_item("distro", ref, newname, logger=None)

    def copy_profile(self, ref, newname):
        self.copy_item("profile", ref, newname, logger=None)

    def copy_system(self, ref, newname):
        self.copy_item("system", ref, newname, logger=None)

    def copy_repo(self, ref, newname):
        self.copy_item("repo", ref, newname, logger=None)

    def copy_image(self, ref, newname):
        self.copy_item("image", ref, newname, logger=None)

    def copy_mgmtclass(self, ref, newname):
        self.copy_item("mgmtclass", ref, newname, logger=None)

    def copy_package(self, ref, newname):
        self.copy_item("package", ref, newname, logger=None)

    def copy_file(self, ref, newname):
        self.copy_item("file", ref, newname, logger=None)

    # ==========================================================================

    def remove_item(self, what, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        if isinstance(what, basestring):
            if isinstance(ref, basestring):
                ref = self.get_item(what, ref)
                if ref is None:
                    return      # nothing to remove
        self.log("remove_item(%s)" % what, [ref.name])
        self.get_items(what).remove(ref.name, recursive=recursive, with_delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_distro(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        self.remove_item("distro", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_profile(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        self.remove_item("profile", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_system(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        self.remove_item("system", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_repo(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        self.remove_item("repo", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_image(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        self.remove_item("image", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_mgmtclass(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        self.remove_item("mgmtclass", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_package(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        self.remove_item("package", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_file(self, ref, recursive=False, delete=True, with_triggers=True, logger=None):
        self.remove_item("file", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    # ==========================================================================

    def rename_item(self, what, ref, newname, logger=None):
        self.log("rename_item(%s)" % what, [ref.name, newname])
        self.get_items(what).rename(ref, newname, logger=logger)

    def rename_distro(self, ref, newname, logger=None):
        self.rename_item("distro", ref, newname, logger=logger)

    def rename_profile(self, ref, newname, logger=None):
        self.rename_item("profile", ref, newname, logger=logger)

    def rename_system(self, ref, newname, logger=None):
        self.rename_item("system", ref, newname, logger=logger)

    def rename_repo(self, ref, newname, logger=None):
        self.rename_item("repo", ref, newname, logger=logger)

    def rename_image(self, ref, newname, logger=None):
        self.rename_item("image", ref, newname, logger=logger)

    def rename_mgmtclass(self, ref, newname, logger=None):
        self.rename_item("mgmtclass", ref, newname, logger=logger)

    def rename_package(self, ref, newname, logger=None):
        self.rename_item("package", ref, newname, logger=logger)

    def rename_file(self, ref, newname, logger=None):
        self.rename_item("file", ref, newname, logger=logger)

    # ==========================================================================

    # FIXME: add a new_item method

    def new_distro(self, is_subobject=False):
        self.log("new_distro", [is_subobject])
        return item_distro.Distro(self._collection_mgr, is_subobject=is_subobject)

    def new_profile(self, is_subobject=False):
        self.log("new_profile", [is_subobject])
        return item_profile.Profile(self._collection_mgr, is_subobject=is_subobject)

    def new_system(self, is_subobject=False):
        self.log("new_system", [is_subobject])
        return item_system.System(self._collection_mgr, is_subobject=is_subobject)

    def new_repo(self, is_subobject=False):
        self.log("new_repo", [is_subobject])
        return item_repo.Repo(self._collection_mgr, is_subobject=is_subobject)

    def new_image(self, is_subobject=False):
        self.log("new_image", [is_subobject])
        return item_image.Image(self._collection_mgr, is_subobject=is_subobject)

    def new_mgmtclass(self, is_subobject=False):
        self.log("new_mgmtclass", [is_subobject])
        return item_mgmtclass.Mgmtclass(self._collection_mgr, is_subobject=is_subobject)

    def new_package(self, is_subobject=False):
        self.log("new_package", [is_subobject])
        return item_package.Package(self._collection_mgr, is_subobject=is_subobject)

    def new_file(self, is_subobject=False):
        self.log("new_file", [is_subobject])
        return item_file.File(self._collection_mgr, is_subobject=is_subobject)

    # ==========================================================================

    def add_item(self, what, ref, check_for_duplicate_names=False, save=True, logger=None):
        self.log("add_item(%s)" % what, [ref.name])
        self.get_items(what).add(ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_distro(self, ref, check_for_duplicate_names=False, save=True, logger=None):
        self.add_item("distro", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_profile(self, ref, check_for_duplicate_names=False, save=True, logger=None):
        self.add_item("profile", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_system(self, ref, check_for_duplicate_names=False, check_for_duplicate_netinfo=False, save=True, logger=None):
        self.add_item("system", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_repo(self, ref, check_for_duplicate_names=False, save=True, logger=None):
        self.add_item("repo", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_image(self, ref, check_for_duplicate_names=False, save=True, logger=None):
        self.add_item("image", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_mgmtclass(self, ref, check_for_duplicate_names=False, save=True, logger=None):
        self.add_item("mgmtclass", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_package(self, ref, check_for_duplicate_names=False, save=True, logger=None):
        self.add_item("package", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_file(self, ref, check_for_duplicate_names=False, save=True, logger=None):
        self.add_item("file", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    # ==========================================================================

    # FIXME: find_items should take all the arguments the other find
    # methods do.

    def find_items(self, what, criteria=None):
        self.log("find_items", [what])
        # defaults
        if criteria is None:
            criteria = {}
        items = self._collection_mgr.get_items(what)
        # empty criteria returns everything
        if criteria == {}:
            res = items
        else:
            res = items.find(return_list=True, no_errors=False, **criteria)
        return res

    def find_distro(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._collection_mgr.distros().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_profile(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._collection_mgr.profiles().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_system(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._collection_mgr.systems().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_repo(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._collection_mgr.repos().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_image(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._collection_mgr.images().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_mgmtclass(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._collection_mgr.mgmtclasses().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_package(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._collection_mgr.packages().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_file(self, name=None, return_list=False, no_errors=False, **kargs):
        return self._collection_mgr.files().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    # ==========================================================================

    def __since(self, mtime, collector, collapse=False):
        """
        Called by get_*_since functions.
        """
        results1 = collector()
        results2 = []
        for x in results1:
            if x.mtime == 0 or x.mtime >= mtime:
                if not collapse:
                    results2.append(x)
                else:
                    results2.append(x.to_dict())
        return results2

    def get_distros_since(self, mtime, collapse=False):
        """
        Returns distros modified since a certain time (in seconds since Epoch)
        collapse=True specifies returning a dict instead of objects.
        """
        return self.__since(mtime, self.distros, collapse=collapse)

    def get_profiles_since(self, mtime, collapse=False):
        return self.__since(mtime, self.profiles, collapse=collapse)

    def get_systems_since(self, mtime, collapse=False):
        return self.__since(mtime, self.systems, collapse=collapse)

    def get_repos_since(self, mtime, collapse=False):
        return self.__since(mtime, self.repos, collapse=collapse)

    def get_images_since(self, mtime, collapse=False):
        return self.__since(mtime, self.images, collapse=collapse)

    def get_mgmtclasses_since(self, mtime, collapse=False):
        return self.__since(mtime, self.mgmtclasses, collapse=collapse)

    def get_packages_since(self, mtime, collapse=False):
        return self.__since(mtime, self.packages, collapse=collapse)

    def get_files_since(self, mtime, collapse=False):
        return self.__since(mtime, self.files, collapse=collapse)

    # ==========================================================================

    def get_signatures(self):
        return utils.SIGNATURE_CACHE

    def signature_update(self, logger):
        try:
            tmpfile = tempfile.NamedTemporaryFile()
            proxies = {}
            proxies['http'] = self.settings().proxy_url_ext
            response = urlgrabber.grabber.urlopen(self.settings().signature_url, proxies=proxies)
            sigjson = response.read()
            tmpfile.write(sigjson)
            tmpfile.flush()

            logger.debug("Successfully got file from %s" % self.settings().signature_url)
            # test the import without caching it
            try:
                utils.load_signatures(tmpfile.name, cache=False)
            except:
                logger.error("Downloaded signatures failed test load (tempfile = %s)" % tmpfile.name)

            # rewrite the real signature file and import it for real
            f = open(self.settings().signature_path, "w")
            f.write(sigjson)
            f.close()

            utils.load_signatures(self.settings().signature_path)
        except:
            utils.log_exc(logger)

    # ==========================================================================

    def dump_vars(self, obj, format=False):
        return obj.dump_vars(format)

    # ==========================================================================

    def auto_add_repos(self):
        """
        Import any repos this server knows about and mirror them.
        Credit: Seth Vidal.
        """
        self.log("auto_add_repos")
        try:
            import yum
        except:
            raise CX(_("yum is not installed"))

        version = yum.__version__
        (a, b, c) = version.split(".")
        version = a * 1000 + b * 100 + c
        if version < 324:
            raise CX(_("need yum > 3.2.4 to proceed"))

        base = yum.YumBase()
        base.doRepoSetup()
        repos = base.repos.listEnabled()
        if len(repos) == 0:
            raise CX(_("no repos enabled/available -- giving up."))

        for repo in repos:
            url = repo.urls[0]
            cobbler_repo = self.new_repo()
            auto_name = repo.name.replace(" ", "")
            # FIXME: probably doesn't work for yum-rhn-plugin ATM
            cobbler_repo.set_mirror(url)
            cobbler_repo.set_name(auto_name)
            print "auto adding: %s (%s)" % (auto_name, url)
            self._collection_mgr.repos().add(cobbler_repo, save=True)

        # run cobbler reposync to apply changes

    # ==========================================================================

    def get_repo_config_for_profile(self, obj):
        return self.yumgen.get_yum_config(obj, True)

    def get_repo_config_for_system(self, obj):
        return self.yumgen.get_yum_config(obj, False)

    # ==========================================================================

    def get_template_file_for_profile(self, obj, path):
        template_results = self.tftpgen.write_templates(obj, False, path)
        if path in template_results:
            return template_results[path]
        else:
            return "# template path not found for specified profile"

    def get_template_file_for_system(self, obj, path):
        template_results = self.tftpgen.write_templates(obj, False, path)
        if path in template_results:
            return template_results[path]
        else:
            return "# template path not found for specified system"

    # ==========================================================================

    def generate_gpxe(self, profile, system):
        self.log("generate_gpxe")
        if system:
            return self.tftpgen.generate_gpxe("system", system)
        else:
            return self.tftpgen.generate_gpxe("profile", profile)

    # ==========================================================================

    def generate_bootcfg(self, profile, system):
        self.log("generate_bootcfg")
        if system:
            return self.tftpgen.generate_bootcfg("system", system)
        else:
            return self.tftpgen.generate_bootcfg("profile", profile)

    # ==========================================================================

    def generate_script(self, profile, system, name):
        self.log("generate_script")
        if system:
            return self.tftpgen.generate_script("system", system, name)
        else:
            return self.tftpgen.generate_script("profile", profile, name)

    # ==========================================================================

    def check(self, logger=None):
        """
        See if all preqs for network booting are valid.  This returns
        a list of strings containing instructions on things to correct.
        An empty list means there is nothing to correct, but that still
        doesn't mean there are configuration errors.  This is mainly useful
        for human admins, who may, for instance, forget to properly set up
        their TFTP servers for PXE, etc.
        """
        self.log("check")
        check = action_check.CobblerCheck(self._collection_mgr, logger=logger)
        return check.run()

    # ==========================================================================

    def dlcontent(self, force=False, logger=None):
        """
        Downloads bootloader content that may not be avialable in packages
        for the given arch, ex: if installing on PPC, get syslinux. If installing
        on x86_64, get elilo, etc.
        """
        # FIXME: teach code that copies it to grab from the right place
        self.log("dlcontent")
        grabber = action_dlcontent.ContentDownloader(self._collection_mgr, logger=logger)
        return grabber.run(force)

    # ==========================================================================

    def validate_autoinstall_files(self, logger=None):

        self.log("validate_autoinstall_files")
        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(self._collection_mgr)
        autoinstall_mgr.validate_autoinstall_files(logger)

    # ==========================================================================

    def sync(self, verbose=False, logger=None):
        """
        Take the values currently written to the configuration files in
        /etc, and /var, and build out the information tree found in
        /tftpboot.  Any operations done in the API that have not been
        saved with serialize() will NOT be synchronized with this command.
        """
        self.log("sync")
        sync = self.get_sync(verbose=verbose, logger=logger)
        sync.run()

    # ==========================================================================

    def sync_dhcp(self, verbose=False, logger=None):
        """
        Only build out the DHCP configuration
        """
        self.log("sync_dhcp")
        sync = self.get_sync(verbose=verbose, logger=logger)
        sync.sync_dhcp()
    # ==========================================================================

    def get_sync(self, verbose=False, logger=None):
        self.dhcp = self.get_module_from_file(
            "dhcp",
            "module",
            "manage_isc"
        ).get_manager(self._collection_mgr, logger)
        self.dns = self.get_module_from_file(
            "dns",
            "module",
            "manage_bind"
        ).get_manager(self._collection_mgr, logger)
        self.tftpd = self.get_module_from_file(
            "tftpd",
            "module",
            "in_tftpd",
        ).get_manager(self._collection_mgr, logger)

        return action_sync.CobblerSync(self._collection_mgr, dhcp=self.dhcp, dns=self.dns, tftpd=self.tftpd, verbose=verbose, logger=logger)

    # ==========================================================================

    def reposync(self, name=None, tries=1, nofail=False, logger=None):
        """
        Take the contents of /var/lib/cobbler/repos and update them --
        or create the initial copy if no contents exist yet.
        """
        self.log("reposync", [name])
        reposync = action_reposync.RepoSync(self._collection_mgr, tries=tries, nofail=nofail, logger=logger)
        reposync.run(name)

    # ==========================================================================

    def status(self, mode, logger=None):
        statusifier = action_status.CobblerStatusReport(self._collection_mgr, mode, logger=logger)
        return statusifier.run()

    # ==========================================================================

    def import_tree(self, mirror_url, mirror_name, network_root=None, autoinstall_file=None, rsync_flags=None, arch=None, breed=None, os_version=None, logger=None):
        """
        Automatically import a directory tree full of distribution files.
        mirror_url can be a string that represents a path, a user@host
        syntax for SSH, or an rsync:// address.  If mirror_url is a
        filesystem path and mirroring is not desired, set network_root
        to something like "nfs://path/to/mirror_url/root"
        """
        self.log("import_tree", [mirror_url, mirror_name, network_root, autoinstall_file, rsync_flags])

        # both --path and --name are required arguments
        if mirror_url is None or not mirror_url:
            self.log("import failed.  no --path specified")
            return False
        if mirror_name is None or not mirror_name:
            self.log("import failed.  no --name specified")
            return False

        path = os.path.normpath("%s/distro_mirror/%s" % (self.settings().webdir, mirror_name))
        if arch is not None:
            arch = arch.lower()
            if arch == "x86":
                # be consistent
                arch = "i386"
            if path.split("-")[-1] != arch:
                path += ("-%s" % arch)

        # we need to mirror (copy) the files
        self.log("importing from a network location, running rsync to fetch the files first")

        utils.mkdir(path)

        # prevent rsync from creating the directory name twice
        # if we are copying via rsync

        if not mirror_url.endswith("/"):
            mirror_url = "%s/" % mirror_url

        if mirror_url.startswith("http://") or mirror_url.startswith("ftp://") or mirror_url.startswith("nfs://"):
            # http mirrors are kind of primative.  rsync is better.
            # that's why this isn't documented in the manpage and we don't support them.
            # TODO: how about adding recursive FTP as an option?
            self.log("unsupported protocol")
            return False
        else:
            # good, we're going to use rsync..
            # we don't use SSH for public mirrors and local files.
            # presence of user@host syntax means use SSH
            spacer = ""
            if not mirror_url.startswith("rsync://") and not mirror_url.startswith("/"):
                spacer = ' -e "ssh" '
            rsync_cmd = RSYNC_CMD
            if rsync_flags:
                rsync_cmd += " " + rsync_flags

            # if --available-as was specified, limit the files we
            # pull down via rsync to just those that are critical
            # to detecting what the distro is
            if network_root is not None:
                rsync_cmd += " --include-from=/etc/cobbler/import_rsync_whitelist"

            # kick off the rsync now
            utils.run_this(rsync_cmd, (spacer, mirror_url, path), self.logger)

        if network_root is not None:
            # in addition to mirroring, we're going to assume the path is available
            # over http, ftp, and nfs, perhaps on an external filer.  scanning still requires
            # --mirror is a filesystem path, but --available-as marks the network path.
            # this allows users to point the path at a directory containing just the network
            # boot files while the rest of the distro files are available somewhere else.

            # find the filesystem part of the path, after the server bits, as each distro
            # URL needs to be calculated relative to this.

            if not network_root.endswith("/"):
                network_root += "/"
            valid_roots = ["nfs://", "ftp://", "http://"]
            for valid_root in valid_roots:
                if network_root.startswith(valid_root):
                    break
            else:
                self.log("Network root given to --available-as must be nfs://, ftp://, or http://")
                return False

            if network_root.startswith("nfs://"):
                try:
                    (a, b, rest) = network_root.split(":", 3)
                except:
                    self.log("Network root given to --available-as is missing a colon, please see the manpage example.")
                    return False

        import_module = self.get_module_by_name("manage_import_signatures").get_import_manager(self._collection_mgr, logger)
        import_module.run(path, mirror_name, network_root, autoinstall_file, arch, breed, os_version)

    # ==========================================================================

    def acl_config(self, adduser=None, addgroup=None, removeuser=None, removegroup=None, logger=None):
        """
        Configures users/groups to run the cobbler CLI as non-root.
        Pass in only one option at a time.  Powers "cobbler aclconfig"
        """
        acl = action_acl.AclConfig(self._collection_mgr, logger)
        acl.run(
            adduser=adduser,
            addgroup=addgroup,
            removeuser=removeuser,
            removegroup=removegroup
        )

    # ==========================================================================

    def serialize(self):
        """
        Save the collections to disk.
        Cobbler internal use only.
        """
        self._collection_mgr.serialize()

    def deserialize(self):
        """
        Load collections from disk.
        Cobbler internal use only.
        """
        return self._collection_mgr.deserialize()

    # ==========================================================================

    def get_module_by_name(self, module_name):
        """
        Returns a loaded cobbler module named 'name', if one exists, else None.
        Cobbler internal use only.
        """
        return module_loader.get_module_by_name(module_name)

    def get_module_from_file(self, section, name, fallback=None):
        """
        Looks in /etc/cobbler/modules.conf for a section called 'section'
        and a key called 'name', and then returns the module that corresponds
        to the value of that key.
        Cobbler internal use only.
        """
        return module_loader.get_module_from_file(section, name, fallback)

    def get_module_name_from_file(self, section, name, fallback=None):
        """
        Looks up a module the same as get_module_from_file but returns
        the module name rather than the module itself
        """
        return module_loader.get_module_name(section, name, fallback)

    def get_modules_in_category(self, category):
        """
        Returns all modules in a given category, for instance "serializer", or "cli".
        Cobbler internal use only.
        """
        return module_loader.get_modules_in_category(category)

    # ==========================================================================

    def authenticate(self, user, password):
        """
        (Remote) access control.
        Cobbler internal use only.
        """
        rc = self.authn.authenticate(self, user, password)
        self.log("authenticate", [user, rc])
        return rc

    def authorize(self, user, resource, arg1=None, arg2=None):
        """
        (Remote) access control.
        Cobbler internal use only.
        """
        rc = self.authz.authorize(self, user, resource, arg1, arg2)
        self.log("authorize", [user, resource, arg1, arg2, rc], debug=True)
        return rc

    # ==========================================================================

    def build_iso(self, iso=None,
                  profiles=None, systems=None, buildisodir=None, distro=None,
                  standalone=None, airgapped=None, source=None,
                  exclude_dns=None, mkisofs_opts=None, logger=None):
        builder = action_buildiso.BuildIso(self._collection_mgr, logger=logger)
        builder.run(
            iso=iso,
            profiles=profiles, systems=systems,
            buildisodir=buildisodir, distro=distro,
            standalone=standalone, airgapped=airgapped, source=source,
            exclude_dns=exclude_dns, mkisofs_opts=mkisofs_opts
        )

    # ==========================================================================

    def hardlink(self, logger=None):
        linker = action_hardlink.HardLinker(self._collection_mgr, logger=logger)
        return linker.run()

    # ==========================================================================

    def replicate(self, cobbler_master=None, distro_patterns="", profile_patterns="", system_patterns="", repo_patterns="", image_patterns="",
                  mgmtclass_patterns=None, package_patterns=None, file_patterns=None, prune=False, omit_data=False, sync_all=False, use_ssl=False, logger=None):
        """
        Pull down data/configs from a remote cobbler server that is a master to this server.
        """
        replicator = action_replicate.Replicate(self._collection_mgr, logger=logger)
        return replicator.run(
            cobbler_master=cobbler_master,
            distro_patterns=distro_patterns,
            profile_patterns=profile_patterns,
            system_patterns=system_patterns,
            repo_patterns=repo_patterns,
            image_patterns=image_patterns,
            mgmtclass_patterns=mgmtclass_patterns,
            package_patterns=package_patterns,
            file_patterns=file_patterns,
            prune=prune,
            omit_data=omit_data,
            sync_all=sync_all,
            use_ssl=use_ssl
        )

    # ==========================================================================

    def report(self, report_what=None, report_name=None, report_type=None, report_fields=None, report_noheaders=None):
        """
        Report functionality for cobbler
        """
        reporter = action_report.Report(self._collection_mgr)
        return reporter.run(report_what=report_what, report_name=report_name,
                            report_type=report_type, report_fields=report_fields,
                            report_noheaders=report_noheaders)

    # ==========================================================================

    def power_system(self, system, power_operation, user=None, password=None, logger=None):
        """
        Power on / power off / get power status /reboot a system.

        @param str system Cobbler system
        @param str power_operation power operation. Valid values: on, off, reboot, status
        @param str token Cobbler authentication token
        @param str user power management user
        @param str password power management password
        @param Logger logger logger
        @return bool if operation was successful
        """

        if power_operation == "on":
            self.power_mgr.power_on(system, user=user, password=password, logger=logger)
        elif power_operation == "off":
            self.power_mgr.power_off(system, user=user, password=password, logger=logger)
        elif power_operation == "status":
            self.power_mgr.get_power_status(system, user=user, password=password, logger=logger)
        elif power_operation == "reboot":
            self.power_mgr.reboot(system, user=user, password=password, logger=logger)
        else:
            utils.die(self.logger, "invalid power operation '%s', expected on/off/status/reboot" % power_operation)

    # ==========================================================================

    def clear_logs(self, system, logger=None):
        """
        Clears console and anamon logs for system
        """
        action_log.LogTool(self._collection_mgr, system, self, logger=logger).clear()

    def get_os_details(self):
        return (self.dist, self.os_version)

# EOF
