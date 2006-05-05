"""
Config.py is a repository of the Cobbler object model
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
       # manage a definitive copy of all data collections with weakrefs
       # back here so they can understand each other
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
       return self._distros

   def profiles(self):
       return self._profiles

   def systems(self):
       return self._systems

   def settings(self):
       return self._settings

   def new_distro(self):
       return distro.Distro(weakref.proxy(self))

   def new_system(self):
       return system.System(weakref.proxy(self))

   def new_profile(self):
       return profile.Profile(weakref.proxy(self))

   def clear(self):
       for x in self._classes:
          x.clear()

   def file_check(self):
       for x in self._classes:
          if not os.path.exists(x.filename()):
              serializer.serialize(x)

   def serialize(self):
       for x in self._classes:
          serializer.serialize(x)

   def deserialize(self):
       for x in self._classes:
          serializer.deserialize(x)

