"""
python API module for Cobbler
see source for cobbler.py, or pydoc, for example usage.
CLI apps and daemons should import api.py, and no other cobbler code.

All functions return True on success, and generally return False on error.
Exceptions are *not* extended to escape this class, nor should this class
need to do any exception handling.

Michael DeHaan <mdehaan@redhat.com>
"""

import config
import utils
import action_sync
import action_check

_config = config.Config()

class BootAPI:


    def __init__(self):
       """
       Constructor...
       """
       self.deserialize()


    def clear(self):
       """
       Forget about current list of profiles, distros, and systems
       """
       return _config.clear()


    def systems(self):
       """
       Return the current list of systems
       """
       return _config.systems()


    def profiles(self):
       """
       Return the current list of profiles
       """
       return _config.profiles()


    def distros(self):
       """
       Return the current list of distributions
       """
       return _config.distros()


    def new_system(self):
       """
       Return a blank, unconfigured system, unattached to a collection
       """
       return _config.new_system()


    def new_distro(self):
       """
       Create a blank, unconfigured distro, unattached to a collection.
       """
       return _config.new_distro()


    def new_profile(self):
       """
       Create a blank, unconfigured profile, unattached to a collection
       """
       return _config.new_profile()

    def check(self):
       """
       See if all preqs for network booting are valid.  This returns
       a list of strings containing instructions on things to correct.
       An empty list means there is nothing to correct, but that still
       doesn't mean there are configuration errors.  This is mainly useful
       for human admins, who may, for instance, forget to properly set up
       their TFTP servers for PXE, etc.
       """
       return action_check.BootCheck(_config).run()


    def sync(self,dry_run=True):
       """
       Take the values currently written to the configuration files in
       /etc, and /var, and build out the information tree found in
       /tftpboot.  Any operations done in the API that have not been
       saved with serialize() will NOT be synchronized with this command.
       """
       return action_sync.BootSync(_config).sync(dry_run)


    def serialize(self):
       """
       Save the config file(s) to disk.
       """
       return _config.serialize()

    def deserialize(self):
       """
       Load the current configuration from config file(s)
       """
       return _config.deserialize()

    def last_error(self):
       """
       In the event of failure, what went wrong?
       """
       return utils.last_error()

