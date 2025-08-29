"""
This module contains code to persist the in memory state of Cobbler on a target. The name of the target should be the
name of the Python file. Cobbler is currently only tested against the file serializer.
"""

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.cobbler_collections.collection import ITEM, Collection


class StorageBase:
    """
    Base class for all storage modules. The serializers are responsible for transforming the items from and to the
    serializer representation.
    """

    def __init__(self, api: "CobblerAPI"):
        self.api = api

    def serialize_item(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        """
        Save a collection item to disk

        :param collection: The Cobbler collection to know the type of the item.
        :param item: The collection item to serialize.
        """
        raise NotImplementedError(
            "The implementation for the configured serializer is missing!"
        )

    def serialize_delete(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        """
        Delete a collection item from disk.

        :param collection: collection
        :param item: collection item
        """
        raise NotImplementedError(
            "The implementation for the configured serializer is missing!"
        )

    def serialize(self, collection: "Collection[ITEM]") -> None:
        """
        Save a collection to disk

        :param collection: The collection to serialize.
        """
        raise NotImplementedError(
            "The implementation for the configured serializer is missing!"
        )

    def deserialize_raw(self, collection_type: str) -> List[Dict[str, Any]]:
        """
        Read the collection from the disk.

        :param collection_type: The collection type to read.
        :return: The list of collection dicts.
        """
        raise NotImplementedError(
            "The implementation for the configured serializer is missing!"
        )

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
        raise NotImplementedError(
            "The implementation for the configured serializer is missing!"
        )

    def deserialize_item(self, collection_type: str, uid: str) -> Dict[str, Any]:
        """
        Get a collection item from disk and parse it into an object.

        :param collection_type: The collection type to deserialize.
        :param uid: The collection item uid to deserialize.
        :return: Dictionary of the collection item.
        """
        raise NotImplementedError(
            "The implementation for the configured serializer is missing!"
        )


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "StorageBase"


def what() -> str:
    """
    Module identification function
    """
    return "serializer/base"


def storage_factory(api: "CobblerAPI") -> StorageBase:
    """
    Factory method to allow the serializer interface to instaniate the concrete serializer without knowing which
    serializer is initalized.
    """
    return StorageBase(api)
