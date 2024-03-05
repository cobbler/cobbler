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
import json
from typing import Any, Dict

import yaml

import cobbler.api as capi
from cobbler import settings
from cobbler.cexceptions import CX

libpath = "/var/lib/cobbler/collections"


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "serializer"


def what() -> str:
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
            raise FileExistsError("Both JSON files (%s) exist!" % filename)


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

    if capi.CobblerAPI().settings().serializer_pretty_json:
        sort_keys = True
        indent = 4
    else:
        sort_keys = False
        indent = None

    _dict = item.serialize()
    with open(filename, "w+") as file_descriptor:
        data = json.dumps(_dict, sort_keys=sort_keys, indent=indent)
        file_descriptor.write(data)


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
    if collection.collection_type() != "setting":
        for x in collection:
            serialize_item(collection, x)


def deserialize_raw(collection_types: str):
    """
    Loads a collection from the disk.

    :param collection_types: The type of collection to load.
    :return: The loaded dictionary.
    """
    if collection_types == "settings":
        return settings.read_settings_file()

    results = []

    path = os.path.join(libpath, collection_types)
    all_files = glob.glob("%s/*.json" % path)
    with open("/etc/cobbler/settings.yaml", encoding="UTF-8") as settings_file:
        lazy_start = yaml.safe_load(settings_file).get("lazy_start", False)

    for file in all_files:
        (name, _) = os.path.splitext(os.path.basename(file))
        if lazy_start:
            _dict = {"name": name, "inmemory": False}
        else:
            with open(file, encoding="UTF-8") as file_descriptor:
                json_data = file_descriptor.read()
                _dict = json.loads(json_data)
                if _dict["name"] != name:
                    raise CX(
                        f"The file name {name}.json does not match the {_dict['name']} {collection_types}!"
                    )
        results.append(_dict)
    return results


def deserialize(collection, topological: bool = True):
    """
    Load a collection from file system.

    :param collection: The collection to deserialize.
    :param topological: If the collection list should be sorted by the
                        collection dict key 'depth' value or not.
    """

    datastruct = deserialize_raw(collection.collection_types())
    if topological and isinstance(datastruct, list):
        datastruct.sort(key=lambda x: x.get("depth", 1))
    if isinstance(datastruct, dict):
        collection.from_dict(datastruct)
    elif isinstance(datastruct, list):
        collection.from_list(datastruct)


def deserialize_item(collection_type: str, name: str) -> Dict[str, Any]:
    """
    Get a collection item from disk and parse it into an object.
    :param collection_type: The collection type to fetch.
    :param name: collection Item name
    :return: Dictionary of the collection item.
    """
    path = os.path.join(libpath, collection_type, f"{name}.json")
    with open(path, encoding="UTF-8") as file_descriptor:
        json_data = file_descriptor.read()
        _dict = json.loads(json_data)
        if _dict["name"] != name:
            raise CX(
                f"The file name {name}.json does not match the {_dict['name']} {collection_type}!"
            )
    _dict["inmemory"] = True
    return _dict
