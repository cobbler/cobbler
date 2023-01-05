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

        for file in all_files:
            with open(file, encoding="UTF-8") as file_descriptor:
                json_data = file_descriptor.read()
                _dict = json.loads(json_data)
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
                f"Error while loading a collection: {exc}. Skipping this collection!"
            )


def storage_factory(api):
    """
    TODO
    """
    return FileSerializer(api)
