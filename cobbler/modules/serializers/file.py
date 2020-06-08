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

from past.builtins import cmp
import os
import glob
import simplejson
import yaml

import cobbler.api as capi
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

    _dict = item.to_dict()

    if capi.CobblerAPI().settings().serializer_pretty_json:
        sort_keys = True
        indent = 4
    else:
        sort_keys = False
        indent = None

    filename += ".json"
    _dict = item.to_dict()
    fd = open(filename, "w+")
    data = simplejson.dumps(_dict, encoding="utf-8", sort_keys=sort_keys, indent=indent)
    fd.write(data)

    fd.close()


def serialize_delete(collection, item):
    """
    Delete a collection item from file system.

    :param collection: collection
    :param item: collection item
    """

    collection_types = collection.collection_types()
    filename = os.path.join(libpath, collection_types, item.name + ".json")

    filename += ".json"
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
    # FIXME: code to load settings file should not be replicated in all serializer subclasses.
    if collection_types == "settings":
        fd = open("/etc/cobbler/settings")
        _dict = yaml.safe_load(fd.read())
        fd.close()

        # include support
        for ival in _dict.get("include", []):
            for ifile in glob.glob(ival):
                with open(ifile, 'r') as fd:
                    _dict.update(yaml.safe_load(fd.read()))

        return _dict
    else:
        results = []

        path = os.path.join(libpath, collection_types)
        all_files = glob.glob("%s/*.json" % path)

        for f in all_files:
            fd = open(f)
            json_data = fd.read()
            _dict = simplejson.loads(json_data, encoding='utf-8')
            results.append(_dict)
            fd.close()
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

    :param collection: The collection type the deserialize
    :param topological: If the dict/list should be sorted or not.
    :type topological: bool
    """

    datastruct = deserialize_raw(collection.collection_types())
    if topological and type(datastruct) == list:
        # FIXME
        # datastruct.sort(key=__depth_cmp)
        pass
    if type(datastruct) == dict:
        collection.from_dict(datastruct)
    elif type(datastruct) == list:
        collection.from_list(datastruct)


def __depth_cmp(item1, item2):
    """
    The compare function to sort a dict.

    :param item1: The first item to compare.
    :param item2: The second item to compare.
    :return: Weather the first or second item is bigger!
    """
    d1 = item1.get("depth", 1)
    d2 = item2.get("depth", 1)
    return cmp(d1, d2)

# EOF
