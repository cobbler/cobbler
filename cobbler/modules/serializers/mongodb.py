"""
Cobbler's Mongo database based object serializer.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>
# SPDX-FileCopyrightText: James Cammarata <jimi@sngx.net>
import logging
from typing import Optional

from cobbler import settings
from cobbler.cexceptions import CX
from cobbler.modules.serializers import StorageBase

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ConfigurationError

    PYMONGO_LOADED = True
except ModuleNotFoundError:
    # FIXME: log message
    PYMONGO_LOADED = False


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

    def __init__(self, api):
        super().__init__(api)
        self.logger = logging.getLogger()
        self.mongodb: Optional[MongoClient] = None
        self.mongodb_database = None
        self.database_name = "cobbler"
        self.__connect()

    def __connect(self):
        """
        Reads the config file for mongodb and then connects to the mongodb.
        """
        host = self.api.settings().mongodb.get("host", "localhost")
        port = self.api.settings().mongodb.get("port", 27017)
        # TODO: Make database name configurable in settings
        # TODO: Make authentication configurable
        self.mongodb = MongoClient(host, port)
        try:
            # The ismaster command is cheap and doesn't require auth.
            self.mongodb.admin.command("ping")
        except ConnectionFailure as error:
            raise CX("Unable to connect to Mongo database.") from error
        except ConfigurationError as error:
            raise CX(
                "The configuration of the MongoDB connection isn't correct, please check the Cobbler settings."
            ) from error
        if self.database_name not in self.mongodb.list_database_names():
            self.logger.info(
                'Database with name "%s" was not found and will be created.',
                self.database_name,
            )
        self.mongodb_database = self.mongodb["cobbler"]

    def serialize_item(self, collection, item):
        collection = self.mongodb_database[collection.collection_type()]
        data = collection.find_one({"name": item.name})
        if data:
            collection.replace_one({"name": item.name}, item.serialize())
        else:
            collection.insert_one(item.serialize())

    def serialize_delete(self, collection, item):
        collection = self.mongodb_database[collection.collection_type()]
        collection.delete_one({"name": item.name})

    def serialize(self, collection):
        # TODO: error detection
        ctype = collection.collection_type()
        if ctype != "settings":
            for item in collection:
                self.serialize_item(collection, item)

    def deserialize_raw(self, collection_type: str):
        if collection_type == "settings":
            return settings.read_settings_file()

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
            result["inmemory"] = not lazy_start
            results.append(result)
        return results

    def deserialize(self, collection, topological: bool = True):
        datastruct = self.deserialize_raw(collection.collection_type())
        if topological and isinstance(datastruct, list):
            datastruct.sort(key=lambda x: x.get("depth", 1))
        if isinstance(datastruct, dict):
            collection.from_dict(datastruct)
        elif isinstance(datastruct, list):
            collection.from_list(datastruct)

    def deserialize_item(self, collection_type: str, name: str) -> dict:
        """
        Get a collection item from database.

        :param collection_type: The collection type to fetch.
        :param name: collection Item name
        :return: Dictionary of the collection item.
        """
        mongodb_collection = self.mongodb_database[collection_type]
        result = mongodb_collection.find_one({"name": name})
        if result is None:
            raise CX(
                f"Item {name} of collection {collection_type} was not found in MongoDB database {self.database_name}!"
            )
        self._remove_id(result)
        result["inmemory"] = True
        return result

    @staticmethod
    def _remove_id(_dict: dict):
        if "_id" in _dict:
            _dict.pop("_id")


def storage_factory(api):
    """
    TODO
    """
    return MongoDBSerializer(api)
