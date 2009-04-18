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
import time
import random
import string
import binascii

import item_distro as distro
import item_profile as profile
import item_system as system
import item_repo as repo
import item_image as image
import item_network as network
import item_userpref as userpref

import collection_distros as distros
import collection_profiles as profiles
import collection_systems as systems
import collection_repos as repos
import collection_images as images
import collection_networks as networks
import collection_userprefs as userprefs
import modules.serializer_yaml as serializer_yaml

import settings
import serializer

from utils import _
from cexceptions import *

class Config:

   has_loaded = False
   __shared_state = {}


   def __init__(self,api):

       """
       Constructor.  Manages a definitive copy of all data collections with weakrefs
       pointing back into the class so they can understand each other's contents
       """

       self.__dict__ = Config.__shared_state
       if not Config.has_loaded:
          self.__load(api)
           

   def __load(self,api):

       Config.has_loaded  = True

       self.init_time     = time.time()
       self.current_id    = 0
       self.api           = api
       self._distros      = distros.Distros(weakref.proxy(self))
       self._repos        = repos.Repos(weakref.proxy(self))
       self._profiles     = profiles.Profiles(weakref.proxy(self))
       self._systems      = systems.Systems(weakref.proxy(self))
       self._images       = images.Images(weakref.proxy(self))
       self._networks     = networks.Networks(weakref.proxy(self))
       self._userprefs    = userprefs.Userprefs(weakref.proxy(self))
       self._settings     = settings.Settings() # not a true collection

   def generate_uid(self):
       """
       Cobbler itself does not use this GUID's though they are provided
       to allow for easier API linkage with other applications.
       Cobbler uses unique names in each collection as the object id
       aka primary key
       """
       data = "%s%s" % (time.time(), random.uniform(1,9999999))
       return binascii.b2a_base64(data).replace("=","").strip()
       
   def generate_random_id(self,length=8):
       """
       Return a random string using ASCII 0..9 and A..z
       """
       return string.join(random.Random().sample(string.letters+string.digits, length),'')

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

   def networks(self):
       """
       Return the definitive copy of the Networks collection
       """
       return self._networks

   def userprefs(self):
       """
       Return the definitive copy of the userprefs collection
       """
       return self._userprefs

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

   def new_network(self,is_subobject=False):
       """
       Create a new network object...
       """
       return network.Network(weakref.proxy(self),is_subobject=is_subobject)

   def new_userpref(self,is_subobject=False):
       """
       Create a new userpref object...
       """
       return userpref.Userpref(weakref.proxy(self),is_subobject=is_subobject)

   def clear(self):
       """
       Forget about all loaded configuration data
       """

       self._distros.clear(),
       self._repos.clear(),
       self._profiles.clear(),
       self._images.clear()
       self._systems.clear(),
       self._networks.clear(),
       self._userprefs.clear(),
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
       serializer.serialize(self._networks)
       serializer.serialize(self._userprefs)
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
       try:
           serializer.deserialize(self._settings)
       except:
           raise CX("/etc/cobbler/settings is not a valid YAML file")
       serializer.deserialize(self._distros)
       serializer.deserialize(self._repos)
       serializer.deserialize(self._profiles)
       serializer.deserialize(self._images)
       serializer.deserialize(self._systems)
       serializer.deserialize(self._networks)
       serializer.deserialize(self._userprefs)
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

   def get_items(self,collection_type):
        if collection_type == "distro":
            result=self._distros
        elif collection_type == "profile":
            result=self._profiles
        elif collection_type == "system":
            result=self._systems
        elif collection_type == "repo":
            result=self._repos
        elif collection_type == "image":
            result=self._images
        elif collection_type == "network":
            result=self._networks
        elif collection_type == "userpref":
            result=self._userprefs
        else:
            raise CX("internal error, collection name %s not supported" % collection_type)
        return result
