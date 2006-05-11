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
import cexceptions

class BootAPI:


    def __init__(self,catch_exceptions=False):
       """
       The API can be invoked in two ways, depending on how it is constructed.
       The catch_exceptions mode will cause any API method to return false
       if any CobblerExceptions were thrown, along with setting 'last_error'.
       The other mode just lets the exceptions pass through, and is the way
       most apps should use the API.  catch_exceptions was added for the test hooks,
       since they are coded to use True/False.
       """
       self._config = config.Config()
       self.catch_exceptions = catch_exceptions
       self.last_error = ""
       self.deserialize()


    def __api_call(self,anonymous):
       if self.catch_exceptions:
           try:
               return anonymous()
           except cexceptions.CobblerException, cobexc:
               self.last_error = str(cobexc)
               return False
       else:
           return anonymous()

    def clear(self):
       """
       Forget about current list of profiles, distros, and systems
       """
       return self.__api_call(lambda: self._config.clear())


    def systems(self):
       """
       Return the current list of systems
       """
       return self.__api_call(lambda: self._config.systems())


    def profiles(self):
       """
       Return the current list of profiles
       """
       return self.__api_call(lambda: self._config.profiles())


    def distros(self):
       """
       Return the current list of distributions
       """
       return self.__api_call(lambda: self._config.distros())

    def settings(self):
       """
       Return the application configuration
       """
       return self.__api_call(lambda: self._config.settings())


    def new_system(self):
       """
       Return a blank, unconfigured system, unattached to a collection
       """
       return self.__api_call(lambda: self._config.new_system())


    def new_distro(self):
       """
       Create a blank, unconfigured distro, unattached to a collection.
       """
       return self.__api_call(lambda: self._config.new_distro())


    def new_profile(self):
       """
       Create a blank, unconfigured profile, unattached to a collection
       """
       return self.__api_call(lambda: self._config.new_profile())

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
       return self.__api_call(lambda: check.run())


    def sync(self,dryrun=True):
       """
       Take the values currently written to the configuration files in
       /etc, and /var, and build out the information tree found in
       /tftpboot.  Any operations done in the API that have not been
       saved with serialize() will NOT be synchronized with this command.
       """
       sync = action_sync.BootSync(self._config)
       return self.__api_call(lambda: sync.run(dryrun=dryrun))


    def serialize(self):
       """
       Save the config file(s) to disk.
       """
       return self.__api_call(lambda: self._config.serialize())

    def deserialize(self):
       """
       Load the current configuration from config file(s)
       """
       return self.__api_call(lambda: self._config.deserialize())

