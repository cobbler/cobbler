"""
Cobbler's file-based object serializer.
As of 9/2014, this is Cobbler's default serializer and the most stable one.
It uses multiple JSON files in /var/lib/cobbler/collections/distros, profiles, etc
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import os
import glob
import json
import logging
from typing import Any, Dict

import cobbler.api as capi
from cobbler import settings
from cobbler.cexceptions import CX
from cobbler.modules.serializers import StorageBase

logger = logging.getLogger()


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


def _find_double_json_files(filename: str):
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
            raise FileExistsError(f"Both JSON files ({filename}) exist!")


class FileSerializer(StorageBase):
    """
    TODO
    """

    def __init__(self, api):
        super().__init__(api)
        self.libpath = "/var/lib/cobbler/collections"

    def serialize_item(self, collection, item):
        if not item.name:
            raise CX("name unset for item!")

        collection_types = collection.collection_types()
        filename = os.path.join(self.libpath, collection_types, item.name + ".json")
        _find_double_json_files(filename)

        if capi.CobblerAPI().settings().serializer_pretty_json:
            sort_keys = True
            indent = 4
        else:
            sort_keys = False
            indent = None

        _dict = item.serialize()
        with open(filename, "w+", encoding="UTF-8") as file_descriptor:
            data = json.dumps(_dict, sort_keys=sort_keys, indent=indent)
            file_descriptor.write(data)

    def serialize_delete(self, collection, item):
        collection_types = collection.collection_types()
        filename = os.path.join(self.libpath, collection_types, item.name + ".json")
        _find_double_json_files(filename)

        if os.path.exists(filename):
            os.remove(filename)

    def serialize(self, collection):
        # do not serialize settings
        if collection.collection_type() != "setting":
            for item in collection:
                self.serialize_item(collection, item)

    def deserialize_raw(self, collection_type: str):
        if collection_type == "settings":
            return settings.read_settings_file()

        results = []

        path = os.path.join(self.libpath, collection_type)
        all_files = glob.glob(f"{path}/*.json")
        lazy_start = self.api.settings().lazy_start

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
                            f"The file name {name}.json does not match the {_dict['name']} {collection_type}!"
                        )
            results.append(_dict)
        return results

    def deserialize(self, collection, topological: bool = True):
        datastruct = self.deserialize_raw(collection.collection_types())
        if topological and isinstance(datastruct, list):
            datastruct.sort(key=lambda x: x.get("depth", 1))
        try:
            if isinstance(datastruct, dict):
                collection.from_dict(datastruct)
            elif isinstance(datastruct, list):
                collection.from_list(datastruct)
        except Exception as exc:
            logger.error(
                "Error while loading a collection: %s. Skipping collection %s!",
                exc,
                collection.collection_type(),
            )

    def deserialize_item(self, collection_type: str, name: str) -> Dict[str, Any]:
        """
        Get a collection item from disk and parse it into an object.

        :param collection_type: The collection type to fetch.
        :param name: collection Item name
        :return: Dictionary of the collection item.
        """
        path = os.path.join(self.libpath, collection_type, f"{name}.json")
        with open(path, encoding="UTF-8") as file_descriptor:
            json_data = file_descriptor.read()
            _dict = json.loads(json_data)
            if _dict["name"] != name:
                raise CX(
                    f"The file name {name}.json does not match the {_dict['name']} {collection_type}!"
                )
        _dict["inmemory"] = True
        return _dict


def storage_factory(api):
    """
    TODO
    """
    return FileSerializer(api)
