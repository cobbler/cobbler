"""
Config.py is a repository of the Cobbler object model

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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
import weakref

import item_distro as distro
import item_profile as profile
import item_system as system
import item_repo as repo
import item_image as image

import collection_distros as distros
import collection_profiles as profiles
import collection_systems as systems
import collection_repos as repos
import collection_images as images
import modules.serializer_yaml as serializer_yaml

import settings
import serializer

from utils import _


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

       self.api           = api
       self._distros      = distros.Distros(weakref.proxy(self))
       self._repos        = repos.Repos(weakref.proxy(self))
       self._profiles     = profiles.Profiles(weakref.proxy(self))
       self._systems      = systems.Systems(weakref.proxy(self))
       self._images       = images.Images(weakref.proxy(self))
       self._settings     = settings.Settings() # not a true collection
       
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

   def images(self):
       """
       Return the definitive copy of the Images collection
       """
       return self._images

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

   def new_image(self,is_subobject=False):
       """
       Create a new image object...
       """
       return image.Image(weakref.proxy(self),is_subobject=is_subobject)

   def clear(self):
       """
       Forget about all loaded configuration data
       """

       self._distros.clear(),
       self._repos.clear(),
       self._profiles.clear(),
       self._images.clear()
       self._systems.clear(),
       return True

   def serialize(self):
       """
       Save the object hierarchy to disk, using the filenames referenced in each object.
       """
       serializer.serialize(self._distros)
       serializer.serialize(self._repos)
       serializer.serialize(self._profiles)
       serializer.serialize(self._images)
       serializer.serialize(self._systems)
       return True

   def serialize_item(self,collection,item):
       """
       Save item in the collection, resaving the whole collection if needed,
       but ideally just saving the item.
       """
       return serializer.serialize_item(collection,item)
      

   def serialize_delete(self,collection,item):
       """
       Erase item from a storage file, if neccessary rewritting the file.
       """
       return serializer.serialize_delete(collection,item) 

   def deserialize(self):
       """
       Load the object hierachy from disk, using the filenames referenced in each object.
       """
       serializer.deserialize(self._settings)
       serializer.deserialize(self._distros)
       serializer.deserialize(self._repos)
       serializer.deserialize(self._profiles)
       serializer.deserialize(self._images)
       serializer.deserialize(self._systems)
       return True

   def deserialize_raw(self,collection_type):
       """
       Get object data from disk, not objects.
       """
       return serializer.deserialize_raw(collection_type)

   def deserialize_item_raw(self,collection_type,obj_name):
       """
       Get a raw single object.
       """
       return serializer.deserialize_item_raw(collection_type,obj_name)




