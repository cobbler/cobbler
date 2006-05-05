"""
python API module for BootConf
see source for bootconf.py for a good API reference

Michael DeHaan <mdehaan@redhat.com>
"""

import exceptions
import os
import traceback

import config
import util
import sync
import check
from msg import *

class BootAPI:


    def __init__(self):
       """
       Constructor...
       """
       # if the file already exists, load real data now
       try:
           if config.files_exist():
              config.deserialize()
       except Exception, e:
           # parse errors, attempt to recover
           print runtime.last_error()
           if runtime.last_error() == m("parse_error"):
               # it's bad, raise it so we can croak
               raise Exception, "parse_error"
           try:
               config.serialize()
           except:
               # it's bad, raise it so we can croak
               traceback.print_exc()
               raise Exception, "parse_error2"
       if not config.files_exist():
           config.serialize()


    def clear(self):
       """
       Forget about current list of profiles, distros, and systems
       """
       config.clear()


    def get_systems(self):
       """
       Return the current list of systems
       """
       return config.get_systems()


    def get_profiles(self):
       """
       Return the current list of profiles
       """
       return config.get_profiles()


    def get_distros(self):
       """
       Return the current list of distributions
       """
       return config.get_distros()


    def new_system(self):
       """
       Return a blank, unconfigured system, unattached to a collection
       """
       return system.System(self,None)


    def new_distro(self):
       """
       Create a blank, unconfigured distro, unattached to a collection.
       """
       return distro.Distro(self,None)


    def new_profile(self):
       """
       Create a blank, unconfigured profile, unattached to a collection
       """
       return profile.Profile(self,None)


    def check(self):
       """
       See if all preqs for network booting are valid.  This returns
       a list of strings containing instructions on things to correct.
       An empty list means there is nothing to correct, but that still
       doesn't mean there are configuration errors.  This is mainly useful
       for human admins, who may, for instance, forget to properly set up
       their TFTP servers for PXE, etc.
       """
       return check.bootcheck().run()


    def sync(self,dry_run=True):
       """
       Take the values currently written to the configuration files in
       /etc, and /var, and build out the information tree found in
       /tftpboot.  Any operations done in the API that have not been
       saved with serialize() will NOT be synchronized with this command.
       """
       config.deserialize();
       return sync.bootsync(self).sync(dry_run)


    def serialize(self):
       """
       Save the config file(s) to disk.
       """
       config.serialize()

    def deserialize(self):
       """
       Load the current configuration from config file(s)
       """
       config.deserialize()

