"""
Cobbler's file-based object serializer.
As of 9/2014, this is Cobbler's default serializer and the most stable one.
It uses multiple JSON files in /var/lib/cobbler/collections/distros, profiles, etc
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import glob
import json
import logging
import os
from typing import TYPE_CHECKING, Any, Dict, List

import cobbler.api as capi
from cobbler.cexceptions import CX
from cobbler.modules.serializers import StorageBase

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.cobbler_collections.collection import ITEM, Collection

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


class FileSerializer(StorageBase):
    """
    JSON-file based serializer for Cobbler items.
    """

    def __init__(self, api: "CobblerAPI") -> None:
        super().__init__(api)
        self.libpath = "/var/lib/cobbler/collections"

    def serialize_item(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        if hasattr(item, "built_in") and getattr(item, "built_in") is True:
            # Don't attempt to serialize templates which are built-in
            return

        collection_types = collection.collection_types()
        filename = os.path.join(self.libpath, collection_types, item.uid + ".json")

        if capi.CobblerAPI().settings().serializer_pretty_json:
            sort_keys = True
            indent = 4
        else:
            sort_keys = False
            indent = None

        _dict = item.serialize()
        with open(filename, "w", encoding="UTF-8") as file_descriptor:
            data = json.dumps(_dict, sort_keys=sort_keys, indent=indent)
            file_descriptor.write(data)

    def serialize_delete(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        collection_types = collection.collection_types()
        filename = os.path.join(self.libpath, collection_types, item.uid + ".json")

        if os.path.exists(filename):
            os.remove(filename)

    def serialize(self, collection: "Collection[ITEM]") -> None:
        if collection.collection_type() == "setting":
            # do not serialize settings
            return
        for item in collection:
            self.serialize_item(collection, item)

    def deserialize_raw(self, collection_type: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        path = os.path.join(self.libpath, collection_type)
        all_files = glob.glob(f"{path}/*.json")
        lazy_start = self.api.settings().lazy_start

        for file in all_files:
            (uid, _) = os.path.splitext(os.path.basename(file))
            if lazy_start:
                _dict = {"uid": uid, "inmemory": False}
            else:
                with open(file, encoding="UTF-8") as file_descriptor:
                    json_data = file_descriptor.read()
                    _dict = json.loads(json_data)
                    if _dict["uid"] != uid:
                        raise CX(
                            f"The file name {uid}.json does not match the {_dict['uid']} {collection_type}!"
                        )
            results.append(_dict)
        return results  # type: ignore

    def deserialize(
        self, collection: "Collection[ITEM]", topological: bool = True
    ) -> None:
        datastruct = self.deserialize_raw(collection.collection_types())
        if topological:
            datastruct.sort(key=lambda x: x.get("depth", 1))
        try:
            if isinstance(datastruct, dict):
                # This is currently the corner case for the settings type.
                collection.from_dict(datastruct)  # type: ignore
            elif isinstance(datastruct, list):  # type: ignore
                collection.from_list(datastruct)  # type: ignore
        except Exception as exc:
            logger.error(
                "Error while loading a collection: %s. Skipping collection %s!",
                exc,
                collection.collection_type(),
            )

    def deserialize_item(self, collection_type: str, uid: str) -> Dict[str, Any]:
        """
        Get a collection item from disk and parse it into an object.

        :param collection_type: The collection type to fetch.
        :param uid: collection Item uid
        :return: Dictionary of the collection item.
        """
        path = os.path.join(self.libpath, collection_type, f"{uid}.json")
        with open(path, encoding="UTF-8") as file_descriptor:
            json_data = file_descriptor.read()
            _dict = json.loads(json_data)
            if _dict["uid"] != uid:
                raise CX(
                    f"The file name {uid}.json does not match the {_dict['uid']} {collection_type}!"
                )
        _dict["inmemory"] = True
        return _dict


def storage_factory(api: "CobblerAPI") -> FileSerializer:
    """
    Factory method to allow the serializer interface to instaniate the concrete serializer without knowing which
    serializer is initalized.
    """
    return FileSerializer(api)
