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

from past.builtins import cmp
from future import standard_library
standard_library.install_aliases()
from configparser import ConfigParser

pymongo_loaded = False
try:
    from pymongo import Connection
    pymongo_loaded = True
except:
    # FIXME: log message
    pass

import yaml

from cobbler.cexceptions import CX

mongodb = None


def __connect():
    """
    Reads the config file for mongodb and then connects to the mongodb.
    """
    cp = ConfigParser()
    cp.read("/etc/cobbler/mongodb.conf")

    host = cp.get("connection", "host")
    port = int(cp.get("connection", "port"))
    # TODO: detect connection error
    global mongodb
    try:
        mongodb = Connection(host, port)['cobbler']
    except:
        # FIXME: log error
        raise CX("Unable to connect to Mongo database")


def register():
    """
    The mandatory Cobbler module registration hook.
    """
    # FIXME: only run this if enabled.
    if not pymongo_loaded:
        return ""
    return "serializer"


def what():
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
    # FIXME: code to load settings file should not be replicated in all serializer subclasses
    if collection_type == "settings":
        fd = open("/etc/cobbler/settings")
        _dict = yaml.safe_load(fd.read())
        fd.close()
        return _dict
    else:
        __connect()
        collection = mongodb[collection_type]
        return collection.find()


def deserialize(collection, topological=True):
    """
    Load a collection from the database.

    :param collection: The collection to deserialize.
    :param topological: This sorts the returned dict.
    :type topological: bool
    """

    datastruct = deserialize_raw(collection.collection_type())
    if topological and type(datastruct) == list:
        datastruct.sort(__depth_cmp)
    if type(datastruct) == dict:
        collection.from_dict(datastruct)
    elif type(datastruct) == list:
        collection.from_list(datastruct)


def __depth_cmp(item1, item2):
    """
    The comparison function to sort a dict.

    :param item1: The first item to compare.
    :param item2: The second item to compare.
    :return: Weather the first or second item is bigger.
    """
    d1 = item1.get("depth", 1)
    d2 = item2.get("depth", 1)
    return cmp(d1, d2)

# EOF
