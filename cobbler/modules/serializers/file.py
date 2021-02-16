"""
Cobbler's file-based object serializer.
As of 9/2014, this is Cobbler's default serializer and the most stable one.
It uses multiple JSON files in /var/lib/cobbler/collections/distros, profiles, etc

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

import os
import glob
import simplejson

import cobbler.api as capi
from cobbler import settings
from cobbler.cexceptions import CX

libpath = "/var/lib/cobbler/collections"


def register():
    """
    The mandatory Cobbler module registration hook.
    """
    return "serializer"


def what():
    """
    Module identification function
    """
    return "serializer/file"


def __find_double_json_files(filename: str):
    """
    Finds a file with duplicate .json ending and renames it.
    :param filename: Filename to be checked
    :raises FileExistsError: If both JSON files exist
    """

    if not os.path.isfile(filename):
        if os.path.isfile(filename + ".json"):
            os.rename(filename + ".json", filename)
    else:
        if os.path.isfile(filename + ".json"):
            raise FileExistsError("Both JSON files exist!")


def serialize_item(collection, item):
    """
    Save a collection item to file system

    :param collection: collection
    :param item: collection item
    """

    if not item.name:
        raise CX("name unset for item!")

    collection_types = collection.collection_types()
    filename = os.path.join(libpath, collection_types, item.name + ".json")
    __find_double_json_files(filename)

    _dict = item.to_dict()

    if capi.CobblerAPI().settings().serializer_pretty_json:
        sort_keys = True
        indent = 4
    else:
        sort_keys = False
        indent = None

    _dict = item.to_dict()
    with open(filename, "w+") as fd:
        data = simplejson.dumps(_dict, encoding="utf-8", sort_keys=sort_keys, indent=indent)
        fd.write(data)


def serialize_delete(collection, item):
    """
    Delete a collection item from file system.

    :param collection: collection
    :param item: collection item
    """

    collection_types = collection.collection_types()
    filename = os.path.join(libpath, collection_types, item.name + ".json")
    __find_double_json_files(filename)

    if os.path.exists(filename):
        os.remove(filename)


def serialize(collection):
    """
    Save a collection to file system

    :param collection: collection
    """

    # do not serialize settings
    ctype = collection.collection_type()
    if ctype != "settings":
        for x in collection:
            serialize_item(collection, x)


def deserialize_raw(collection_types):
    """
    Loads a collection from the disk.

    :param collection_types: The type of collection to load.
    :return: The loaded dictionary.
    """
    if collection_types == "settings":
        return settings.read_settings_file()
    else:
        results = []

        path = os.path.join(libpath, collection_types)
        all_files = glob.glob("%s/*.json" % path)

        for f in all_files:
            with open(f) as fd:
                json_data = fd.read()
                _dict = simplejson.loads(json_data, encoding='utf-8')
                results.append(_dict)
        return results


def filter_upgrade_duplicates(file_list):
    """
    In a set of files, some ending with .json, some not, return the list of files with the .json ones taking priority
    over the ones that are not.

    :param file_list: The list of files to remove duplicates from.
    :return: The filtered list of files. Normally this should only return ``.json``-Files.
    """
    bases = {}
    for f in file_list:
        basekey = f.replace(".json", "")
        if f.endswith(".json"):
            bases[basekey] = f
        else:
            lookup = bases.get(basekey, "")
            if not lookup.endswith(".json"):
                bases[basekey] = f
    return list(bases.values())


def deserialize(collection, topological=True):
    """
    Load a collection from file system.

    :param collection: The collection to deserialize.
    :param topological: If the collection list should be sorted by the
                        collection dict depth value or not.
    :type topological: bool
    """

    datastruct = deserialize_raw(collection.collection_types())
    if topological and type(datastruct) == list:
        datastruct.sort(key=lambda x: x["depth"])
    if type(datastruct) == dict:
        collection.from_dict(datastruct)
    elif type(datastruct) == list:
        collection.from_list(datastruct)
