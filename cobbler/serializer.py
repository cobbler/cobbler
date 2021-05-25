"""
Serializer code for Cobbler
Now adapted to support different storage backends

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

import fcntl
import os
import sys
import time
import traceback

from cobbler import module_loader

LOCK_ENABLED = True
LOCK_HANDLE = None


def handler(num, frame):
    print("Ctrl-C not allowed during writes. Please wait.", file=sys.stderr)
    return True


def __grab_lock():
    """
    Dual purpose locking:
    (A) flock to avoid multiple process access
    (B) block signal handler to avoid ctrl+c while writing YAML
    """
    try:
        if LOCK_ENABLED:
            if not os.path.exists("/var/lib/cobbler/lock"):
                fd = open("/var/lib/cobbler/lock", "w+")
                fd.close()
            LOCK_HANDLE = open("/var/lib/cobbler/lock", "r")
            fcntl.flock(LOCK_HANDLE.fileno(), fcntl.LOCK_EX)
    except:
        # this is pretty much FATAL, avoid corruption and quit now.
        traceback.print_exc()
        sys.exit(7)


def __release_lock(with_changes=False):
    if with_changes:
        # this file is used to know the time of last modification on cobbler_collections
        # was made -- allowing the API to work more smoothly without
        # a lot of unneccessary reloads.
        fd = open("/var/lib/cobbler/.mtime", 'w')
        fd.write("%f" % time.time())
        fd.close()
    if LOCK_ENABLED:
        LOCK_HANDLE = open("/var/lib/cobbler/lock", "r")
        fcntl.flock(LOCK_HANDLE.fileno(), fcntl.LOCK_UN)
        LOCK_HANDLE.close()


def serialize(collection):
    """
    Save a collection to disk

    :param collection: The collection to serialize.
    """

    __grab_lock()
    storage_module = __get_storage_module(collection.collection_type())
    storage_module.serialize(collection)
    __release_lock()


def serialize_item(collection, item):
    """
    Save a collection item to disk

    :param collection: The Cobbler collection to know the type of the item.
    :param item: The collection item to serialize.
    """

    __grab_lock()
    storage_module = __get_storage_module(collection.collection_type())
    storage_module.serialize_item(collection, item)
    __release_lock(with_changes=True)


def serialize_delete(collection, item):
    """
    Delete a collection item from disk

    :param collection: The Cobbler collection to know the type of the item.
    :param item: The collection item to delete.
    """

    __grab_lock()
    storage_module = __get_storage_module(collection.collection_type())
    storage_module.serialize_delete(collection, item)
    __release_lock(with_changes=True)


def deserialize(collection, topological: bool = True):
    """
    Load a collection from disk.

    :param collection: The Cobbler collection to know the type of the item.
    :param topological: Sort collection based on each items' depth attribute
                        in the list of collection items.  This ensures
                        properly ordered object loading from disk with
                        objects having parent/child relationships, i.e.
                        profiles/subprofiles.  See cobbler/items/item.py
    """
    __grab_lock()
    storage_module = __get_storage_module(collection.collection_type())
    storage_module.deserialize(collection, topological)
    __release_lock()


def __get_storage_module(collection_type):
    """
    Look up serializer in /etc/cobbler/modules.conf

    :param collection_type: str
    :returns: A Python module.
    """
    return module_loader.get_module_from_file("serializers", collection_type, "serializers.file")
