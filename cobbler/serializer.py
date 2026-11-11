"""
Serializer code for Cobbler
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import contextlib
import logging
import time
from types import ModuleType
from typing import TYPE_CHECKING, Any, Dict, Iterator

from cobbler import utils

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.cobbler_collections.collection import ITEM, Collection


class Serializer:
    """
    Serializer interface that is used to access data in Cobbler independent of the actual data source.
    """

    def __init__(self, api: "CobblerAPI"):
        """
        Constructor that created the state for the object.

        :param api: The CobblerAPI that is used for accessing shared functionality.
        """
        self.api = api
        self.logger = logging.getLogger()
        self.lock_enabled = True
        self.lock_file_location = "/var/lib/cobbler/lock"
        self.storage_module = self.__get_storage_module()
        self.storage_object = self.storage_module.storage_factory(api)

    @contextlib.contextmanager
    def __locked(self) -> Iterator[None]:
        """
        Context manager holding the lock for the duration of the ``with`` block.

        Delegates to ``utils.filelock()`` - the same lock primitive used for sync/quick-sync
        coordination (``cobbler/api.py``, ``cobbler/cobbler_collections/collection.py``) - instead
        of independently ``open()``-ing and ``flock()``-ing the same path. Sharing one reentrant,
        per-thread-aware lock means a thread that already holds this lock for an unrelated reason
        (e.g. a quick-sync call site) can safely call into ``serialize_item()``/``serialize_delete()``
        without a second, independent ``flock()`` attempt on the same file deadlocking the process -
        ``flock()`` locks are owned by the open file description, not the thread, so two genuinely
        separate acquisitions of the same path from the very same thread would otherwise block on
        each other forever. ``utils.filelock()`` itself already guarantees release via ``finally``
        even if the wrapped code raises.

        :return: An iterator that yields exactly once while the lock is held.
        """
        if not self.lock_enabled:
            yield
            return
        with utils.filelock(self.lock_file_location):
            yield

    def __touch_mtime(self) -> None:
        """
        Record the current time as the global modification time of cobbler_collections, allowing
        the API to work more smoothly without a lot of unnecessary reloads.

        Must only be called from inside a ``with self.__locked():`` block, after the write it is
        recording has actually succeeded.
        """
        with open(self.api.mtime_location, "w", encoding="UTF-8") as mtime_fd:
            mtime_fd.write(f"{time.time():f}")

    def serialize(self, collection: "Collection[ITEM]") -> None:
        """
        Save a collection to disk

        :param collection: The collection to serialize.
        """
        with self.__locked():
            self.storage_object.serialize(collection)

    def serialize_item(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        """
        Save a collection item to disk

        :param collection: The Cobbler collection to know the type of the item.
        :param item: The collection item to serialize.
        """
        with self.__locked():
            self.storage_object.serialize_item(collection, item)
            self.__touch_mtime()

    def serialize_delete(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        """
        Delete a collection item from disk

        :param collection: The Cobbler collection to know the type of the item.
        :param item: The collection item to delete.
        """
        with self.__locked():
            self.storage_object.serialize_delete(collection, item)
            self.__touch_mtime()

    def deserialize(
        self, collection: "Collection[ITEM]", topological: bool = True
    ) -> None:
        """
        Load a collection from disk.

        :param collection: The Cobbler collection to know the type of the item.
        :param topological: Sort collection based on each items' depth attribute in the list of collection items. This
                            ensures properly ordered object loading from disk with objects having parent/child
                            relationships, i.e. profiles/subprofiles.  See cobbler/items/abstract/inheritable_item.py
        """
        with self.__locked():
            self.storage_object.deserialize(collection, topological)

    def deserialize_item(self, collection_type: str, uid: str) -> Dict[str, Any]:
        """
        Load a collection item from disk.

        :param collection_type: The collection type to deserialize.
        :param uid: The uid of the collection item to deserialize.
        :return: The deserialized item data as a dict.
        """
        with self.__locked():
            return self.storage_object.deserialize_item(collection_type, uid)

    def __get_storage_module(self) -> ModuleType:
        """
        Look up configured module in the settings

        :returns: A Python module.
        """
        module_name = (
            self.api.settings()
            .modules.get("serializers", {})
            .get("module", "serializers.file")
        )
        if not isinstance(module_name, str):
            module_name = "serializers.file"
        return self.api.get_module_from_file(
            "serializers",
            module_name,
            "serializers.file",
        )
