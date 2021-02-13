"""
Cobbler's Mongo database based object serializer.
Experimental version.

Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>
James Cammarata <jimi@sngx.net>

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

from configparser import ConfigParser

from cobbler import settings
from cobbler.cexceptions import CX

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ConfigurationError
    pymongo_loaded = True
except ModuleNotFoundError:
    # FIXME: log message
    pymongo_loaded = False

mongodb: MongoClient


def __connect(configfile="/etc/cobbler/mongodb.conf"):
    """
    Reads the config file for mongodb and then connects to the mongodb.
    """
    cp = ConfigParser()
    cp.read(configfile)

    host = cp.get("connection", "host")
    port = int(cp.get("connection", "port"))
    # pylint: disable=global-statement
    global mongodb
    mongodb = MongoClient(host, port)['cobbler']
    try:
        # The ismaster command is cheap and doesn't require auth.
        mongodb.admin.command('ismaster')
    except ConnectionFailure as e:
        # FIXME: log error
        raise CX("Unable to connect to Mongo database or get database \"cobbler\"") from e
    except ConfigurationError as e:
        raise CX("The configuration of the MongoDB connection isn't correct, please check the Cobbler settings.") from e


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    # FIXME: only run this if enabled.
    if not pymongo_loaded:
        return ""
    return "serializer"


def what() -> str:
    """
    Module identification function
    """
    return "serializer/mongodb"


def serialize_item(collection, item):
    """
    Save a collection item to database.

    :param collection: collection
    :param item: collection item
    """

    __connect()
    collection = mongodb[collection.collection_type()]
    data = collection.find_one({'name': item.name})
    if data:
        collection.update({'name': item.name}, item.to_dict())
    else:
        collection.insert(item.to_dict())


def serialize_delete(collection, item):
    """
    Delete a collection item from database.

    :param collection: collection
    :param item: collection item
    """

    __connect()
    collection = mongodb[collection.collection_type()]
    collection.remove({'name': item.name})


def serialize(collection):
    """
    Save a collection to database

    :param collection: collection
    """

    # TODO: error detection
    ctype = collection.collection_type()
    if ctype != "settings":
        for x in collection:
            serialize_item(collection, x)


def deserialize_raw(collection_type):
    """
    Get a collection from mongodb and parse it into an object.

    :param collection_type: The collection type to fetch.
    :return: The first element of the collection requested.
    """
    if collection_type == "settings":
        return settings.read_settings_file()
    else:
        __connect()
        collection = mongodb[collection_type]
        return collection.find()


def deserialize(collection, topological=True):
    """
    Load a collection from the database.

    :param collection: The collection to deserialize.
    :param topological: If the collection list should be sorted by the
                        collection dict depth value or not.
    :type topological: bool
    """

    datastruct = deserialize_raw(collection.collection_type())
    if topological and type(datastruct) == list:
        datastruct.sort(key=lambda x: x["depth"])
    if type(datastruct) == dict:
        collection.from_dict(datastruct)
    elif type(datastruct) == list:
        collection.from_list(datastruct)
