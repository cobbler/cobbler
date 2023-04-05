"""
Cobbler's Mongo database based object serializer.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>
# SPDX-FileCopyrightText: James Cammarata <jimi@sngx.net>

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional

from cobbler import settings
from cobbler.cexceptions import CX
from cobbler.modules.serializers import StorageBase

if TYPE_CHECKING:
    from pymongo.database import Database

    from cobbler.api import CobblerAPI
    from cobbler.cobbler_collections.collection import ITEM, Collection

try:
    from pymongo.errors import ConfigurationError, ConnectionFailure
    from pymongo.mongo_client import MongoClient

    PYMONGO_LOADED = True
except ModuleNotFoundError:
    # FIXME: log message
    # This is a constant! pyright just doesn't understand it.
    PYMONGO_LOADED = False  # type: ignore


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    # FIXME: only run this if enabled.
    if not PYMONGO_LOADED:
        return ""
    return "serializer"


def what() -> str:
    """
    Module identification function
    """
    return "serializer/mongodb"


class MongoDBSerializer(StorageBase):
    """
    TODO
    """

    def __init__(self, api: "CobblerAPI"):
        super().__init__(api)
        self.logger = logging.getLogger()
        self.mongodb: Optional[MongoClient[Mapping[str, Any]]] = None
        self.mongodb_database: Optional["Database[Mapping[str, Any]]"] = None
        self.database_name = "cobbler"
        self.__connect()

    def __connect(self) -> None:
        """
        Reads the config file for mongodb and then connects to the mongodb.
        """
        host = self.api.settings().mongodb.get("host", "localhost")
        port = self.api.settings().mongodb.get("port", 27017)
        # TODO: Make database name configurable in settings
        # TODO: Make authentication configurable
        self.mongodb = MongoClient(host, port)  # type: ignore
        try:
            # The ismaster command is cheap and doesn't require auth.
            self.mongodb.admin.command("ping")  # type: ignore
        except ConnectionFailure as error:
            raise CX("Unable to connect to Mongo database.") from error
        except ConfigurationError as error:
            raise CX(
                "The configuration of the MongoDB connection isn't correct, please check the Cobbler settings."
            ) from error
        if self.database_name not in self.mongodb.list_database_names():  # type: ignore
            self.logger.info(
                'Database with name "%s" was not found and will be created.',
                self.database_name,
            )
        self.mongodb_database = self.mongodb["cobbler"]  # type: ignore

    def serialize_item(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        if self.mongodb_database is None:
            raise ValueError("Database not available!")
        mongodb_collection = self.mongodb_database[collection.collection_type()]
        data = mongodb_collection.find_one({"name": item.name})
        if data:
            mongodb_collection.replace_one({"name": item.name}, item.serialize())  # type: ignore
        else:
            mongodb_collection.insert_one(item.serialize())  # type: ignore

    def serialize_delete(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        if self.mongodb_database is None:
            raise ValueError("Database not available!")
        mongodb_collection = self.mongodb_database[collection.collection_type()]
        mongodb_collection.delete_one({"name": item.name})  # type: ignore

    def serialize(self, collection: "Collection[ITEM]") -> None:
        # TODO: error detection
        ctype = collection.collection_type()
        if ctype != "settings":
            for item in collection:
                self.serialize_item(collection, item)

    def deserialize_raw(self, collection_type: str) -> List[Dict[str, Any]]:
        if collection_type == "settings":
            return settings.read_settings_file()  # type: ignore

        if self.mongodb_database is None:
            raise ValueError("Database not available!")

        results = []
        projection = None
        collection = self.mongodb_database[collection_type]
        lazy_start = self.api.settings().lazy_start
        if lazy_start:
            projection = ["name"]

        # pymongo.cursor.Cursor
        cursor = collection.find(projection=projection)
        for result in cursor:
            self._remove_id(result)
            result["inmemory"] = not lazy_start  # type: ignore
            results.append(result)  # type: ignore
        return results  # type: ignore

    def deserialize(self, collection: "Collection[ITEM]", topological: bool = True):
        datastruct = self.deserialize_raw(collection.collection_type())
        if topological and isinstance(datastruct, list):  # type: ignore
            datastruct.sort(key=lambda x: x.get("depth", 1))
        if isinstance(datastruct, dict):
            # This is currently the corner case for the settings type.
            collection.from_dict(datastruct)  # type: ignore
        elif isinstance(datastruct, list):  # type: ignore
            collection.from_list(datastruct)

    def deserialize_item(self, collection_type: str, name: str) -> Dict[str, Any]:
        """
        Get a collection item from database.

        :param collection_type: The collection type to fetch.
        :param name: collection Item name
        :return: Dictionary of the collection item.
        """
        if self.mongodb_database is None:
            raise ValueError("Database not available!")

        mongodb_collection = self.mongodb_database[collection_type]
        result = mongodb_collection.find_one({"name": name})
        if result is None:
            raise CX(
                f"Item {name} of collection {collection_type} was not found in MongoDB database {self.database_name}!"
            )
        self._remove_id(result)
        result["inmemory"] = True  # type: ignore
        return result  # type: ignore

    @staticmethod
    def _remove_id(_dict: Mapping[str, Any]):
        if "_id" in _dict:
            _dict.pop("_id")  # type: ignore


def storage_factory(api: "CobblerAPI") -> MongoDBSerializer:
    """
    TODO
    """
    return MongoDBSerializer(api)
