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
        from_path = "%s:%s" % (self.host, from_path)
        cmd = "rsync -avz %s %s" % (from_path, to_path)
        rc = utils.subprocess_call(self.logger, cmd, shell=True)
        if rc !=0:
            self.logger.info("rsync failed")
    
    # -------------------------------------------------------

    def remove_objects_not_on_master(self, local_obj_data, remote_obj_data, obj_type):
        locals = utils.loh_to_hoh(local_obj_data,"uid")
        remotes = utils.loh_to_hoh(remote_obj_data,"uid")

        for (luid, ldata) in locals.iteritems():
            if not remotes.has_key(luid):
                try:
                    self.logger.info("removing %s %s" % (obj_type, x["name"]))
                    self.api.remove(obj_type, x["name"], recursive=True, logger=self.logger)
                except Exception, e:
                    utils.log_exc(self.logger)

    # -------------------------------------------------------

    def add_objects_not_on_local(self, local_obj_data, remote_obj_data, otype):
         locals = utils.loh_to_hoh(local_obj_data, "uid")
         remotes = utils.loh_sort_by_key(remote_obj_data,"depth")
         remotes2 = utils.loh_sort_by_key(remote_obj_data,"depth")

         for rdata in remotes:
             if not locals.has_key(rdata["uid"]):
                 creator = getattr(self.api, "new_%s" % otype)
                 newobj = creator()
                 newobj.from_datastruct(remotes2[rdata["uid"]])
                 adder = getattr(self.api, "add_%s" % otype)
                 try:
                     self.logger.info("adding %s %s" % (otype, rdata["name"])) 
                     adder(newobj)
                 except Exception, e:
                     utils.log_exc(self.logger)

    # -------------------------------------------------------

    def replace_objects_newer_on_remote(self, local_obj_data, remote_obj_data, otype):
         locals = utils.loh_to_hoh(local_obj_data,"uid")
         remotes = utils.loh_to_hoh(remote_obj_data,"uid")

         for (ruid, rdata) in remotes.iteritems():
             if locals.has_key(ruid):
                 ldata = locals[ruid]
                 if ldata["mtime"] < rdata["mtime"]:
                     creator = getattr(self.api, "new_%s" % otype)
                     newobj = creator()
                     newobj.from_datastruct(rdata)
                     adder = getattr(self.api, "add_%s" % otype)
                     try:
                         self.logger.info("updating %s %s" % (otype, rdata["name"])) 
                         adder(newobj)
                     except Exception, e:
                         utils.log_exc(self.logger)

    # -------------------------------------------------------

    def replicate_data(self):

        obj_types = [ "distro", "profile", "system", "repo", "image" ]
        local_data  = {}    
        remote_data = {}
       
        self.logger.info("Querying Both Servers")
        for what in obj_types:
            remote_data[what] = self.remote.get_items(what)
            local_data[what]  = self.local.get_items(what)

        # FIXME: this should be optional as we might want to maintain local system records
        # and just keep profiles/distros common
        self.logger.info("Removing Objects Not Stored On Master")
        for what in obj_types:
            self.remove_objects_not_on_master(local_data[what], remote_data[what], what) 

        if self.sync_all or self.sync_trees:
            self.logger.info("Rsyncing Distribution Trees")
            self.rsync_it(os.path.join(self.settings.webdir,"ks_mirror"),self.settings.webdir)

        self.logger.info("Removing Objects Not Stored On Local")
        for what in obj_types:
            self.add_objects_not_on_local(local_data[what], remote_data[what], what)

        self.logger.info("Updating Objects Newer On Remote")
        for what in obj_types:
            self.replace_objects_newer_on_remote(local_data[what], remote_data[what], what)


        #for distro in remote_distros:
        #    self.logger.info("Importing remote distro %s." % distro['name'])
        #    if os.path.exists(distro['kernel']):
        #        remote_mtime = distro['mtime']
        #        if self.should_add_or_replace(distro, "distros"): 
        #            new_distro = self.api.new_distro()
        #            new_distro.from_datastruct(distro)
        #            try:
        #                self.api.add_distro(new_distro)
        #                self.logger.info("Copied distro %s." % distro['name'])
        #            except Exception, e:
        #                utils.log_exc(self.logger)
        #                self.logger.error("Failed to copy distro %s" % distro['name'])
        #        else:
        #            # FIXME: force logic
        #            self.logger.info("Not copying distro %s, sufficiently new mtime" % distro['name'])
        #    else:
        #        self.logger.error("Failed to copy distro %s, content not here yet." % distro['name'])

        if self.sync_all or self.sync_repos:
            self.logger.info("Rsyncing Package Mirrors")
            self.rsync_it(os.path.join(self.settings.webdir,"repo_mirror"),self.settings.webdir)

        if self.sync_all or self.sync_kickstarts:
            self.logger.info("Rsyncing kickstart templates & snippets")
            self.rsync_it("/var/lib/cobbler/kickstarts","/var/lib/cobbler")
            self.rsync_it("/var/lib/cobbler/snippets","/var/lib/cobbler")

        # repos
        # FIXME: check to see if local mirror is here, or if otherwise accessible
        #self.logger.info("Copying Repos")
        #local_repos = self.api.repos()
        #remote_repos = self.remote.get_repos()
        #for repo in remote_repos:
        #    self.logger.info("Importing remote repo %s." % repo['name'])
        #    if self.should_add_or_replace(repo, "repos"): 
        #        new_repo = self.api.new_repo()
        #        new_repo.from_datastruct(repo)
        #        try:
        #            self.api.add_repo(new_repo)
        #            self.logger.info("Copied repo %s." % repo['name'])
        #        except Exception, e:
        #            utils.log_exc(self.logger)
        #            self.logger.error("Failed to copy repo %s." % repo['name'])
        #    else:
        #        self.logger.info("Not copying repo %s, sufficiently new mtime" % repo['name'])

        # profiles
        #self.logger.info("Copying Profiles")
        #local_profiles = self.api.profiles()
        #remote_profiles = self.remote.get_profiles()

        # workaround for profile inheritance, must load in order
        #def __depth_sort(a,b):
        #    return cmp(a["depth"],b["depth"])
        #remote_profiles.sort(__depth_sort)

        #for profile in remote_profiles:
        #    self.logger.info("Importing remote profile %s" % profile['name'])
        #    if self.should_add_or_replace(profile, "profiles"): 
        #        new_profile = self.api.new_profile()
        #        new_profile.from_datastruct(profile)
        #        try:
        #            self.api.add_profile(new_profile)
        #            self.logger.info("Copied profile %s." % profile['name'])
        #        except Exception, e:
        #            utils.log_exc(self.logger)
        #            self.logger.error("Failed to copy profile %s." % profile['name'])
        #    else:
        #        self.logger.info("Not copying profile %s, sufficiently new mtime" % profile['name'])

        # images
        #self.logger.info("Copying Images")
        #remote_images = self.remote.get_images()
        #for image in remote_images:
        #    self.logger.info("Importing remote image %s" % image['name'])
        #    if self.should_add_or_replace(image, "images"): 
        ##        new_image = self.api.new_image()
        #        new_image.from_datastruct(image)
        #        try:
        #            self.api.add_image(new_image)
        #            self.logger.info("Copied image %s." % image['name'])
        #        except Exception, e:
        #            utils.log_exc(self.logger)
        ##            self.logger.info("Failed to copy image %s." % profile['image'])
        #    else:
        #        self.logger.info("Not copying image %s, sufficiently new mtime" % image['name'])

        # systems
        # (optional)
        #if self.include_systems:
        #    self.logger.info("Copying Systems")
        #    local_systems = self.api.systems()
        #    remote_systems = self.remote.get_systems()
        #    for system in remote_systems:
        #        self.logger.info("Importing remote system %s" % system['name'])
        #        if self.should_add_or_replace(system, "systems"): 
        #            new_system = self.api.new_system()
        #            new_system.from_datastruct(system)
        #            try:
        #                self.api.add_system(new_system)
        #                self.logger.info("Copied system %s." % system['name'])
        #            except Exception, e:
        #                utils.log_exc(self.logger)
        #                self.logger.info("Failed to copy system %s" % system['name'])    
        #        else:
        #            self.logger.info("Not copying system %s, sufficiently new mtime" % system['name'])

        if self.sync_all or self.sync_triggers:
            self.logger.info("Rsyncing triggers")
            self.rsync_it("/var/lib/cobbler/triggers","/var/lib/cobbler")

    # -------------------------------------------------------

    def run(self, cobbler_master=None, sync_all=False, sync_kickstarts=False,
                  sync_trees=False, sync_repos=False, sync_triggers=False, include_systems=False):
        """
        Get remote profiles and distros and sync them locally
        """

        self.sync_all        = sync_all
        self.sync_kickstarts = sync_kickstarts
        self.sync_trees      = sync_trees
        self.sync_repos      = sync_repos
        self.sync_triggers   = sync_triggers
        self.include_systems = include_systems

        self.logger.info("cobbler_master = %s" % cobbler_master)
        self.logger.info("sync_all = %s" % sync_all)
        self.logger.info("sync_kickstarts = %s" % sync_kickstarts)
        self.logger.info("sync_trees = %s" % sync_trees)
        self.logger.info("sync_repos = %s" % sync_repos)
        self.logger.info("sync_triggers = %s" % sync_triggers)
        self.logger.info("include_systems = %s" % include_systems)

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
        self.remote =  xmlrpclib.Server(self.uri)
        self.remote.ping()
        self.local  =  xmlrpclib.Server("http://127.0.0.1/cobbler_api")
        self.local.ping()
 
        self.replicate_data()
        self.logger.info("Syncing")
        self.api.sync()
        self.logger.info("Done")
        return True

