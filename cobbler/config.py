"""
Config.py is a repository of the Cobbler object model

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import weakref

import item_distro as distro
import item_profile as profile
import item_system as system
import item_repo as repo

import collection_distros as distros
import collection_profiles as profiles
import collection_systems as systems
import collection_repos as repos
import modules.serializer_yaml as serializer_yaml

import module_loader as loader

import settings
import serializer

from rhpl.translate import _, N_, textdomain, utf8


class Config:

   has_loaded = False
   __shared_state = {}


   def __init__(self,api):

       """
       Constructor.  Manages a definitive copy of all data collections with weakrefs
       pointing back into the class so they can understand each other's contents
       """
       self.__dict__ == Config.__shared_state
       if not Config.has_loaded:
           self.__load(api)
           

   def __load(self,api):

       Config.has_loaded  = True

       self.modules       = loader.load_modules()

       print "DEBUG: You've got modules!: %s" % self.modules

       self.api           = api
       self._distros      = distros.Distros(weakref.proxy(self))
       self._repos        = repos.Repos(weakref.proxy(self))
       self._profiles     = profiles.Profiles(weakref.proxy(self))
       self._systems      = systems.Systems(weakref.proxy(self))
       self._settings     = settings.Settings() # not a true collection
       self._graph_classes = [
          self._distros,
          self._repos,
          self._profiles,
          self._systems
       ]
       # self.file_check()

   def __cmp(self,a,b):
       return cmp(a.name,b.name)

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

   def repos(self):
       """
       Return the definitive copy of the Repos collection
       """
       return self._repos

   def new_distro(self,is_subobject=False):
       """
       Create a new distro object with a backreference to this object
       """
       return distro.Distro(weakref.proxy(self),is_subobject=is_subobject)

   def new_system(self,is_subobject=False):
       """
       Create a new system with a backreference to this object
       """
       return system.System(weakref.proxy(self),is_subobject=is_subobject)

   def new_profile(self,is_subobject=False):
       """
       Create a new profile with a backreference to this object
       """
       return profile.Profile(weakref.proxy(self),is_subobject=is_subobject)

   def new_repo(self,is_subobject=False):
       """
       Create a new mirror to keep track of...
       """
       return repo.Repo(weakref.proxy(self),is_subobject=is_subobject)

   def clear(self):
       """
       Forget about all loaded configuration data
       """
       for x in self._graph_classes:
          x.clear()
       return True

   #def file_check(self):
   #    """
   #    Serialize any files that do not yet exist.  This is useful for bringing the
   #    app up to a working state on first run or if files are deleted.  See api.py
   #    """
   #    for x in self._classes:
   #       if not os.path.exists(x.filename()):
   #           if not serializer.serialize(x):
   #               return False
   #    return True


   def serialize(self):
       """
       Save the object hierarchy to disk, using the filenames referenced in each object.
       """
       if not serializer_yaml.serialize(self._settings):
          return False
       for x in self._graph_classes:
          if not serializer.serialize(x):
              return False
       return True

   def deserialize(self):
       """
       Load the object hierachy from disk, using the filenames referenced in each object.
       """
       if not serializer_yaml.deserialize(self._settings,topological=False):
          return False
       for x in self._graph_classes:
          if not serializer.deserialize(x,topological=True):
              return False
       return True



