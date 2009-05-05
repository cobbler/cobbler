"""
Replicate from a cobbler master.

Copyright 2007-2008, Red Hat, Inc
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
import sub_process

class Replicate:
    def __init__(self,config):
        """
        Constructor
        """
        self.config   = config
        self.settings = config.settings()
        self.api         = config.api
        self.remote = None
        self.uri = None

    # -------------------------------------------------------

    def link_distro(self, distro):
        """
        Create the distro links
        """
        # find the tree location
        dirname = os.path.dirname(distro.kernel)
        tokens = dirname.split("/")
        tokens = tokens[:-2]
        base = "/".join(tokens)
        dest_link = os.path.join(self.settings.webdir, "links", distro.name)

        # create the links directory only if we are mirroring because with
        # SELinux Apache can't symlink to NFS (without some doing)

        # be sure not to create broken symlinks, base must exist, use --rync-trees to mirror
        if not os.path.exists(dest_link) and os.path.exists(base):
            try:
                os.symlink(base, dest_link)
            except:
                # this shouldn't happen but I've seen it ... debug ...
                print _("- symlink creation failed: %(base)s, %(dest)s") % { "base" : base, "dest" : dest_link }

    # -------------------------------------------------------

    def rsync_it(self,from_path,to_path):
        from_path = "%s:%s" % (self.host, from_path)
        cmd = "rsync -avz %s %s" % (from_path, to_path)
        print _("- %s") % cmd
        rc = sub_process.call(cmd, shell=True, close_fds=True)
        if rc !=0:
            raise CX(_("rsync failed"))
    
    def scp_it(self,from_path,to_path):
        from_path = "%s:%s" % (self.host, from_path)
        cmd = "scp %s %s" % (from_path, to_path)
        print _("- %s") % cmd
        rc = sub_process.call(cmd, shell=True, close_fds=True)
        if rc !=0:
            raise CX(_("scp failed"))

    # -------------------------------------------------------

    def should_add_or_replace(self, remote_data, objtype):
        """
        We only want to transfer objects that have newer mtimes or when
        the object does not otherwise exist.
        """
        # FIXME: logic can be removed with get_*_since
        #remote_name = remote_data["name"]
        #if objtype == "distros":
        #    objdata = self.api.find_distro(remote_name)
        #elif objtype == "profiles":
        #    objdata = self.api.find_profile(remote_name)
        #elif objtype == "systems":
        #    objdata = self.api.find_system(remote_name)
        #elif objtype == "images":
        #    objdata = self.api.find_image(remote_name)
        #3elif objtype == "repos":
        #    objdata = self.api.find_repo(remote_name)
        #elif objtype == "networks":
        #    objdata = self.api.find_network(remote_name)
        #
        #if objdata is None:
        #    return True
        #else:
        #    remote_mtime = remote_data["mtime"]
        #    local_mtime = objdata.mtime
        #    if local_mtime == 0:
        #       # upgrade from much older version
        #       return True
        #    else:
        #      return remote_mtime > local_mtime
        return True

    # -------------------------------------------------------

    def replicate_data(self):
       
        # FIXME: need to replicate network objects
        fh = open("/var/lib/cobbler/.mtime")
        data = fh.read()
        last_edit = float(data)
        fh.close()


        # distros 
        print _("----- Copying Distros")
        local_distros = self.api.distros()
        try:
            remote_distros = self.remote.get_distros_since(last_edit)
        except:
            raise CX(_("Failed to contact remote server"))

        if self.sync_all or self.sync_trees:
            print _("----- Rsyncing Distribution Trees")
            self.rsync_it(os.path.join(self.settings.webdir,"ks_mirror"),self.settings.webdir)

        for distro in remote_distros:
            print _("Importing remote distro %s.") % distro['name']
            if os.path.exists(distro['kernel']):
                remote_mtime = distro['mtime']
                if self.should_add_or_replace(distro, "distros"): 
                    new_distro = self.api.new_distro()
                    new_distro.from_datastruct(distro)
                    try:
                        self.api.add_distro(new_distro)
                        print _("Copied distro %s.") % distro['name']
                    except Exception, e:
                        utils.print_exc(e) 
                        print _("Failed to copy distro %s") % distro['name']
                else:
                    # FIXME: force logic
                    print "Not copying distro %s, sufficiently new mtime" % distro['name']
            else:
                print _("Failed to copy distro %s, content not here yet.") % distro['name']

        if self.sync_all or self.sync_repos:
            print _("----- Rsyncing Package Mirrors")
            self.rsync_it(os.path.join(self.settings.webdir,"repo_mirror"),self.settings.webdir)

        if self.sync_all or self.sync_kickstarts:
            print _("----- Rsyncing kickstart templates & snippets")
            self.scp_it("/etc/cobbler/*.ks","/etc/cobbler")
            self.rsync_it("/var/lib/cobbler/kickstarts","/var/lib/cobbler")
            self.rsync_it("/var/lib/cobbler/snippets","/var/lib/cobbler")

        # repos
        # FIXME: check to see if local mirror is here, or if otherwise accessible
        print _("----- Copying Repos")
        local_repos = self.api.repos()
        remote_repos = self.remote.get_repos_since(last_edit)
        for repo in remote_repos:
            print _("Importing remote repo %s.") % repo['name']
            if self.should_add_or_replace(repo, "repos"): 
                new_repo = self.api.new_repo()
                new_repo.from_datastruct(repo)
                try:
                    self.api.add_repo(new_repo)
                    print _("Copied repo %s.") % repo['name']
                except Exception, e:
                    utils.print_exc(e) 
                    print _("Failed to copy repo %s.") % repo['name']
            else:
                print "Not copying repo %s, sufficiently new mtime" % repo['name']

        # profiles
        print _("----- Copying Profiles")
        local_profiles = self.api.profiles()
        remote_profiles = self.remote.get_profiles_since(last_edit)

        # workaround for profile inheritance, must load in order
        def __depth_sort(a,b):
            return cmp(a["depth"],b["depth"])
        remote_profiles.sort(__depth_sort)

        for profile in remote_profiles:
            print _("Importing remote profile %s" % profile['name'])
            if self.should_add_or_replace(profile, "profiles"): 
                new_profile = self.api.new_profile()
                new_profile.from_datastruct(profile)
                try:
                    self.api.add_profile(new_profile)
                    print _("Copyied profile %s.") % profile['name']
                except Exception, e:
                    utils.print_exc(e)
                    print _("Failed to copy profile %s.") % profile['name']
            else:
                print "Not copying profile %s, sufficiently new mtime" % profile['name']

        # images
        print _("----- Copying Images")
        remote_images = self.remote.get_images_since(last_edit)
        for image in remote_images:
            print _("Importing remote image %s" % image['name'])
            if self.should_add_or_replace(image, "images"): 
                new_image = self.api.new_image()
                new_image.from_datastruct(image)
                try:
                    self.api.add_image(new_image)
                    print _("Copyied image %s.") % image['name']
                except Exception, e:
                    utils.print_exc(e)
                    print _("Failed to copy image %s.") % profile['image']
            else:
                print "Not copying image %s, sufficiently new mtime" % image['name']

        # systems
        # (optional)
        if self.include_systems:
            print _("----- Copying Systems")
            local_systems = self.api.systems()
            remote_systems = self.remote.get_systems_since(last_edit)
            for system in remote_systems:
                print _("Importing remote system %s" % system['name'])
                if self.should_add_or_replace(system, "systems"): 
                    new_system = self.api.new_system()
                    new_system.from_datastruct(system)
                    try:
                        self.api.add_system(new_system)
                        print _("Copied system %s.") % system['name']
                    except Exception, e:
                        utils.print_exc(e)
                        print _("Failed to copy system %s") % system['name']        
                else:
                    print "Not copying system %s, sufficiently new mtime" % system['name']  

        if self.sync_all or self.sync_triggers:
            print _("----- Rsyncing triggers")
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

        if cobbler_master is not None:
            self.host = cobbler_master
            self.uri = 'http://%s/cobbler_api' % cobbler_master
             
        elif len(self.settings.cobbler_master) > 0:
            self.host = self.settings.cobbler_master
            self.uri = 'http://%s/cobbler_api' % self.settings.cobbler_master
        else:
            raise CX(_('No cobbler master specified, try --master.'))

        print _("XMLRPC endpoint: %s") % self.uri        
        self.remote =  xmlrpclib.Server(self.uri)
        self.replicate_data()
        print _("----- Syncing")
        self.api.sync()
        print _("----- Done")

