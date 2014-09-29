"""
Cobbler's Couch database based object serializer.
Experimental version.

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

import distutils.sysconfig
import simplejson
import sys
import yaml

plib = distutils.sysconfig.get_python_lib()
mod_path = "%s/cobbler" % plib
sys.path.insert(0, mod_path)

import couch

typez = ["distro", "profile", "system", "image", "repo"]
couchdb = couch.Couch('127.0.0.1')


def __connect():
    couchdb.connect()
    for x in typez:
        couchdb.createDb(x)


def register():
    """
    The mandatory cobbler module registration hook.
    """
    # FIXME: only run this if enabled.
    return "serializer"


def what():
    """
    Module identification function
    """
    return "serializer/couchdb"


def serialize_item(collection, item):
    """
    Save a collection item to database

    @param Collection collection collection
    @param Item item collection item
    """

    __connect()
    _dict = item.to_dict()
    # blindly prevent conflict resolution
    couchdb.openDoc(collection.collection_type(), item.name)
    data = couchdb.saveDoc(collection.collection_type(),
                           simplejson.dumps(_dict, encoding="utf-8"),
                           item.name)
    data = simplejson.loads(data)


def serialize_delete(collection, item):
    """
    Delete a collection item from database

    @param Collection collection collection
    @param Item item collection item
    """

    couchdb.deleteDoc(collection.collection_type(), item.name)


def serialize(collection):
    """
    Save a collection to disk
    API should usually use serialize_item() instead

    @param Collection collection collection
    """

    __connect()
    ctype = collection.collection_type()
    if ctype != "settings":
        for x in collection:
            serialize_item(collection, x)


def deserialize_raw(collection_type):
    __connect()
    contents = simplejson.loads(couchdb.listDoc(collection_type))
    items = []
    if "error" in contents and contents.get("reason", "").find("Missing") != -1:
        # no items in the DB yet
        return []
    for x in contents["rows"]:
        items.append(x["key"])

    # FIXME: code to load settings file should not be replicated in all
    #   serializer subclasses
    if collection_type == "settings":
        fd = open("/etc/cobbler/settings")
        _dict = yaml.safe_load(fd.read())
        fd.close()
        return _dict
    else:
        results = []
        for f in items:
            data = couchdb.openDoc(collection_type, f)
            _dict = simplejson.loads(data, encoding='utf-8')
            results.append(_dict)
        return results


def deserialize(collection, topological=True):
    """
    Load a collection from database

    @param Collection collection collection
    @param bool topological
    """

    __connect()
    datastruct = deserialize_raw(collection.collection_type())
    if topological and type(datastruct) == list:
        datastruct.sort(__depth_cmp)
    if type(datastruct) == list:
        collection.from_list(datastruct)
    elif type(datastruct) == dict:
        collection.from_dict(datastruct)


def __depth_cmp(item1, item2):
    d1 = item1.get("depth", 1)
    d2 = item2.get("depth", 1)
    return cmp(d1, d2)

# EOF
