"""
Serializer code for Cobbler
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import fcntl
import logging
import os
import pathlib
import sys
import time


class Serializer:
    """
    Serializer interface that is used to access data in Cobbler independent of the actual data source.
    """

    def __init__(self, api):
        """
        Constructor that created the state for the object.

        :param api: The CobblerAPI that is used for accessing shared functionality.
        """
        self.api = api
        self.logger = logging.getLogger()
        self.lock_enabled = True
        self.lock_handle = None
        self.lock_file_location = "/var/lib/cobbler/lock"
        self.storage_module = self.__get_storage_module()
        self.storage_object = self.storage_module.storage_factory(api)

    def __grab_lock(self):
        """
        Dual purpose locking:
        (A) flock to avoid multiple process access
        (B) block signal handler to avoid ctrl+c while writing YAML
        """
        try:
            if self.lock_enabled:
                if not os.path.exists(self.lock_file_location):
                    pathlib.Path(self.lock_file_location).touch()
                self.lock_handle = open(self.lock_file_location, "r", encoding="UTF-8")
                fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_EX)
        except Exception as exception:
            # this is pretty much FATAL, avoid corruption and quit now.
            self.logger.exception("File locking error.", exc_info=exception)
            sys.exit(7)

    def __release_lock(self, with_changes=False):
        """
        Releases the lock on the resource that is currently being written.

        :param with_changes: If this is true the global modification time is being updated. Default is false.
        """
        if with_changes:
            # this file is used to know the time of last modification on cobbler_collections
            # was made -- allowing the API to work more smoothly without
            # a lot of unnecessary reloads.
            with open(self.api.mtime_location, "w", encoding="UTF-8") as mtime_fd:
                mtime_fd.write(f"{time.time():f}")
        if self.lock_enabled:
            self.lock_handle = open(self.lock_file_location, "r", encoding="UTF-8")
            fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_UN)
            self.lock_handle.close()

    def serialize(self, collection):
        """
        Save a collection to disk

        :param collection: The collection to serialize.
        """

        self.__grab_lock()
        self.storage_object.serialize(collection)
        self.__release_lock()

    def serialize_item(self, collection, item):
        """
        Save a collection item to disk

        :param collection: The Cobbler collection to know the type of the item.
        :param item: The collection item to serialize.
        """

        self.__grab_lock()
        self.storage_object.serialize_item(collection, item)
        self.__release_lock(with_changes=True)

    def serialize_delete(self, collection, item):
        """
        Delete a collection item from disk

        :param collection: The Cobbler collection to know the type of the item.
        :param item: The collection item to delete.
        """

        self.__grab_lock()
        self.storage_object.serialize_delete(collection, item)
        self.__release_lock(with_changes=True)

    def deserialize(self, collection, topological: bool = True):
        """
        Load a collection from disk.

        :param collection: The Cobbler collection to know the type of the item.
        :param topological: Sort collection based on each items' depth attribute in the list of collection items. This
                            ensures properly ordered object loading from disk with objects having parent/child
                            relationships, i.e. profiles/subprofiles.  See cobbler/items/item.py
        """
        self.__grab_lock()
        self.storage_object.deserialize(collection, topological)
        self.__release_lock()

    def __get_storage_module(self):
        """
        Look up configured module in the settings

        :returns: A Python module.
        """
        return self.api.get_module_from_file(
            "serializers",
            self.api.settings().modules.get("serializers", {}).get("module"),
            "serializers.file",
        )
