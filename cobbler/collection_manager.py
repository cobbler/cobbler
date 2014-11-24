"""
Repository of the Cobbler object model

Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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

import binascii
import random
import time
import weakref

from cexceptions import CX
import collection_distros as distros
import collection_files as files
import collection_images as images
import collection_mgmtclasses as mgmtclasses
import collection_packages as packages
import collection_profiles as profiles
import collection_repos as repos
import collection_systems as systems
import settings
import serializer


class CollectionManager:

    has_loaded = False
    __shared_state = {}


    def __init__(self, api):
        """
        Constructor.  Manages a definitive copy of all data collections with weakrefs
        pointing back into the class so they can understand each other's contents
        """
        self.__dict__ = CollectionManager.__shared_state
        if not CollectionManager.has_loaded:
            self.__load(api)


    def __load(self, api):
        CollectionManager.has_loaded = True

        self.init_time = time.time()
        self.current_id = 0
        self.api = api
        self._distros = distros.Distros(weakref.proxy(self))
        self._repos = repos.Repos(weakref.proxy(self))
        self._profiles = profiles.Profiles(weakref.proxy(self))
        self._systems = systems.Systems(weakref.proxy(self))
        self._images = images.Images(weakref.proxy(self))
        self._mgmtclasses = mgmtclasses.Mgmtclasses(weakref.proxy(self))
        self._packages = packages.Packages(weakref.proxy(self))
        self._files = files.Files(weakref.proxy(self))
        self._settings = settings.Settings()         # not a true collection

    def generate_uid(self):
        """
        Cobbler itself does not use this GUID's though they are provided
        to allow for easier API linkage with other applications.
        Cobbler uses unique names in each collection as the object id
        aka primary key
        """
        data = "%s%s" % (time.time(), random.uniform(1, 9999999))
        return binascii.b2a_base64(data).replace("=", "").strip()

    def __cmp(self, a, b):
        return cmp(a.name, b.name)

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

    def mgmtclasses(self):
        """
        Return the definitive copy of the Mgmtclasses collection
        """
        return self._mgmtclasses

    def packages(self):
        """
        Return the definitive copy of the Packages collection
        """
        return self._packages

    def files(self):
        """
        Return the definitive copy of the Files collection
        """
        return self._files

    def serialize(self):
        """
        Save all collections to disk
        """

        serializer.serialize(self._distros)
        serializer.serialize(self._repos)
        serializer.serialize(self._profiles)
        serializer.serialize(self._images)
        serializer.serialize(self._systems)
        serializer.serialize(self._mgmtclasses)
        serializer.serialize(self._packages)
        serializer.serialize(self._files)

    def serialize_item(self, collection, item):
        """
        Save a collection item to disk

        @param Collection collection Collection
        @param Item item collection item
        """

        return serializer.serialize_item(collection, item)

    def serialize_delete(self, collection, item):
        """
        Delete a collection item from disk

        @param Collection collection collection
        @param Item item collection item
        """

        return serializer.serialize_delete(collection, item)

    def deserialize(self):
        """
        Load all collections from disk

        @raise CX if there is an error in deserialization
        """

        for collection in (
            self._settings,
            self._distros,
            self._repos,
            self._profiles,
            self._images,
            self._systems,
            self._mgmtclasses,
            self._packages,
            self._files,
        ):
            try:
                serializer.deserialize(collection)
            except Exception as e:
                raise CX("serializer: error loading collection %s: %s. Check /etc/cobbler/modules.conf" % (collection.collection_type(), e))

    def get_items(self, collection_type):
        if collection_type == "distro":
            result = self._distros
        elif collection_type == "profile":
            result = self._profiles
        elif collection_type == "system":
            result = self._systems
        elif collection_type == "repo":
            result = self._repos
        elif collection_type == "image":
            result = self._images
        elif collection_type == "mgmtclass":
            result = self._mgmtclasses
        elif collection_type == "package":
            result = self._packages
        elif collection_type == "file":
            result = self._files
        elif collection_type == "settings":
            result = self._settings
        else:
            raise CX("internal error, collection name %s not supported" % collection_type)
        return result
