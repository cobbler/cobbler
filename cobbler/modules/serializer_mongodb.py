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

import distutils.sysconfig
import sys

plib = distutils.sysconfig.get_python_lib()
mod_path = "%s/cobbler" % plib
sys.path.insert(0, mod_path)

import ConfigParser

pymongo_loaded = False

try:
    from pymongo import Connection
    pymongo_loaded = True
except:
    # FIXME: log message
    pass
from cexceptions import CX

cp = ConfigParser.ConfigParser()
cp.read("/etc/cobbler/mongodb.conf")

host = cp.get("connection", "host")
port = int(cp.get("connection", "port"))
mongodb = None


def __connect():
    # TODO: detect connection error
    global mongodb
    try:
        mongodb = Connection('localhost', 27017)['cobbler']
    except:
        # FIXME: log error
        raise CX("Unable to connect to Mongo database")


def register():
    """
    The mandatory cobbler module registration hook.
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


def serialize_item(obj, item):
    __connect()
    collection = mongodb[obj.collection_type()]
    data = collection.find_one({'name': item.name})
    if data:
        collection.update({'name': item.name}, item.to_datastruct())
    else:
        collection.insert(item.to_datastruct())


def serialize_delete(obj, item):
    __connect()
    collection = mongodb[obj.collection_type()]
    collection.remove({'name': item.name})


def serialize(obj):
    """
    Save an object to the database.
    """
    # TODO: error detection
    for x in obj:
        serialize_item(obj, x)


def deserialize_raw(collection_type):
    __connect()
    collection = mongodb[collection_type]
    return collection.find()


def deserialize(obj, topological=True):
    """
    Populate an existing object with the contents of datastruct.
    Object must "implement" Serializable.
    """
    datastruct = deserialize_raw(obj.collection_type())
    if topological and type(datastruct) == list:
        datastruct.sort(__depth_cmp)
    obj.from_datastruct(datastruct)


def __depth_cmp(item1, item2):
    d1 = item1.get("depth", 1)
    d2 = item2.get("depth", 1)
    return cmp(d1, d2)


