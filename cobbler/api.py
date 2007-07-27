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
import action_reposync
import action_status
import action_validate
import sub_process

class BootAPI:

    __shared_state = {}
    has_loaded = False

    def __init__(self):
        """
        Constructor
        """

        self.__dict__ = self.__shared_state
        if not BootAPI.has_loaded:
            BootAPI.has_loaded = True
            self._config = config.Config(self)
            self.deserialize()
            self.__settings = self._config.settings()
            self.sync_flag = self.__settings.minimize_syncs

    def version(self):
        """
        What version is cobbler?
        Currently checks the RPM DB, which is not perfect.
        Will return "?" if not installed.
        """
        cmd = sub_process.Popen("/bin/rpm -q cobbler", stdout=sub_process.PIPE, shell=True)
        result = cmd.communicate()[0].replace("cobbler-","")
        if result.find("not installed") != -1:
            return "?"
        tokens = result[:result.rfind("-")].split(".")
        return int(tokens[0]) + 0.1 * int(tokens[1]) + 0.001 * int(tokens[2])


    def clear(self):
        """
        Forget about current list of profiles, distros, and systems
        """
        return self._config.clear()

    def __cmp(self,a,b):
        return cmp(a.name,b.name)

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

    def repos(self):
        """
        Return the current list of repos
        """
        return self._config.repos()

    def settings(self):
        """
        Return the application configuration
        """
        return self._config.settings()

    def new_system(self,is_subobject=False):
        """
        Return a blank, unconfigured system, unattached to a collection
        """
        return self._config.new_system(is_subobject=is_subobject)

    def new_distro(self,is_subobject=False):
        """
        Create a blank, unconfigured distro, unattached to a collection.
        """
        return self._config.new_distro(is_subobject=is_subobject)


    def new_profile(self,is_subobject=False):
        """
        Create a blank, unconfigured profile, unattached to a collection
        """
        return self._config.new_profile(is_subobject=is_subobject)

    def new_repo(self,is_subobject=False):
        """
        Create a blank, unconfigured repo, unattached to a collection
        """
        return self._config.new_repo(is_subobject=is_subobject)

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

    def validateks(self):
        """
        Use ksvalidator (from pykickstart, if available) to determine
        whether the cobbler kickstarts are going to be (likely) well
        accepted by Anaconda.  Presence of an error does not indicate
        the kickstart is bad, only that the possibility exists.  ksvalidator
        is not available on all platforms and can not detect "future"
        kickstart format correctness.
        """
        validator = action_validate.Validate(self._config)
        return validator.run()

    def sync(self):
        """
        Take the values currently written to the configuration files in
        /etc, and /var, and build out the information tree found in
        /tftpboot.  Any operations done in the API that have not been
        saved with serialize() will NOT be synchronized with this command.
        """
        sync = action_sync.BootSync(self._config)
        return sync.run()

    def reposync(self):
        """
        Take the contents of /var/lib/cobbler/repos and update them --
        or create the initial copy if no contents exist yet.
        """
        reposync = action_reposync.RepoSync(self._config)
        return reposync.run()

    def enchant(self,address,profile,systemdef,is_virt):
        """
        Re-kickstart a running system.
        Either profile or systemdef should be a name of a
        profile or system definition, the other should be None.  address is an
        address reachable by SSH.
        """
        enchanter = action_enchant.Enchant(self._config,address,profile,systemdef,is_virt)
        return enchanter.run()

    def status(self,mode):
        statusifier = action_status.BootStatusReport(self._config, mode)
        return statusifier.run()

    def import_tree(self,mirror_url,mirror_name):
        """
        Automatically import a directory tree full of distribution files.
        mirror_url can be a string that represents a path, a user@host syntax for SSH, or an rsync:// address
        """
        importer = action_import.Importer(self, self._config, mirror_url, mirror_name)
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

if __name__ == "__main__":
    api = BootAPI()
    print api.version()



