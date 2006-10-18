"""
python API module for Cobbler
see source for cobbler.py, or pydoc, for example usage.
CLI apps and daemons should import api.py, and no other cobbler code.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import config
import utils
import action_sync
import action_check
import action_enchant
import action_import
import cexceptions

class BootAPI:

    def __init__(self):
        """
        Constructor
        """
        self._config = config.Config()
        self.deserialize()

    def clear(self):
        """
        Forget about current list of profiles, distros, and systems
        """
        return self._config.clear()


    def systems(self):
        """
        Return the current list of systems
        """
        return self._config.systems()


    def profiles(self):
        """
        Return the current list of profiles
        """
        return self._config.profiles()


    def distros(self):
        """
        Return the current list of distributions
        """
        return self._config.distros()

    def settings(self):
        """
        Return the application configuration
        """
        return self._config.settings()


    def new_system(self):
        """
        Return a blank, unconfigured system, unattached to a collection
        """
        return self._config.new_system()


    def new_distro(self):
        """
        Create a blank, unconfigured distro, unattached to a collection.
        """
        return self._config.new_distro()


    def new_profile(self):
        """
        Create a blank, unconfigured profile, unattached to a collection
        """
        return self._config.new_profile()

    def check(self):
        """
        See if all preqs for network booting are valid.  This returns
        a list of strings containing instructions on things to correct.
        An empty list means there is nothing to correct, but that still
        doesn't mean there are configuration errors.  This is mainly useful
        for human admins, who may, for instance, forget to properly set up
        their TFTP servers for PXE, etc.
        """
        check = action_check.BootCheck(self._config)
        return check.run()


    def sync(self,dryrun=True):
        """
        Take the values currently written to the configuration files in
        /etc, and /var, and build out the information tree found in
        /tftpboot.  Any operations done in the API that have not been
        saved with serialize() will NOT be synchronized with this command.
        """
        sync = action_sync.BootSync(self._config)
        return sync.run(dryrun=dryrun)

    def enchant(self,address,profile,systemdef):
        """
        Re-kickstart a running system.
        Either profile or systemdef should be a name of a
        profile or system definition, the other should be None.  address is an
        address reachable by SSH.
        """
        enchant = action_enchant.Enchant(self._config,address,profile,systemdef)
        return enchant.run()

    def import_tree(self,tree_path,mirror_url,mirror_name):
        """
        Automatically import a directory tree full of distribution files.
        Imports either a tree (path) or mirror (ftp/http).
        Mirror support really doesn't exist yet... TBA.
        """
        importer = action_import.Importer(self, self._config, tree_path, mirror_url, mirror_name)
        return importer.run()

    def serialize(self):
        """
        Save the config file(s) to disk.
        """
        return self._config.serialize()

    def deserialize(self):
        """
        Load the current configuration from config file(s)
        """
        return self._config.deserialize()


