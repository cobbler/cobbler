"""
Serializer code for Cobbler
Now adapted to support different storage backends
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import fcntl
import os
import sys
import time
import traceback

LOCK_ENABLED = True
LOCK_HANDLE = None
LOCKFILE_LOCATION = "/var/lib/cobbler/lock"


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
            if not os.path.exists(LOCKFILE_LOCATION):
                fd = open(LOCKFILE_LOCATION, "w+")
                fd.close()
            LOCK_HANDLE = open(LOCKFILE_LOCATION, "r")
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
        fd = open("/var/lib/cobbler/.mtime", "w")
        fd.write("%f" % time.time())
        fd.close()
    if LOCK_ENABLED:
        LOCK_HANDLE = open(LOCKFILE_LOCATION, "r")
        fcntl.flock(LOCK_HANDLE.fileno(), fcntl.LOCK_UN)
        LOCK_HANDLE.close()


def serialize(api, collection):
    """
    Save a collection to disk

    :param api: CobblerAPI
    :param collection: The collection to serialize.
    """

    __grab_lock()
    storage_module = __get_storage_module(api)
    storage_module.serialize(collection)
    __release_lock()


def serialize_item(api, collection, item):
    """
    Save a collection item to disk

    :param api: CobblerAPI
    :param collection: The Cobbler collection to know the type of the item.
    :param item: The collection item to serialize.
    """

    __grab_lock()
    storage_module = __get_storage_module(api)
    storage_module.serialize_item(collection, item)
    __release_lock(with_changes=True)


def serialize_delete(api, collection, item):
    """
    Delete a collection item from disk

    :param api: CobblerAPI
    :param collection: The Cobbler collection to know the type of the item.
    :param item: The collection item to delete.
    """

    __grab_lock()
    storage_module = __get_storage_module(api)
    storage_module.serialize_delete(collection, item)
    __release_lock(with_changes=True)


def deserialize(api, collection, topological: bool = True):
    """
    Load a collection from disk.

    :param api: CobblerAPI
    :param collection: The Cobbler collection to know the type of the item.
    :param topological: Sort collection based on each items' depth attribute
                        in the list of collection items.  This ensures
                        properly ordered object loading from disk with
                        objects having parent/child relationships, i.e.
                        profiles/subprofiles.  See cobbler/items/item.py
    """
    __grab_lock()
    storage_module = __get_storage_module(api)
    storage_module.deserialize(collection, topological)
    __release_lock()


def __get_storage_module(api):
    """
    Look up configured module in the settings

    :param api: CobblerAPI
    :returns: A Python module.
    """
    return api.get_module_from_file(
        "serializers",
        api.settings().modules.get("serializers", {}).get("module"),
        "serializers.file",
    )
