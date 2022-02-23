"""
Replicate from a Cobbler master.

Copyright 2007-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>
Scott Henson <shenson@redhat.com>

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

import fnmatch
import logging
import os
import xmlrpc.client
from typing import Optional

from cobbler import utils

OBJ_TYPES = ["distro", "profile", "system", "repo", "image", "mgmtclass", "package", "file"]


class Replicate:
    """
    This class contains the magic to replicate a Cobbler instance to another Cobbler instance.
    """

    def __init__(self, api):
        """
        Constructor

        :param api: The API which holds all information available in Cobbler.
        """
        self.settings = api.settings()
        self.api = api
        self.remote = None
        self.uri = None
        self.logger = logging.getLogger()

    def rsync_it(self, from_path, to_path, type: Optional[str] = None):
        """
        Rsync from a source to a destination with the rsync options Cobbler was configured with.

        :param from_path: The source to rsync from.
        :param to_path: The destination to rsync to.
        :param type: If set to "repo" this will take the repo rsync options instead of the global ones.
        """
        from_path = "%s::%s" % (self.master, from_path)
        if type == 'repo':
            cmd = "rsync %s %s %s" % (self.settings.replicate_repo_rsync_options, from_path, to_path)
        else:
            cmd = "rsync %s %s %s" % (self.settings.replicate_rsync_options, from_path, to_path)

        rc = utils.subprocess_call(cmd, shell=True)
        if rc != 0:
            self.logger.info("rsync failed")

    # -------------------------------------------------------

    def remove_objects_not_on_master(self, obj_type):
        """
        Remove objects on this slave which are not on the master.

        :param obj_type: The type of object which should be synchronized.
        """
        locals = utils.lod_to_dod(self.local_data[obj_type], "uid")
        remotes = utils.lod_to_dod(self.remote_data[obj_type], "uid")

        for (luid, ldata) in list(locals.items()):
            if luid not in remotes:
                try:
                    self.logger.info("removing %s %s" % (obj_type, ldata["name"]))
                    self.api.remove_item(obj_type, ldata["name"], recursive=True)
                except Exception:
                    utils.log_exc()

    # -------------------------------------------------------

    def add_objects_not_on_local(self, obj_type):
        """
        Add objects locally which are not present on the slave but on the master.

        :param obj_type:
        """
        locals = utils.lod_to_dod(self.local_data[obj_type], "uid")
        remotes = utils.lod_sort_by_key(self.remote_data[obj_type], "depth")

        for rdata in remotes:

            # do not add the system if it is not on the transfer list
            if not rdata["name"] in self.must_include[obj_type]:
                continue

            if not rdata["uid"] in locals:
                creator = getattr(self.api, "new_%s" % obj_type)
                newobj = creator()
                newobj.from_dict(utils.revert_strip_none(rdata))
                try:
                    self.logger.info("adding %s %s" % (obj_type, rdata["name"]))
                    if not self.api.add_item(obj_type, newobj):
                        self.logger.error("failed to add %s %s" % (obj_type, rdata["name"]))
                except Exception:
                    utils.log_exc()

    # -------------------------------------------------------

    def replace_objects_newer_on_remote(self, obj_type):
        """
        Replace objects which are newer on the local slave then on the remote slave

        :param obj_type: The type of object to synchronize.
        """
        locals = utils.lod_to_dod(self.local_data[obj_type], "uid")
        remotes = utils.lod_to_dod(self.remote_data[obj_type], "uid")

        for (ruid, rdata) in list(remotes.items()):
            # do not add the system if it is not on the transfer list
            if not rdata["name"] in self.must_include[obj_type]:
                continue

            if ruid in locals:
                ldata = locals[ruid]
                if ldata["mtime"] < rdata["mtime"]:

                    if ldata["name"] != rdata["name"]:
                        self.logger.info("removing %s %s" % (obj_type, ldata["name"]))
                        self.api.remove_item(obj_type, ldata["name"], recursive=True)
                    creator = getattr(self.api, "new_%s" % obj_type)
                    newobj = creator()
                    newobj.from_dict(utils.revert_strip_none(rdata))
                    try:
                        self.logger.info("updating %s %s" % (obj_type, rdata["name"]))
                        if not self.api.add_item(obj_type, newobj):
                            self.logger.error("failed to update %s %s" % (obj_type, rdata["name"]))
                    except Exception:
                        utils.log_exc()

    # -------------------------------------------------------

    def replicate_data(self):
        """
        Replicate the local and remote data to each another.

        """
        self.local_data = {}
        self.remote_data = {}
        self.remote_settings = self.remote.get_settings()

        self.logger.info("Querying Both Servers")
        for what in OBJ_TYPES:
            self.remote_data[what] = self.remote.get_items(what)
            self.local_data[what] = self.local.get_items(what)

        self.generate_include_map()

        if self.prune:
            self.logger.info("Removing Objects Not Stored On Master")
            obj_types = OBJ_TYPES[:]
            if len(self.system_patterns) == 0 and "system" in obj_types:
                obj_types.remove("system")
            for what in obj_types:
                self.remove_objects_not_on_master(what)
        else:
            self.logger.info("*NOT* Removing Objects Not Stored On Master")

        if not self.omit_data:
            self.logger.info("Rsyncing distros")
            for distro in list(self.must_include["distro"].keys()):
                if self.must_include["distro"][distro] == 1:
                    self.logger.info("Rsyncing distro %s" % distro)
                    target = self.remote.get_distro(distro)
                    target_webdir = os.path.join(self.remote_settings["webdir"], "distro_mirror")
                    tail = utils.path_tail(target_webdir, target["kernel"])
                    if tail != "":
                        try:
                            # path_tail(a,b) returns something that looks like
                            # an absolute path, but it's really the sub-path
                            # from a that is contained in b. That means we want
                            # the first element of the path
                            dest = os.path.join(self.settings.webdir, "distro_mirror", tail.split("/")[1])
                            self.rsync_it("distro-%s" % target["name"], dest)
                        except:
                            self.logger.error("Failed to rsync distro %s" % distro)
                            continue
                    else:
                        self.logger.warning("Skipping distro %s, as it doesn't appear to live under distro_mirror"
                                            % distro)

            self.logger.info("Rsyncing repos")
            for repo in list(self.must_include["repo"].keys()):
                if self.must_include["repo"][repo] == 1:
                    self.rsync_it("repo-%s" % repo, os.path.join(self.settings.webdir, "repo_mirror", repo), "repo")

            self.logger.info("Rsyncing distro repo configs")
            self.rsync_it("cobbler-distros/config/", os.path.join(self.settings.webdir, "distro_mirror", "config"))
            self.logger.info("Rsyncing automatic installation templates & snippets")
            self.rsync_it("cobbler-templates", self.settings.autoinstall_templates_dir)
            self.rsync_it("cobbler-snippets", self.settings.autoinstall_snippets_dir)
            self.logger.info("Rsyncing triggers")
            self.rsync_it("cobbler-triggers", "/var/lib/cobbler/triggers")
            self.logger.info("Rsyncing scripts")
            self.rsync_it("cobbler-scripts", "/var/lib/cobbler/scripts")
        else:
            self.logger.info("*NOT* Rsyncing Data")

        self.logger.info("Adding Objects Not Stored On Local")
        for what in OBJ_TYPES:
            self.add_objects_not_on_local(what)

        self.logger.info("Updating Objects Newer On Remote")
        for what in OBJ_TYPES:
            self.replace_objects_newer_on_remote(what)

    def link_distros(self):
        """
        Link a distro from its location into the web directory to make it available for usage.
        """
        for distro in self.api.distros():
            self.logger.debug("Linking Distro %s" % distro.name)
            utils.link_distro(self.settings, distro)

    def generate_include_map(self):
        """
        Not known what this exactly does.
        """
        self.remote_names = {}
        self.remote_dict = {}
        self.must_include = {
            "distro": {},
            "profile": {},
            "system": {},
            "image": {},
            "repo": {},
            "mgmtclass": {},
            "package": {},
            "file": {}
        }

        for ot in OBJ_TYPES:
            self.remote_names[ot] = list(utils.lod_to_dod(self.remote_data[ot], "name").keys())
            self.remote_dict[ot] = utils.lod_to_dod(self.remote_data[ot], "name")
            if self.sync_all:
                for names in self.remote_dict[ot]:
                    self.must_include[ot][names] = 1

        self.logger.debug("remote names struct is %s" % self.remote_names)

        if not self.sync_all:
            # include all profiles that are matched by a pattern
            for obj_type in OBJ_TYPES:
                patvar = getattr(self, "%s_patterns" % obj_type)
                self.logger.debug("* Finding Explicit %s Matches" % obj_type)
                for pat in patvar:
                    for remote in self.remote_names[obj_type]:
                        self.logger.debug("?: seeing if %s looks like %s" % (remote, pat))
                        if fnmatch.fnmatch(remote, pat):
                            self.logger.debug("Adding %s for pattern match %s." % (remote, pat))
                            self.must_include[obj_type][remote] = 1

            # include all profiles that systems require whether they are explicitly included or not
            self.logger.debug("* Adding Profiles Required By Systems")
            for sys in list(self.must_include["system"].keys()):
                pro = self.remote_dict["system"][sys].get("profile", "")
                self.logger.debug("?: system %s requires profile %s." % (sys, pro))
                if pro != "":
                    self.logger.debug("Adding profile %s for system %s." % (pro, sys))
                    self.must_include["profile"][pro] = 1

            # include all profiles that subprofiles require whether they are explicitly included or not very deep
            # nesting is possible
            self.logger.debug("* Adding Profiles Required By SubProfiles")
            while True:
                loop_exit = True
                for pro in list(self.must_include["profile"].keys()):
                    parent = self.remote_dict["profile"][pro].get("parent", "")
                    if parent != "":
                        if parent not in self.must_include["profile"]:
                            self.logger.debug("Adding parent profile %s for profile %s." % (parent, pro))
                            self.must_include["profile"][parent] = 1
                            loop_exit = False
                if loop_exit:
                    break

            # require all distros that any profiles in the generated list requires whether they are explicitly included
            # or not
            self.logger.debug("* Adding Distros Required By Profiles")
            for p in list(self.must_include["profile"].keys()):
                distro = self.remote_dict["profile"][p].get("distro", "")
                if not distro == "<<inherit>>" and not distro == "~":
                    self.logger.debug("Adding distro %s for profile %s." % (distro, p))
                    self.must_include["distro"][distro] = 1

            # require any repos that any profiles in the generated list requires whether they are explicitly included
            # or not
            self.logger.debug("* Adding Repos Required By Profiles")
            for p in list(self.must_include["profile"].keys()):
                repos = self.remote_dict["profile"][p].get("repos", [])
                if repos != "<<inherit>>":
                    for r in repos:
                        self.logger.debug("Adding repo %s for profile %s." % (r, p))
                        self.must_include["repo"][r] = 1

            # include all images that systems require whether they are explicitly included or not
            self.logger.debug("* Adding Images Required By Systems")
            for sys in list(self.must_include["system"].keys()):
                img = self.remote_dict["system"][sys].get("image", "")
                self.logger.debug("?: system %s requires image %s." % (sys, img))
                if img != "":
                    self.logger.debug("Adding image %s for system %s." % (img, sys))
                    self.must_include["image"][img] = 1

    # -------------------------------------------------------

    def run(self, cobbler_master=None, port: str = "80", distro_patterns=None, profile_patterns=None,
            system_patterns=None, repo_patterns=None, image_patterns=None, mgmtclass_patterns=None,
            package_patterns=None, file_patterns=None, prune: bool = False, omit_data=False, sync_all: bool = False,
            use_ssl: bool = False):
        """
        Get remote profiles and distros and sync them locally

        :param cobbler_master: The remote url of the master server.
        :param port: The remote port of the master server.
        :param distro_patterns: The pattern of distros to sync.
        :param profile_patterns: The pattern of profiles to sync.
        :param system_patterns: The pattern of systems to sync.
        :param repo_patterns: The pattern of repositories to sync.
        :param image_patterns: The pattern of images to sync.
        :param mgmtclass_patterns: The pattern of management classes to sync.
        :param package_patterns: The pattern of packages to sync.
        :param file_patterns: The pattern of files to sync.
        :param prune: If the local server should be pruned before coping stuff.
        :param omit_data: If the data behind images etc should be omitted or not.
        :param sync_all: If everything should be synced (then the patterns are useless) or not.
        :param use_ssl: If HTTPS or HTTP should be used.
        """

        self.port = str(port)
        self.distro_patterns = distro_patterns.split()
        self.profile_patterns = profile_patterns.split()
        self.system_patterns = system_patterns.split()
        self.repo_patterns = repo_patterns.split()
        self.image_patterns = image_patterns.split()
        self.mgmtclass_patterns = mgmtclass_patterns.split()
        self.package_patterns = package_patterns.split()
        self.file_patterns = file_patterns.split()
        self.omit_data = omit_data
        self.prune = prune
        self.sync_all = sync_all
        self.use_ssl = use_ssl

        if self.use_ssl:
            protocol = 'https'
        else:
            protocol = 'http'

        if cobbler_master is not None:
            self.master = cobbler_master
        elif len(self.settings.cobbler_master) > 0:
            self.master = self.settings.cobbler_master
        else:
            utils.die('No Cobbler master specified, try --master.')

        self.uri = '%s://%s:%s/cobbler_api' % (protocol, self.master, self.port)

        self.logger.info("cobbler_master      = %s" % cobbler_master)
        self.logger.info("port                = %s" % self.port)
        self.logger.info("distro_patterns     = %s" % self.distro_patterns)
        self.logger.info("profile_patterns    = %s" % self.profile_patterns)
        self.logger.info("system_patterns     = %s" % self.system_patterns)
        self.logger.info("repo_patterns       = %s" % self.repo_patterns)
        self.logger.info("image_patterns      = %s" % self.image_patterns)
        self.logger.info("mgmtclass_patterns  = %s" % self.mgmtclass_patterns)
        self.logger.info("package_patterns    = %s" % self.package_patterns)
        self.logger.info("file_patterns       = %s" % self.file_patterns)
        self.logger.info("omit_data           = %s" % self.omit_data)
        self.logger.info("sync_all            = %s" % self.sync_all)
        self.logger.info("use_ssl             = %s" % self.use_ssl)

        self.logger.info("XMLRPC endpoint: %s" % self.uri)
        self.logger.debug("test ALPHA")
        self.remote = xmlrpc.client.Server(self.uri)
        self.logger.debug("test BETA")
        self.remote.ping()
        self.local = xmlrpc.client.Server("http://127.0.0.1:%s/cobbler_api" % self.settings.http_port)
        self.local.ping()

        self.replicate_data()
        self.link_distros()
        self.logger.info("Syncing")
        self.api.sync()
        self.logger.info("Done")
