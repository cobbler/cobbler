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
    TODO
    """

    def __init__(self, api: "CobblerAPI"):
        self.api = api

    def serialize_item(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        """
        Save a collection item to database.

        :param collection: collection
        :param item: collection item
        """
        raise NotImplementedError(
            "The implementation for the configured serializer is missing!"
        )

    def serialize_delete(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        """
        Delete a collection item from database.

        :param collection: collection
        :param item: collection item
        """
        raise NotImplementedError(
            "The implementation for the configured serializer is missing!"
        )

    def serialize(self, collection: "Collection[ITEM]") -> None:
        """
        Save a collection to database

        :param collection: collection
        """
        raise NotImplementedError(
            "The implementation for the configured serializer is missing!"
        )

    def deserialize_raw(self, collection_type: str) -> List[Dict[str, Any]]:
        """
        Get a collection from mongodb and parse it into an object.

        :param collection_type: The collection type to fetch.
        :return: The first element of the collection requested.
        """
        raise NotImplementedError(
            "The implementation for the configured serializer is missing!"
        )

    def deserialize(
        self, collection: "Collection[ITEM]", topological: bool = True
    ) -> None:
        """
        Load a collection from the database.

        :param collection: The collection to deserialize.
        :param topological: If the collection list should be sorted by the collection dict depth value or not.
        """
        raise NotImplementedError(
            "The implementation for the configured serializer is missing!"
        )

    def deserialize_item(self, collection_type: str, name: str) -> Dict[str, Any]:
        """
        Get a collection item from database and parse it into an object.

        :param collection_type: The collection type to fetch.
        :param item: collection item
        :param topological: If the collection list should be sorted by the collection dict depth value or not.
        :return: The first element of the collection requested.
        """
        raise NotImplementedError(
            "The implementation for the configured serializer is missing!"
        )


def register() -> str:
    """
    TODO
    """
    return "StorageBase"


def what() -> str:
    """
    TODO
    """
    return "serializer/base"


def storage_factory(api: "CobblerAPI") -> StorageBase:
    """
    TODO
    """
    return StorageBase(api)
