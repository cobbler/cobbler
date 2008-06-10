"""
Replicate from a cobbler master.

Copyright 2007-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>
Scott Henson <shenson@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import os.path
import xmlrpclib
import api as cobbler_api
from utils import _

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

        if not os.path.exists(dest_link):
            try:
                os.symlink(base, dest_link)
            except:
                # this shouldn't happen but I've seen it ... debug ...
                print _("- symlink creation failed: %(base)s, %(dest)s") % { "base" : base, "dest" : dest_link }
                
    # -------------------------------------------------------

    def add_distro(self, distro):
        """
        Add a distro that has been found
        """
        #Register the distro
        if os.path.exists(distro['kernel']):
            new_distro = self.api.new_distro()
            new_distro.from_datastruct(distro)
            #create the symlinks
            self.link_distro(new_distro)
            #Add the distro permanently
            self.api.distros().add(new_distro, save=True)
            print 'Added distro %s. Creating Links.' % distro['name']
        else:
            print 'Distro %s not here yet.' % distro['name']

    # -------------------------------------------------------

    def add_profile(self, profile):
        """
        Add a profile that has been found
        """
        #Register the new profile
        new_profile = self.api.new_profile()
        new_profile.from_datastruct(profile)
        self.api.profiles().add(new_profile, save=True)
        print 'Added profile %s.' % profile['name']


    # -------------------------------------------------------

    def check_profile(self, profile):
        """
        Check that a profile belongs to a distro
        """
        profiles = self.api.profiles().to_datastruct()
        if profile not in profiles:
            for distro in self.api.distros().to_datastruct():
                if distro['name'] == profile['name']:
                    return True
        return False


    # -------------------------------------------------------

    def sync_distros(self):
        """
        Sync distros from master
        """
        local_distros = self.api.distros()
        remote_distros = self.remote.get_distros()

        needsync = False
        for distro in remote_distros:
            if distro not in local_distros.to_datastruct():
                print 'Found distro %s.' % distro['name']
                self.add_distro(distro)
                needsync = True
                
        self.call_sync(needsync)


    # -------------------------------------------------------

    def sync_profiles(self):
        """
        Sync profiles from master
        """
        local_profiles = self.api.profiles()
        remote_profiles = self.remote.get_profiles()

        needsync = False
        for profile in remote_profiles:
            if self.check_profile(profile):
                print 'Found profile %s.' % profile['name']
                self.add_profile(profile)
                needsync = True
        self.call_sync(needsync)


    # -------------------------------------------------------

    def call_sync(self, needsync):
        if needsync:
            self.api.sync()
    
    # -------------------------------------------------------

    def run(self, cobbler_master=None):
        """
        Get remote profiles and distros and sync them locally
        """
        if cobbler_master is not None:
            self.uri = 'http://%s/cobbler_api' % cobbler_master
        elif len(self.settings.cobbler_master) > 0:
            self.uri = 'http://%s/cobbler_api' % self.settings.cobbler_master
        else:
            print _('No cobbler master found to replicate from, try --master.')
        if self.uri is not None:
            self.remote =  xmlrpclib.Server(self.uri)
            self.sync_distros()
            self.sync_profiles()

