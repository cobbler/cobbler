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

from configparser import ConfigParser

import os
import random
import tempfile
from typing import Optional

from cobbler.actions import status, dlcontent, hardlink, sync, buildiso, replicate, report, log, acl, check, reposync
from cobbler import autoinstall_manager
from cobbler import clogger
from cobbler.cobbler_collections import manager
from cobbler.items import package, system, image, profile, repo, mgmtclass, distro, file
from cobbler import module_loader
from cobbler import power_manager
from cobbler import tftpgen
from cobbler import utils
from cobbler import yumgen
from cobbler import autoinstallgen
from cobbler import download_manager
from cobbler.cexceptions import CX


ERROR = 100
INFO = 10
DEBUG = 5

# FIXME: add --quiet depending on if not --verbose?
RSYNC_CMD = "rsync -a %s '%s' %s --progress"

# notes on locking:
# - CobblerAPI is a singleton object
# - The XMLRPC variants allow 1 simultaneous request, therefore we flock on our settings file for now on a request by
#   request basis.


class CobblerAPI:
    """
    Python API module for Cobbler.
    See source for cobbler.py, or pydoc, for example usage.
    Cli apps and daemons should import api.py, and no other Cobbler code.
    """
    __shared_state = {}
    __has_loaded = False

    def __init__(self, is_cobblerd: bool = False):
        """
        Constructor

        :param is_cobblerd: Wether this API is run as a deamon or not.
        """

        # FIXME: this should be switchable through some simple system

        self.__dict__ = CobblerAPI.__shared_state
        self.perms_ok = False
        if not CobblerAPI.__has_loaded:
            # NOTE: we do not log all API actions, because a simple CLI invocation may call adds and such to load the
            # config, which would just fill up the logs, so we'll do that logging at CLI level (and remote.py web
            # service level) instead.

            random.seed()
            self.is_cobblerd = is_cobblerd

            try:
                self.logger = clogger.Logger()
            except CX:
                # return to CLI/other but perms are not valid
                # perms_ok is False
                return

            # FIXME: conslidate into 1 server instance

            self.selinux_enabled = utils.is_selinux_enabled()
            self.dist, self.os_version = utils.os_release()

            CobblerAPI.__has_loaded = True

            # load the modules first, or nothing else works...
            module_loader.load_modules()

            self._collection_mgr = manager.CollectionManager(self)
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

            # FIXME: pass more loggers around, and also see that those using things via tasks construct their own
            #  yumgen/tftpgen versus reusing this one, which has the wrong logger (most likely) for background tasks.

            self.autoinstallgen = autoinstallgen.AutoInstallationGen(self._collection_mgr)
            self.yumgen = yumgen.YumGen(self._collection_mgr)
            self.tftpgen = tftpgen.TFTPGen(self._collection_mgr, logger=self.logger)
            self.power_mgr = power_manager.PowerManager(self, self._collection_mgr)
            self.logger.debug("API handle initialized")
            self.perms_ok = True

    # ==========================================================

    def is_selinux_enabled(self) -> bool:
        """
        Returns whether selinux is enabled on the Cobbler server.
        We check this just once at Cobbler API init time, because a restart is required to change this; this does
        /not/ check enforce/permissive, nor does it need to.
        """
        return self.selinux_enabled

    def is_selinux_supported(self) -> bool:
        """
        Returns whether or not the OS is sufficient enough to run with SELinux enabled (currently EL 5 or later).

        :returns: False per default. If Distro is Redhat and Version >= 5 then it returns true.
        """
        # FIXME: This detection is flawed. There is more than just Rhel with selinux and the original implementation was
        #        too broad.
        if ("red hat" in self.dist or "redhat" in self.dist) and self.os_version >= 5:
            return True
        # doesn't support public_content_t
        return False

    # ==========================================================

    def last_modified_time(self) -> float:
        """
        Returns the time of the last modification to Cobbler, made by any API instance, regardless of the serializer
        type.

        :returns: 0 if there is no file where the information required for this method is saved.
        """
        if not os.path.exists("/var/lib/cobbler/.mtime"):
            fd = open("/var/lib/cobbler/.mtime", 'w')
            fd.write("0")
            fd.close()
            return float(0)
        fd = open("/var/lib/cobbler/.mtime", 'r')
        data = fd.read().strip()
        return float(data)

    # ==========================================================

    def log(self, msg: str, args=None, debug: bool = False):
        """
        Logs a message with the already initiated logger of this object.

        :param msg: The message to log.
        :param args: Optional message which gets appended to the main msg with a ';'.
        :param debug: Weather the logged message is a debug message (true) or info (false).
        """
        if debug:
            logger = self.logger.debug
        else:
            logger = self.logger.info
        if args is None:
            logger("%s" % msg)
        else:
            logger("%s; %s" % (msg, str(args)))

    # ==========================================================

    def version(self, extended: bool = False):
        """
        What version is Cobbler?

        If extended == False, returns a float for backwards compatibility
        If extended == True, returns a dict:

            gitstamp      -- the last git commit hash
            gitdate       -- the last git commit date on the builder machine
            builddate     -- the time of the build
            version       -- something like "1.3.2"
            version_tuple -- something like [ 1, 3, 2 ]

        :param extended: False returns a float, True a Dictionary.
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

    def get_item(self, what: str, name: str):
        """
        Get a general item.

        :param what: The item type to retrieve from the internal database.
        :param name: The name of the item to retrieve.
        :return: An item of the desired type.
        """
        self.log("get_item", [what, name], debug=True)
        item = self._collection_mgr.get_items(what).get(name)
        self.log("done with get_item", [what, name], debug=True)
        return item

    def get_items(self, what: str):
        """
        Get all items of a collection.

        :param what: The collection to query.
        :return: The items which were queried. May return no items.
        """
        self.log("get_items", [what], debug=True)
        items = self._collection_mgr.get_items(what)
        self.log("done with get_items", [what], debug=True)
        return items

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
        """
        General copy method which is called by the specific methods.

        :param what: The collection type which gets copied.
        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        :param logger: The logger which is used for auditing the copy task.
        """
        self.log("copy_item(%s)" % what, [ref.name, newname])
        self.get_items(what).copy(ref, newname, logger=logger)

    def copy_distro(self, ref, newname):
        """
        This method copies a distro which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self.copy_item("distro", ref, newname, logger=None)

    def copy_profile(self, ref, newname):
        """
        This method copies a profile which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self.copy_item("profile", ref, newname, logger=None)

    def copy_system(self, ref, newname):
        """
        This method copies a system which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self.copy_item("system", ref, newname, logger=None)

    def copy_repo(self, ref, newname):
        """
        This method copies a repository which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self.copy_item("repo", ref, newname, logger=None)

    def copy_image(self, ref, newname):
        """
        This method copies an image which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self.copy_item("image", ref, newname, logger=None)

    def copy_mgmtclass(self, ref, newname):
        """
        This method copies a management class which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self.copy_item("mgmtclass", ref, newname, logger=None)

    def copy_package(self, ref, newname):
        """
        This method copies a package which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self.copy_item("package", ref, newname, logger=None)

    def copy_file(self, ref, newname):
        """
        This method copies a file which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self.copy_item("file", ref, newname, logger=None)

    # ==========================================================================

    def remove_item(self, what: str, ref: str, recursive: bool = False, delete: bool = True, with_triggers: bool = True,
                    logger=None):
        """
        Remove a general item. This method should not be used by an external api. Please use the specific
        remove_<itemtype> methods.

        :param what: The type of the item.
        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        :param logger: The logger to audit the removal with.
        """
        if isinstance(what, str):
            if isinstance(ref, str):
                ref = self.get_item(what, ref)
                if ref is None:
                    return      # nothing to remove
        self.log("remove_item(%s)" % what, [ref.name])
        self.get_items(what).remove(ref.name, recursive=recursive, with_delete=delete, with_triggers=with_triggers,
                                    logger=logger)

    def remove_distro(self, ref: str, recursive: bool = False, delete: bool = True, with_triggers: bool = True,
                      logger=None):
        """
        Remove a distribution from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        :param logger: The logger to audit the removal with.
        """
        self.remove_item("distro", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_profile(self, ref: str, recursive: bool = False, delete: bool = True, with_triggers: bool = True,
                       logger=None):
        """
        Remove a profile from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        :param logger: The logger to audit the removal with.
        """
        self.remove_item("profile", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_system(self, ref: str, recursive: bool = False, delete: bool = True, with_triggers: bool = True,
                      logger=None):
        """
        Remove a system from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        :param logger: The logger to audit the removal with.
        """
        self.remove_item("system", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_repo(self, ref: str, recursive: bool = False, delete: bool = True, with_triggers: bool = True,
                    logger=None):
        """
        Remove a repository from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        :param logger: The logger to audit the removal with.
        """
        self.remove_item("repo", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_image(self, ref: str, recursive: bool = False, delete: bool = True, with_triggers: bool = True,
                     logger=None):
        """
        Remove a image from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        :param logger: The logger to audit the removal with.
        """
        self.remove_item("image", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_mgmtclass(self, ref: str, recursive: bool = False, delete: bool = True, with_triggers: bool = True,
                         logger=None):
        """
        Remove a management class from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        :param logger: The logger to audit the removal with.
        """
        self.remove_item("mgmtclass", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_package(self, ref: str, recursive: bool = False, delete: bool = True, with_triggers: bool = True,
                       logger=None):
        """
        Remove a package from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        :param logger: The logger to audit the removal with.
        """
        self.remove_item("package", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    def remove_file(self, ref: str, recursive: bool = False, delete: bool = True, with_triggers: bool = True,
                    logger=None):
        """
        Remove a file from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        :param logger: The logger to audit the removal with.
        """
        self.remove_item("file", ref, recursive=recursive, delete=delete, with_triggers=with_triggers, logger=logger)

    # ==========================================================================

    def rename_item(self, what, ref, newname, logger=None):
        """
        Remove a general item. This method should not be used by an external api. Please use the specific
        rename_<itemtype> methods.

        :param what: The type of object which should be renamed.
        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        :param logger: The logger to audit the removal with.
        """
        self.log("rename_item(%s)" % what, [ref.name, newname])
        self.get_items(what).rename(ref, newname, logger=logger)

    def rename_distro(self, ref, newname, logger=None):
        """
        Rename a distro to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        :param logger: The logger to audit the removal with.
        """
        self.rename_item("distro", ref, newname, logger=logger)

    def rename_profile(self, ref, newname, logger=None):
        """
        Rename a profile to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        :param logger: The logger to audit the removal with.
        """
        self.rename_item("profile", ref, newname, logger=logger)

    def rename_system(self, ref, newname, logger=None):
        """
        Rename a system to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        :param logger: The logger to audit the removal with.
        """
        self.rename_item("system", ref, newname, logger=logger)

    def rename_repo(self, ref, newname, logger=None):
        """
        Rename a repository to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        :param logger: The logger to audit the removal with.
        """
        self.rename_item("repo", ref, newname, logger=logger)

    def rename_image(self, ref, newname, logger=None):
        """
        Rename an image to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        :param logger: The logger to audit the removal with.
        """
        self.rename_item("image", ref, newname, logger=logger)

    def rename_mgmtclass(self, ref, newname, logger=None):
        """
        Rename a management class to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        :param logger: The logger to audit the removal with.
        """
        self.rename_item("mgmtclass", ref, newname, logger=logger)

    def rename_package(self, ref, newname, logger=None):
        """
        Rename a package to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        :param logger: The logger to audit the removal with.
        """
        self.rename_item("package", ref, newname, logger=logger)

    def rename_file(self, ref, newname, logger=None):
        """
        Rename a file to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        :param logger: The logger to audit the removal with.
        """
        self.rename_item("file", ref, newname, logger=logger)

    # ==========================================================================

    # FIXME: add a new_item method

    def new_distro(self, is_subobject: bool = False):
        """
        Returns a new empty distro object. This distro is not automatically persited. Persistance is achieved via
        ``save()``.

        :param is_subobject: If the object created is a subobject or not.
        :return: An empty Distro object.
        """
        self.log("new_distro", [is_subobject])
        return distro.Distro(self._collection_mgr, is_subobject=is_subobject)

    def new_profile(self, is_subobject: bool = False):
        """
        Returns a new empty profile object. This profile is not automatically persisted. Persistence is achieved via
        ``save()``.

        :param is_subobject: If the object created is a subobject or not.
        :return: An empty Profile object.
        """
        self.log("new_profile", [is_subobject])
        return profile.Profile(self._collection_mgr, is_subobject=is_subobject)

    def new_system(self, is_subobject: bool = False):
        """
        Returns a new empty system object. This system is not automatically persisted. Persistence is achieved via
        ``save()``.

        :param is_subobject: If the object created is a subobject or not.
        :return: An empty System object.
        """
        self.log("new_system", [is_subobject])
        return system.System(self._collection_mgr, is_subobject=is_subobject)

    def new_repo(self, is_subobject: bool = False):
        """
        Returns a new empty repo object. This repository is not automatically persisted. Persistence is achieved via
        ``save()``.

        :param is_subobject: If the object created is a subobject or not.
        :return: An empty repo object.
        """
        self.log("new_repo", [is_subobject])
        return repo.Repo(self._collection_mgr, is_subobject=is_subobject)

    def new_image(self, is_subobject: bool = False):
        """
        Returns a new empty image object. This image is not automatically persisted. Persistence is achieved via
        ``save()``.

        :param is_subobject: If the object created is a subobject or not.
        :return: An empty image object.
        """
        self.log("new_image", [is_subobject])
        return image.Image(self._collection_mgr, is_subobject=is_subobject)

    def new_mgmtclass(self, is_subobject: bool = False):
        """
        Returns a new empty mgmtclass object. This mgmtclass is not automatically persisted. Persistence is achieved via
        ``save()``.

        :param is_subobject: If the object created is a subobject or not.
        :return: An empty mgmtclass object.
        """
        self.log("new_mgmtclass", [is_subobject])
        return mgmtclass.Mgmtclass(self._collection_mgr, is_subobject=is_subobject)

    def new_package(self, is_subobject: bool = False):
        """
        Returns a new empty package object. This package is not automatically persisted. Persistence is achieved via
        ``save()``.

        :param is_subobject: If the object created is a subobject or not.
        :return: An empty Package object.
        """
        self.log("new_package", [is_subobject])
        return package.Package(self._collection_mgr, is_subobject=is_subobject)

    def new_file(self, is_subobject: bool = False):
        """
        Returns a new empty file object. This file is not automatically persisted. Persistence is achieved via
        ``save()``.

        :param is_subobject: If the object created is a subobject or not.
        :return: An empty File object.
        """
        self.log("new_file", [is_subobject])
        return file.File(self._collection_mgr, is_subobject=is_subobject)

    # ==========================================================================

    def add_item(self, what, ref, check_for_duplicate_names: bool = False, save: bool = True, logger=None):
        """
        Add an abstract item to a collection of its specific items. This is not meant for external use. Please reefer
        to one of the specific methods ``add_<type>``.

        :param what: The item type.
        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param logger: The logger to audit the removal with.
        """
        self.log("add_item(%s)" % what, [ref.name])
        self.get_items(what).add(ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_distro(self, ref, check_for_duplicate_names: bool = False, save: bool = True, logger=None):
        """
        Add a distribution to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param logger: The logger to audit the removal with.
        """
        self.add_item("distro", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_profile(self, ref, check_for_duplicate_names: bool = False, save: bool = True, logger=None):
        """
        Add a profile to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param logger: The logger to audit the removal with.
        """
        self.add_item("profile", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_system(self, ref, check_for_duplicate_names: bool = False, check_for_duplicate_netinfo=False,
                   save: bool = True, logger=None):
        """
        Add a system to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param check_for_duplicate_netinfo: If the name of the network interface should be unique or can be present
                                            multiple times.
        :param save: If the item should be persisted.
        :param logger: The logger to audit the removal with.
        """
        self.add_item("system", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_repo(self, ref, check_for_duplicate_names: bool = False, save: bool = True, logger=None):
        """
        Add a repository to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param logger: The logger to audit the removal with.
        """
        self.add_item("repo", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_image(self, ref, check_for_duplicate_names: bool = False, save: bool = True, logger=None):
        """
        Add an image to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param logger: The logger to audit the removal with.
        """
        self.add_item("image", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_mgmtclass(self, ref, check_for_duplicate_names: bool = False, save: bool = True, logger=None):
        """
        Add a management class to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param logger: The logger to audit the removal with.
        """
        self.add_item("mgmtclass", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_package(self, ref, check_for_duplicate_names: bool = False, save: bool = True, logger=None):
        """
        Add a package to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param logger: The logger to audit the removal with.
        """
        self.add_item("package", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    def add_file(self, ref, check_for_duplicate_names: bool = False, save: bool = True, logger=None):
        """
        Add a file to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param logger: The logger to audit the removal with.
        """
        self.add_item("file", ref, check_for_duplicate_names=check_for_duplicate_names, save=save, logger=logger)

    # ==========================================================================

    # FIXME: find_items should take all the arguments the other find methods do.

    def find_items(self, what, criteria=None):
        """
        This is the abstract base method for finding object int the api. It should not be used by external resources.
        Please reefer to the specific implementations of this method called ``find_<object type>``.

        :param what: The object type of the item to search for.
        :param criteria: The dictionary with the key-value pairs to find objects with.
        :return: The list of items witch match the search criteria.
        """
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
        """
        Find a distribution via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.distros().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_profile(self, name=None, return_list=False, no_errors=False, **kargs):
        """
        Find a profile via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.profiles().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_system(self, name=None, return_list=False, no_errors=False, **kargs):
        """
        Find a system via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.systems().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_repo(self, name=None, return_list=False, no_errors=False, **kargs):
        """
        Find a repository via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.repos().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_image(self, name=None, return_list=False, no_errors=False, **kargs):
        """
        Find an image via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.images().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_mgmtclass(self, name=None, return_list=False, no_errors=False, **kargs):
        """
        Find a management class via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.mgmtclasses().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_package(self, name=None, return_list=False, no_errors=False, **kargs):
        """
        Find a package via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.packages().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    def find_file(self, name=None, return_list=False, no_errors=False, **kargs):
        """
        Find a file via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.files().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)

    # ==========================================================================

    def __since(self, mtime, collector, collapse: bool = False) -> list:
        """
        Called by get_*_since functions. This is an internal part of Cobbler.

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collector: The list of objects to filter after mtime.
        :param collapse: Whether the object should be collapsed to a dict or not. If not the item objects are used for
                         the list.
        :return: The list of objects which are newer then the given timestamp.
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

    def get_distros_since(self, mtime, collapse: bool = False):
        """
        Returns distros modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: collapse=True specifies returning a dict instead of objects.
        :return: The list of distros which are newer then the given timestamp.
        """
        return self.__since(mtime, self.distros, collapse=collapse)

    def get_profiles_since(self, mtime, collapse: bool = False):
        """
        Returns profiles modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: If True then this specifies that a list of dicts should be returned instead of a list of
                         objects.
        :return: The list of profiles which are newer then the given timestamp.
        :rtype: list
        """
        return self.__since(mtime, self.profiles, collapse=collapse)

    def get_systems_since(self, mtime, collapse: bool = False):
        """
        Return systems modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: If True then this specifies that a list of dicts should be returned instead of a list of
                         objects.
        :return: The list of systems which are newer then the given timestamp.
        :rtype: list
        """
        return self.__since(mtime, self.systems, collapse=collapse)

    def get_repos_since(self, mtime, collapse: bool = False):
        """
        Return repositories modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: If True then this specifies that a list of dicts should be returned instead of a list of
                         objects.
        :return: The list of repositories which are newer then the given timestamp.
        :rtype: list
        """
        return self.__since(mtime, self.repos, collapse=collapse)

    def get_images_since(self, mtime, collapse: bool = False):
        """
        Return images modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: If True then this specifies that a list of dicts should be returned instead of a list of
                         objects.
        :return: The list of images which are newer then the given timestamp.
        :rtype: list
        """
        return self.__since(mtime, self.images, collapse=collapse)

    def get_mgmtclasses_since(self, mtime, collapse: bool = False):
        """
        Return management classes modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: If True then this specifies that a list of dicts should be returned instead of a list of
                         objects.
        :return: The list of management classes which are newer then the given timestamp.
        :rtype: list
        """
        return self.__since(mtime, self.mgmtclasses, collapse=collapse)

    def get_packages_since(self, mtime, collapse: bool = False):
        """
        Return packages modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: If True then this specifies that a list of dicts should be returned instead of a list of
                         objects.
        :return: The list of packages which are newer then the given timestamp.
        :rtype: list
        """
        return self.__since(mtime, self.packages, collapse=collapse)

    def get_files_since(self, mtime, collapse: bool = False):
        """
        Return files modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: If True then this specifies that a list of dicts should be returned instead of a list of
                         objects.
        :return: The list of files which are newer then the given timestamp.
        :rtype: list
        """
        return self.__since(mtime, self.files, collapse=collapse)

    # ==========================================================================

    def get_signatures(self) -> dict:
        """
        This returns the local signature cache.

        :return: The dict containing all signatures.
        """
        return utils.SIGNATURE_CACHE

    def signature_update(self, logger):
        """
        Update all signatures from the URL specified in the settings.

        :param logger: The logger to audit the removal with.
        """
        try:
            url = self.settings().signature_url
            dlmgr = download_manager.DownloadManager(self._collection_mgr, self.logger)
            # write temp json file
            tmpfile = tempfile.NamedTemporaryFile()
            sigjson = dlmgr.urlread(url)
            tmpfile.write(sigjson.text.encode())
            tmpfile.flush()
            logger.debug("Successfully got file from %s" % self.settings().signature_url)
            # test the import without caching it
            try:
                utils.load_signatures(tmpfile.name, cache=False)
            except:
                logger.error("Downloaded signatures failed test load (tempfile = %s)" % tmpfile.name)

            # rewrite the real signature file and import it for real
            f = open(self.settings().signature_path, "w")
            f.write(sigjson.text)
            f.close()

            utils.load_signatures(self.settings().signature_path)
        except:
            utils.log_exc(logger)

    # ==========================================================================

    def dump_vars(self, obj, format: bool = False):
        """
        Dump all known variables related to that object.

        :param obj: The object for which the variables should be dumped.
        :param format: If True the values will align in one column and be pretty printed for cli example.
        :return: A dictionary with all the information which could be collected.
        """
        return obj.dump_vars(format)

    # ==========================================================================

    def auto_add_repos(self):
        """
        Import any repos this server knows about and mirror them. Run ``cobbler reposync`` to apply the changes.
        Credit: Seth Vidal.
        """
        self.log("auto_add_repos")
        try:
            import dnf
        except:
            raise CX("dnf is not installed")

        base = dnf.Base()
        base.read_all_repos()
        basearch = base.conf.substitutions["basearch"]

        for repository in base.repos.iter_enabled():
            auto_name = repository.id + '-' + base.conf.releasever + '-' + basearch

            if self.find_repo(auto_name) is None:
                cobbler_repo = self.new_repo()
                cobbler_repo.set_name(auto_name)
                cobbler_repo.set_breed("yum")
                cobbler_repo.set_arch(basearch)
                cobbler_repo.set_yumopts({})
                cobbler_repo.set_environment({})
                cobbler_repo.set_apt_dists([])
                cobbler_repo.set_apt_components([])
                cobbler_repo.set_comment(repository.name)
                baseurl = repository.baseurl
                metalink = repository.metalink
                mirrorlist = repository.mirrorlist

                if metalink is not None:
                    mirror = metalink
                    mirror_type = "metalink"
                elif mirrorlist is not None:
                    mirror = mirrorlist
                    mirror_type = "mirrorlist"
                elif len(baseurl) > 0:
                    mirror = baseurl[0]
                    mirror_type = "baseurl"

                cobbler_repo.set_mirror(mirror)
                cobbler_repo.set_mirror_type(mirror_type)
                self.log("auto repo adding: %s" % auto_name)
                self.add_repo(cobbler_repo)
            else:
                self.log("auto repo adding: %s - exists" % auto_name)

    # ==========================================================================

    def get_repo_config_for_profile(self, obj) -> str:
        """
        Get the repository configuration for the specified profile

        :param obj: The profile to return the configuration for.
        :return: The repository configuration as a string.
        """
        return self.yumgen.get_yum_config(obj, True)

    def get_repo_config_for_system(self, obj) -> str:
        """
        Get the repository configuration for the specified system.

        :param obj: The system to return the configuration for.
        :return: The repository configuration as a string.
        """
        return self.yumgen.get_yum_config(obj, False)

    # ==========================================================================

    def get_template_file_for_profile(self, obj, path) -> str:
        """
        Get the template for the specified profile.

        :param obj: The object which is related to that template.
        :param path: The path to the template.
        :return: The template as in its string representation.
        """
        template_results = self.tftpgen.write_templates(obj, False, path)
        if path in template_results:
            return template_results[path]
        else:
            return "# template path not found for specified profile"

    def get_template_file_for_system(self, obj, path):
        """
        Get the template for the specified system.

        :param obj: The object which is related to that template.
        :param path: The path to the template.
        :return: The template as in its string representation.
        """
        template_results = self.tftpgen.write_templates(obj, False, path)
        if path in template_results:
            return template_results[path]
        else:
            return "# template path not found for specified system"

    # ==========================================================================

    def generate_gpxe(self, profile, system):
        """
        Generate the gpxe configuration files. The system wins over the profile.

        :param profile: The profile to return the configuration for.
        :param system: The system to return the configuration for.
        :return: The generated configuration file.
        """
        self.log("generate_gpxe")
        if system:
            return self.tftpgen.generate_gpxe("system", system)
        else:
            return self.tftpgen.generate_gpxe("profile", profile)

    # ==========================================================================

    def generate_bootcfg(self, profile, system):
        """
        Generate a boot configuration. The system wins over the profile.

        :param profile: The profile to return the configuration for.
        :param system: The system to return the configuration for.
        :return: The generated configuration file.
        """
        self.log("generate_bootcfg")
        if system:
            return self.tftpgen.generate_bootcfg("system", system)
        else:
            return self.tftpgen.generate_bootcfg("profile", profile)

    # ==========================================================================

    def generate_script(self, profile, system, name):
        """
        Generate an autoinstall script for the specified profile or system. The system wins over the profile.

        :param profile: The profile to generate the script for.
        :param system: The system to generate the script for.
        :param name: The name of the script which should be generated.
        :return: The generated script or an error message.
        """
        self.log("generate_script")
        if system:
            return self.tftpgen.generate_script("system", system, name)
        else:
            return self.tftpgen.generate_script("profile", profile, name)

    # ==========================================================================

    def check(self, logger=None):
        """
        See if all preqs for network booting are valid. This returns a list of strings containing instructions on things
        to correct. An empty list means there is nothing to correct, but that still doesn't mean there are configuration
        errors. This is mainly useful for human admins, who may, for instance, forget to properly set up their TFTP
        servers for PXE, etc.

        :param logger: The logger to audit the removal with.
        :return: None or a list of things to address.
        :rtype: None or list
        """
        self.log("check")
        action_check = check.CobblerCheck(self._collection_mgr, logger=logger)
        return action_check.run()

    # ==========================================================================

    def dlcontent(self, force=False, logger=None):
        """
        Downloads bootloader content that may not be avialable in packages for the given arch, ex: if installing on PPC,
        get syslinux. If installing on x86_64, get elilo, etc.

        :param force: Force the download, although the content may be already downloaded.
        :param logger: The logger to audit the removal with.
        """
        # FIXME: teach code that copies it to grab from the right place
        self.log("dlcontent")
        grabber = dlcontent.ContentDownloader(self._collection_mgr, logger=logger)
        return grabber.run(force)

    # ==========================================================================

    def validate_autoinstall_files(self, logger=None):
        """
        Validate if any of the autoinstallation files are invalid and if yes report this.

        :param logger: The logger to audit the removal with.
        """
        self.log("validate_autoinstall_files")
        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(self._collection_mgr)
        autoinstall_mgr.validate_autoinstall_files(logger)

    # ==========================================================================

    def sync(self, verbose: bool = False, logger=None):
        """
        Take the values currently written to the configuration files in /etc, and /var, and build out the information
        tree found in /tftpboot. Any operations done in the API that have not been saved with serialize() will NOT be
        synchronized with this command.

        :param verbose: If the action should be just logged as needed or (if True) as much verbose as possible.
        :param logger: The logger to audit the removal with.
        """
        self.log("sync")
        sync = self.get_sync(verbose=verbose, logger=logger)
        sync.run()

    # ==========================================================================

    def sync_dhcp(self, verbose: bool = False, logger=None):
        """
        Only build out the DHCP configuration

        :param verbose: If the action should be just logged as needed or (if True) as much verbose as possible.
        :param logger: The logger to audit the removal with.
        """
        self.log("sync_dhcp")
        sync = self.get_sync(verbose=verbose, logger=logger)
        sync.sync_dhcp()
    # ==========================================================================

    def get_sync(self, verbose: bool = False, logger=None):
        """
        Get a Cobbler Sync object which may be executed through the call of ``obj.run()``.

        :param verbose: If the action should be just logged as needed or (if True) as much verbose as possible.
        :param logger: The logger to audit the removal with.
        :return: An instance of the CobblerSync class to execute the sync with.
        """
        self.dhcp = self.get_module_from_file(
            "dhcp",
            "module",
            "managers.isc"
        ).get_manager(self._collection_mgr, logger)
        self.dns = self.get_module_from_file(
            "dns",
            "module",
            "managers.bind"
        ).get_manager(self._collection_mgr, logger)
        self.tftpd = self.get_module_from_file(
            "tftpd",
            "module",
            "managers.in_tftpd",
        ).get_manager(self._collection_mgr, logger)

        return sync.CobblerSync(self._collection_mgr, dhcp=self.dhcp, dns=self.dns, tftpd=self.tftpd, verbose=verbose,
                                logger=logger)

    # ==========================================================================

    def reposync(self, name=None, tries: int = 1, nofail: bool = False, logger=None):
        """
        Take the contents of ``/var/lib/cobbler/repos`` and update them -- or create the initial copy if no contents
        exist yet.

        :param name: The name of the repository to run reposync for.
        :param tries: How many tries should be executed before the action fails.
        :param nofail: If True then the action will fail, otherwise the action will just be skipped. This respects the
                       ``tries`` parameter.
        :param logger: The logger to audit the removal with.
        """
        self.log("reposync", [name])
        action_reposync = reposync.RepoSync(self._collection_mgr, tries=tries, nofail=nofail, logger=logger)
        action_reposync.run(name)

    # ==========================================================================

    def status(self, mode, logger=None):
        """
        Get the status of the current Cobbler instance.

        :param mode: "text" or anything else. Meaning whether the output is thought for the terminal or not.
        :param logger: The logger to audit the removal with.
        :return: The current status of Cobbler.
        """
        statusifier = status.CobblerStatusReport(self._collection_mgr, mode, logger=logger)
        return statusifier.run()

    # ==========================================================================

    def import_tree(self, mirror_url: str, mirror_name: str, network_root=None, autoinstall_file=None, rsync_flags=None,
                    arch=None, breed=None, os_version=None, logger: Optional[clogger.Logger] = None) -> Optional[bool]:
        """
        Automatically import a directory tree full of distribution files.

        :param mirror_url: Can be a string that represents a path, a user@host syntax for SSH, or an rsync:// address.
                           If mirror_url is a filesystem path and mirroring is not desired, set network_root to
                           something like "nfs://path/to/mirror_url/root"
        :param mirror_name: The name of the mirror.
        :param network_root:
        :param autoinstall_file:
        :param rsync_flags:
        :param arch:
        :param breed:
        :param os_version:
        :param logger: The logger to audit the removal with.
        """
        self.log("import_tree", [mirror_url, mirror_name, network_root, autoinstall_file, rsync_flags])

        # Both --path and --name are required arguments.
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

        # We need to mirror (copy) the files.
        self.log("importing from a network location, running rsync to fetch the files first")

        utils.mkdir(path)

        # Prevent rsync from creating the directory name twice if we are copying via rsync.

        if not mirror_url.endswith("/"):
            mirror_url = "%s/" % mirror_url

        if mirror_url.startswith("http://") or mirror_url.startswith("https://") or mirror_url.startswith("ftp://")\
                or mirror_url.startswith("nfs://"):
            # HTTP mirrors are kind of primative. rsync is better. That's why this isn't documented in the manpage and
            # we don't support them.
            # TODO: how about adding recursive FTP as an option?
            self.log("unsupported protocol")
            return False
        else:
            # Good, we're going to use rsync.. We don't use SSH for public mirrors and local files.
            # Presence of user@host syntax means use SSH
            spacer = ""
            if not mirror_url.startswith("rsync://") and not mirror_url.startswith("/"):
                spacer = ' -e "ssh" '
            rsync_cmd = RSYNC_CMD
            if rsync_flags:
                rsync_cmd += " " + rsync_flags

            # If --available-as was specified, limit the files we pull down via rsync to just those that are critical
            # to detecting what the distro is
            if network_root is not None:
                rsync_cmd += " --include-from=/etc/cobbler/import_rsync_whitelist"

            # kick off the rsync now
            utils.run_this(rsync_cmd, (spacer, mirror_url, path), self.logger)

        if network_root is not None:
            # In addition to mirroring, we're going to assume the path is available over http, ftp, and nfs, perhaps on
            # an external filer. Scanning still requires --mirror is a filesystem path, but --available-as marks the
            # network path. This allows users to point the path at a directory containing just the network boot files
            # while the rest of the distro files are available somewhere else.

            # Find the filesystem part of the path, after the server bits, as each distro URL needs to be calculated
            # relative to this.

            if not network_root.endswith("/"):
                network_root += "/"
            valid_roots = ["nfs://", "ftp://", "http://", "https://"]
            for valid_root in valid_roots:
                if network_root.startswith(valid_root):
                    break
            else:
                self.log("Network root given to --available-as must be nfs://, ftp://, http://, or https://")
                return False

            if network_root.startswith("nfs://"):
                try:
                    (a, b, rest) = network_root.split(":", 3)
                except:
                    self.log("Network root given to --available-as is missing a colon, please see the manpage example.")
                    return False

        import_module = self.get_module_by_name("managers.import_signatures")\
            .get_import_manager(self._collection_mgr, logger)
        import_module.run(path, mirror_name, network_root, autoinstall_file, arch, breed, os_version)

    # ==========================================================================

    def acl_config(self, adduser=None, addgroup=None, removeuser=None, removegroup=None, logger=None):
        """
        Configures users/groups to run the Cobbler CLI as non-root.
        Pass in only one option at a time. Powers ``cobbler aclconfig``.

        :param adduser:
        :param addgroup:
        :param removeuser:
        :param removegroup:
        :param logger: The logger to audit the removal with.
        """
        action_acl = acl.AclConfig(self._collection_mgr, logger)
        action_acl.run(
            adduser=adduser,
            addgroup=addgroup,
            removeuser=removeuser,
            removegroup=removegroup
        )

    # ==========================================================================

    def serialize(self):
        """
        Save the cobbler_collections to disk.
        Cobbler internal use only.
        """
        self._collection_mgr.serialize()

    def deserialize(self):
        """
        Load cobbler_collections from disk.
        Cobbler internal use only.
        """
        return self._collection_mgr.deserialize()

    # ==========================================================================

    def get_module_by_name(self, module_name):
        """
        Returns a loaded Cobbler module named 'name', if one exists, else None.
        Cobbler internal use only.

        :param module_name:
        :return:
        """
        return module_loader.get_module_by_name(module_name)

    def get_module_from_file(self, section, name, fallback=None):
        """
        Looks in ``/etc/cobbler/modules.conf`` for a section called 'section' and a key called 'name', and then returns
        the module that corresponds to the value of that key.
        Cobbler internal use only.

        :param section:
        :param name:
        :param fallback:
        :return:
        """
        return module_loader.get_module_from_file(section, name, fallback)

    def get_module_name_from_file(self, section, name, fallback=None):
        """
        Looks up a module the same as ``get_module_from_file`` but returns the module name rather than the module
        itself.

        :param section:
        :param name:
        :param fallback:
        :return:
        """
        return module_loader.get_module_name(section, name, fallback)

    def get_modules_in_category(self, category):
        """
        Returns all modules in a given category, for instance "serializer", or "cli".
        Cobbler internal use only.

        :param category: The category to check.
        :return: The list of modules.
        """
        return module_loader.get_modules_in_category(category)

    # ==========================================================================

    def authenticate(self, user, password):
        """
        (Remote) access control. This depends on the chosen authentication module.
        Cobbler internal use only.

        :param user: The username to check for authentication.
        :param password: The password to check for authentication.
        :return: Whether the action succeeded or not.
        """
        rc = self.authn.authenticate(self, user, password)
        self.log("authenticate", [user, rc])
        return rc

    def authorize(self, user, resource, arg1=None, arg2=None):
        """
        (Remote) access control. This depends on the chosen authorization module.
        Cobbler internal use only.

        :param user: The username to check for authorization.
        :param resource: The type of resource which should be checked for access from the supplied user.
        :param arg1: The actual resource to check for authorization.
        :param arg2: Not known what this parameter does exactly.
        :return: The return code of the action.
        """
        rc = self.authz.authorize(self, user, resource, arg1, arg2)
        self.log("authorize", [user, resource, arg1, arg2, rc], debug=True)
        return rc

    # ==========================================================================

    def build_iso(self, iso=None, profiles=None, systems=None, buildisodir=None, distro=None, standalone=None,
                  airgapped=None, source=None, exclude_dns=None, xorrisofs_opts=None, logger=None):
        """
        Build an iso image which may be network bootable or not.

        :param iso:
        :param profiles:
        :param systems:
        :param buildisodir:
        :param distro:
        :param standalone:
        :param airgapped:
        :param source:
        :param exclude_dns:
        :param xorrisofs_opts:
        :param logger: The logger to audit the removal with.
        """
        builder = buildiso.BuildIso(self._collection_mgr, logger=logger)
        builder.run(
            iso=iso, profiles=profiles, systems=systems, buildisodir=buildisodir, distro=distro, standalone=standalone,
            airgapped=airgapped, source=source, exclude_dns=exclude_dns, xorrisofs_opts=xorrisofs_opts
        )

    # ==========================================================================

    def hardlink(self, logger=None):
        """
        Hardlink all files where this is possible to improve performance.

        :param logger: The logger to audit the removal with.
        :return: The return code of the subprocess call which actually hardlinks the files.
        """
        linker = hardlink.HardLinker(self._collection_mgr, logger=logger)
        return linker.run()

    # ==========================================================================

    def replicate(self, cobbler_master: Optional[str] = None, port: str = "80", distro_patterns: str = "",
                  profile_patterns: str = "", system_patterns: str = "", repo_patterns: str = "",
                  image_patterns: str = "", mgmtclass_patterns=None, package_patterns=None, file_patterns: bool = False,
                  prune: bool = False, omit_data=False, sync_all: bool = False, use_ssl: bool = False, logger=None):
        """
        Pull down data/configs from a remote Cobbler server that is a master to this server.

        :param cobbler_master: The hostname/URL of the other Cobbler server
        :type cobbler_master: str
        :param port: The port to use for the replication task.
        :type port: str
        :param distro_patterns: The pattern of distros which should be synced.
        :param profile_patterns: The pattern of profiles which should be synced.
        :param system_patterns: The pattern of systems which should be synced.
        :param repo_patterns: The pattern of repositories which should be synced.
        :param image_patterns: The pattern of images which should be synced.
        :param mgmtclass_patterns: The pattern of management classes which should be synced.
        :param package_patterns: The pattern of packages which should be synced.
        :param file_patterns: The pattern of files which should be synced.
        :param prune: Whether the object not on the master should be removed or not.
        :type prune: bool
        :param omit_data: If the data downloaded by the current Cobbler server should be rsynced to the destination
                          server.
        :type omit_data: bool
        :param sync_all: This parameter behaves similarly to a dry run argument. If True then everything will executed,
                         if False then only some things are synced.
        :type sync_all: bool
        :param use_ssl: Whether SSL should be used (True) or not (False).
        :type use_ssl: bool
        :param logger: The logger to audit the removal with.
        """
        replicator = replicate.Replicate(self._collection_mgr, logger=logger)
        return replicator.run(
            cobbler_master=cobbler_master, port=port, distro_patterns=distro_patterns,
            profile_patterns=profile_patterns, system_patterns=system_patterns, repo_patterns=repo_patterns,
            image_patterns=image_patterns, mgmtclass_patterns=mgmtclass_patterns, package_patterns=package_patterns,
            file_patterns=file_patterns, prune=prune, omit_data=omit_data, sync_all=sync_all, use_ssl=use_ssl
        )

    # ==========================================================================

    def report(self, report_what=None, report_name=None, report_type=None, report_fields=None, report_noheaders=None):
        """
        Report functionality for Cobbler.

        :param report_what: The object type that should be reported.
        :param report_name: The name of the object which should be possibly reported.
        :param report_type: May be either "text", "csv", "mediawiki", "trac" or "doku".
        :param report_fields: Specify "all" or the fields you want to be reported.
        :param report_noheaders: If the column headers should be included in the output or not.
        """
        reporter = report.Report(self._collection_mgr)
        return reporter.run(report_what=report_what, report_name=report_name, report_type=report_type,
                            report_fields=report_fields, report_noheaders=report_noheaders)

    # ==========================================================================

    def power_system(self, system: str, power_operation: str, user: Optional[str] = None,
                     password: Optional[str] = None, logger=None):
        """
        Power on / power off / get power status /reboot a system.

        :param system: Cobbler system
        :param power_operation: power operation. Valid values: on, off, reboot, status
        :param user: power management user
        :param password: power management password
        :param logger: The logger to audit the removal with.
        :type logger: Logger
        :return: bool if operation was successful
        """

        if power_operation == "on":
            self.power_mgr.power_on(system, user=user, password=password, logger=logger)
        elif power_operation == "off":
            self.power_mgr.power_off(system, user=user, password=password, logger=logger)
        elif power_operation == "status":
            return self.power_mgr.get_power_status(system, user=user, password=password, logger=logger)
        elif power_operation == "reboot":
            self.power_mgr.reboot(system, user=user, password=password, logger=logger)
        else:
            utils.die(self.logger, "invalid power operation '%s', expected on/off/status/reboot" % power_operation)
        return None

    # ==========================================================================

    def clear_logs(self, system, logger=None):
        """
        Clears console and anamon logs for system

        :param system: The system to clear logs of.
        :param logger: The logger to audit the log clearing with.
        """
        log.LogTool(self._collection_mgr, system, self, logger=logger).clear()
