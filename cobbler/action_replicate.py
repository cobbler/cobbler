"""
Replicate from a cobbler master.

Copyright 2007-2009, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>
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

import os
import os.path
import xmlrpclib
import api as cobbler_api
import utils
from utils import _
from cexceptions import *
import clogger
import fnmatch

OBJ_TYPES = [ "distro", "profile", "system", "repo", "image" ]

class Replicate:

    def __init__(self,config,logger=None):
        """
        Constructor
        """
        self.config   = config
        self.settings = config.settings()
        self.api      = config.api
        self.remote   = None
        self.uri      = None
        if logger is None:
           logger     = clogger.Logger()
        self.logger   = logger

    def rsync_it(self,from_path,to_path):
        from_path = "%s::%s" % (self.host, from_path)
        cmd = "rsync -avz %s %s" % (from_path, to_path)
        rc = utils.subprocess_call(self.logger, cmd, shell=True)
        if rc !=0:
            self.logger.info("rsync failed")

    # -------------------------------------------------------

    def remove_objects_not_on_master(self, obj_type):
        locals = utils.loh_to_hoh(self.local_data[obj_type],"uid")
        remotes = utils.loh_to_hoh(self.remote_data[obj_type],"uid")

        for (luid, ldata) in locals.iteritems():
            if not remotes.has_key(luid):
                try:
                    self.logger.info("removing %s %s" % (obj_type, ldata["name"]))
                    self.api.remove_item(obj_type, ldata["name"], recursive=True, logger=self.logger)
                except Exception, e:
                    utils.log_exc(self.logger)

    # -------------------------------------------------------

    def add_objects_not_on_local(self, obj_type):
         locals   = utils.loh_to_hoh(self.local_data[obj_type], "uid")
         remotes  = utils.loh_sort_by_key(self.remote_data[obj_type],"depth")
         remotes2 = utils.loh_to_hoh(self.remote_data[obj_type],"depth")

         for rdata in remotes:

             # do not add the system if it is not on the transfer list
             if not self.must_include[obj_type].has_key(rdata["name"]):
                 continue

             if not locals.has_key(rdata["uid"]):
                 creator = getattr(self.api, "new_%s" % obj_type)
                 newobj = creator()
                 newobj.from_datastruct(rdata)
                 try:
                     self.logger.info("adding %s %s" % (obj_type, rdata["name"]))
                     self.api.add_item(obj_type, newobj)
                 except Exception, e:
                     utils.log_exc(self.logger)

    # -------------------------------------------------------

    def replace_objects_newer_on_remote(self, otype):
         locals = utils.loh_to_hoh(self.local_data[otype],"uid")
         remotes = utils.loh_to_hoh(self.remote_data[otype],"uid")

         for (ruid, rdata) in remotes.iteritems():

             # do not add the system if it is not on the transfer list
             if not self.must_include[otype].has_key(rdata["name"]):
                 continue

             if locals.has_key(ruid):
                 ldata = locals[ruid]
                 if ldata["mtime"] < rdata["mtime"]:

                     if ldata["name"] != rdata["name"]:
                         self.logger.info("removing %s %s" % (obj_type, ldata["name"]))
                         self.api.remove_item(obj_type, ldata["name"], recursive=True, logger=self.logger)
                     creator = getattr(self.api, "new_%s" % otype)
                     newobj = creator()
                     newobj.from_datastruct(rdata)
                     try:
                         self.logger.info("updating %s %s" % (otype, rdata["name"]))
                         self.api.add_item(otype, newobj)
                     except Exception, e:
                         utils.log_exc(self.logger)

    # -------------------------------------------------------

    def replicate_data(self):

        self.local_data  = {}
        self.remote_data = {}

        self.logger.info("Querying Both Servers")
        for what in OBJ_TYPES:
            self.remote_data[what] = self.remote.get_items(what)
            self.local_data[what]  = self.local.get_items(what)


        self.generate_include_map()

        # FIXME: this should be optional as we might want to maintain local system records
        # and just keep profiles/distros common
        if self.prune:
            self.logger.info("Removing Objects Not Stored On Master")
            for what in OBJ_TYPES:
                self.remove_objects_not_on_master(what)
        else:
            self.logger.info("*NOT* Removing Objects Not Stored On Master")

        if not self.omit_data:
            self.logger.info("Rsyncing distros")
            for distro in self.must_include["distro"].keys():
                if self.must_include["distro"][distro] == 1:
                    distro = self.remote.get_item('distro',distro)
                    if distro["breed"] == 'redhat':
                        dest = distro["kernel"]
                        top = None
                        while top != 'images' and top != '':
                            dest, top = os.path.split(dest)
                        if not dest == os.path.sep and len(dest) > 1:
                            parentdir = os.path.split(dest)[0]
                            if not os.path.isdir(parentdir):
                                os.makedirs(parentdir)
                            self.rsync_it("distro-%s"%distro["name"], dest)
            self.logger.info("Rsyncing repos")
            for repo in self.must_include["repo"].keys():
                if self.must_include["repo"][repo] == 1:
                    self.rsync_it("repo-%s"%repo, os.path.join(self.settings.webdir,"repo_mirror",repo))
            self.logger.info("Rsyncing distro repo configs")
            self.rsync_it("cobbler-distros/config", os.path.join(self.settings.webdir,"ks_mirror"))
            self.logger.info("Rsyncing kickstart templates & snippets")
            self.rsync_it("cobbler-kickstarts","/var/lib/cobbler/kickstarts")
            self.rsync_it("cobbler-snippets","/var/lib/cobbler/snippets")
            self.logger.info("Rsyncing triggers")
            self.rsync_it("cobbler-triggers","/var/lib/cobbler/triggers")
        else:
            self.logger.info("*NOT* Rsyncing Data")

        self.logger.info("Removing Objects Not Stored On Local")
        for what in OBJ_TYPES:
            self.add_objects_not_on_local(what)

        self.logger.info("Updating Objects Newer On Remote")
        for what in OBJ_TYPES:
            self.replace_objects_newer_on_remote(what)


    def generate_include_map(self):

        self.remote_names = {}
        self.remote_dict  = {}
        for ot in OBJ_TYPES:
            self.remote_names[ot] = utils.loh_to_hoh(self.remote_data[ot],"name").keys()
            self.remote_dict[ot]  = utils.loh_to_hoh(self.remote_data[ot],"name")

        self.logger.debug("remote names struct is %s" % self.remote_names)

        self.must_include = {
            "distro"  : {},
            "profile" : {},
            "system"  : {},
            "image"   : {},
            "repo"    : {}
        }

        # include all profiles that are matched by a pattern
        for otype in OBJ_TYPES:
            patvar = getattr(self, "%s_patterns" % otype)
            self.logger.debug("* Finding Explicit %s Matches" % otype)
            for pat in patvar:
                for remote in self.remote_names[otype]:
                    self.logger.debug("?: seeing if %s looks like %s" % (remote,pat))
                    if fnmatch.fnmatch(remote, pat):
                        self.must_include[otype][remote] = 1

        # include all profiles that systems require
        # whether they are explicitly included or not
        self.logger.debug("* Adding Profiles Required By Systems")
        for sys in self.must_include["system"].keys():
            pro = self.remote_dict["system"][sys].get("profile","")
            self.logger.debug("?: requires profile: %s" % pro)
            if pro != "":
               self.must_include["profile"][pro] = 1

        # include all profiles that subprofiles require
        # whether they are explicitly included or not
        # very deep nesting is possible
        self.logger.debug("* Adding Profiles Required By SubProfiles")
        while True:
            loop_exit = True
            for pro in self.must_include["profile"].keys():
                parent = self.remote_dict["profile"][pro].get("parent","")
                if parent != "":
                    if not self.must_include["profile"].has_key(parent):
                        self.must_include["profile"][parent] = 1
                        loop_exit = False
            if loop_exit:
                break

        # require all distros that any profiles in the generated list requires
        # whether they are explicitly included or not
        self.logger.debug("* Adding Distros Required By Profiles")
        for p in self.must_include["profile"].keys():
            distro = self.remote_dict["profile"][p].get("distro","")
            if not distro == "<<inherit>>" and not distro == "~":
                self.logger.info("Adding repo %s for profile %s."%(p, distro))
                self.must_include["distro"][distro] = 1

        # require any repos that any profiles in the generated list requires
        # whether they are explicitly included or not
        self.logger.debug("* Adding Repos Required By Profiles")
        for p in self.must_include["profile"].keys():
            repos = self.remote_dict["profile"][p].get("repos",[])
            for r in repos:
                self.must_include["repo"][r] = 1

        # include all images that systems require
        # whether they are explicitly included or not
        self.logger.debug("* Adding Images Required By Systems")
        for sys in self.must_include["system"].keys():
            img = self.remote_dict["system"][sys].get("image","")
            self.logger.debug("?: requires profile: %s" % pro)
            if img != "":
               self.must_include["image"][img] = 1

        # FIXME: remove debug
        for ot in OBJ_TYPES:
            self.logger.debug("transfer list for %s is %s" % (ot, self.must_include[ot].keys()))

    # -------------------------------------------------------

    def run(self, cobbler_master=None, distro_patterns=None, profile_patterns=None, system_patterns=None, repo_patterns=None, image_patterns=None, prune=False, omit_data=False):
        """
        Get remote profiles and distros and sync them locally
        """

        self.distro_patterns  = distro_patterns.split()
        self.profile_patterns = profile_patterns.split()
        self.system_patterns  = system_patterns.split()
        self.repo_patterns    = repo_patterns.split()
        self.image_patterns   = image_patterns.split()
        self.omit_data        = omit_data
        self.prune            = prune

        self.logger.info("cobbler_master   = %s" % cobbler_master)
        self.logger.info("profile_patterns = %s" % self.profile_patterns)
        self.logger.info("system_patterns  = %s" % self.system_patterns)
        self.logger.info("omit_data        = %s" % self.omit_data)

        if cobbler_master is not None:
            self.logger.info("using CLI defined master")
            self.host = cobbler_master
            self.uri = 'http://%s/cobbler_api' % cobbler_master
        elif len(self.settings.cobbler_master) > 0:
            self.logger.info("using info from master")
            self.host = self.settings.cobbler_master
            self.uri = 'http://%s/cobbler_api' % self.settings.cobbler_master
        else:
            utils.die('No cobbler master specified, try --master.')

        self.logger.info("XMLRPC endpoint: %s" % self.uri)
        self.logger.debug("test ALPHA")
        self.remote =  xmlrpclib.Server(self.uri)
        self.logger.debug("test BETA")
        self.remote.ping()
        self.local  =  xmlrpclib.Server("http://127.0.0.1/cobbler_api")
        self.local.ping()

        self.replicate_data()
        self.logger.info("Syncing")
        self.api.sync()
        self.logger.info("Done")
        return True
