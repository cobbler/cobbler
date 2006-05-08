"""
Config.py is a repository of the Cobbler object model

Michael DeHaan <mdehaan@redhat.com>
"""

import os
import weakref

import item_distro as distro
import item_profile as profile
import item_system as system

import collection_distros as distros
import collection_profiles as profiles
import collection_systems as systems

import settings
import serializer

class Config:

   def __init__(self):
       """
       Constructor.  Manages a definitive copy of all data collections with weakrefs
       poiting back into the class so they can understand each other's contents
       """
       self._distros      = distros.Distros(weakref.proxy(self))
       self._profiles     = profiles.Profiles(weakref.proxy(self))
       self._systems      = systems.Systems(weakref.proxy(self))
       self._settings     = settings.Settings() # not a true collection
       self._classes = [
          self._distros,
          self._profiles,
          self._systems,
          self._settings,
       ]
       self.file_check()

   def distros(self):
       """
       Return the definitive copy of the Distros collection
       """
       return self._distros

   def profiles(self):
       """
       Return the definitive copy of the Profiles collection
       """
       return self._profiles

   def systems(self):
       """
       Return the definitive copy of the Systems collection
       """
       return self._systems

   def settings(self):
       """
       Return the definitive copy of the application settings
       """
       return self._settings

   def new_distro(self):
       """
       Create a new distro object with a backreference to this object
       """
       return distro.Distro(weakref.proxy(self))

   def new_system(self):
       """
       Create a new system with a backreference to this object
       """
       return system.System(weakref.proxy(self))

   def new_profile(self):
       """
       Create a new profile with a backreference to this object
       """
       return profile.Profile(weakref.proxy(self))

   def clear(self):
       """
       Forget about all loaded configuration data
       """
       for x in self._classes:
          x.clear()
       return True

   def file_check(self):
       """
       Serialize any files that do not yet exist.  This is useful for bringing the
       app up to a working state on first run or if files are deleted.  See api.py
       """
       for x in self._classes:
          if not os.path.exists(x.filename()):
              if not serializer.serialize(x):
                  return False
       return True
       

   def serialize(self):
       """
       Save the object hierarchy to disk, using the filenames referenced in each object.
       """
       for x in self._classes:
          if not serializer.serialize(x):
              return False
       return True

   def deserialize(self):
       """
       Load the object hierachy from disk, using the filenames referenced in each object.
       """
       for x in self._classes:
          if not serializer.deserialize(x):
              return False
       return True



