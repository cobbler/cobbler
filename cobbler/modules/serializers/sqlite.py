"""
Cobbler's SQLite database based object serializer.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2024 Yuriy Chelpanov <yuriy.chelpanov@gmail.com>

import json
import logging
import os
import sqlite3
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from cobbler.cexceptions import CX
from cobbler.modules.serializers import StorageBase

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.cobbler_collections.collection import ITEM, Collection
    from cobbler.items.abstract.base_item import BaseItem


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "serializer"


def what() -> str:
    """
    Module identification function
    """
    return "serializer/sqlite"


class SQLiteSerializer(StorageBase):
    """
    Each collection is stored in a separate table named distros, profiles, etc.
    Tables are created on demand, when the first object of this type is written.

    TABLE name // name from collection.collection_types()
    (
        name TEXT PRIMARY KEY,    // name from item.name
        item TEXT                 // JSON representation of an object
    )
    """

    def __init__(self, api: "CobblerAPI"):
        super().__init__(api)
        self.logger = logging.getLogger()
        self.connection: Optional[sqlite3.Connection] = None
        self.arraysize = 1000
        self.database_file = "/var/lib/cobbler/collections/collections.db"

    def __connect(self) -> None:
        """
        Connect to the sqlite.
        """
        if self.connection is not None:
            return
        is_new_database = not os.path.isfile(self.database_file)
        conn = sqlite3.connect(":memory:")
        threadsafety_option = conn.execute(
            """
            select * from pragma_compile_options
            where compile_options like 'THREADSAFE=%'
            """
        ).fetchone()[0]
        conn.close()

        threadsafety = int(threadsafety_option.split("=")[1])
        if threadsafety != 1:
            raise CX(
                f"You cannot use SQLite compiled with SQLITE_THREADSAFE={threadsafety} with Cobbler.\n"
                "Please compile the code with the option SQLITE_THREADSAFE=1"
            )

        try:
            self.connection = sqlite3.connect(
                self.database_file,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )
        except sqlite3.DatabaseError as error:
            raise CX(
                f'Unable to connect to SQLite database "{self.database_file}": {error}'
            ) from error

        if is_new_database:
            self.logger.info(
                'Database with name "{%s}" was not found and will be created.',
                self.database_file,
            )

    def __create_table(self, table_name: str) -> None:
        """
        Creates a new SQLite table.

        :param table_name: The table name.
        """
        try:
            self.connection.execute(f"CREATE TABLE {table_name}(name text primary key, item text)")  # type: ignore
        except sqlite3.DatabaseError as error:
            raise CX(f'Unable to create table "{table_name}": {error}') from error

    def __is_table_exists(self, table_name: str) -> bool:
        """
        Return True if the table exists.

        :param table_name: The table name.
        :return: True if the table exists. Otherwise false.
        """
        cursor = self.connection.execute(  # type: ignore
            "SELECT name FROM sqlite_master WHERE name=:name", {"name": table_name}
        )
        if cursor.fetchone() is None:
            return False
        return True

    def __upsert_items(
        self, table_name: str, bind_vars: List[Optional[Dict[str, str]]]
    ) -> None:
        """
        Insert/Update values into the table.

        :param table_name: The table name.
        :param bind_vars: The list of bind variables for SQL statement.
        """
        if len(bind_vars) == 0:
            return

        self.__connect()
        if not self.__is_table_exists(table_name):
            self.__create_table(table_name)
        try:
            self.connection.executemany(  # type: ignore
                f"INSERT INTO {table_name}(name, item) "  # nosec
                "VALUES(:name, :item) "
                "ON CONFLICT(name) DO UPDATE SET item=excluded.item",
                bind_vars,  # type: ignore
            )
            self.connection.commit()  # type: ignore
        except sqlite3.DatabaseError as error:
            raise CX(f'Unable to upsert into table "{table_name}": {error}') from error

    def __build_bind_vars(self, item: "BaseItem") -> Dict[str, str]:
        """
        Build the bind variables for Insert/Update.

        :param item: The object for Insert/Update.
        :return: The bind variables dict.
        """
        if self.api.settings().serializer_pretty_json:
            sort_keys = True
            indent = 4
        else:
            sort_keys = False
            indent = None

        _dict = item.serialize()
        data = json.dumps(_dict, sort_keys=sort_keys, indent=indent)
        return {"name": item.name, "item": data}

    def serialize_item(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        """
        Save a collection item to table

        :param collection: The Cobbler collection to know the type of the item.
        :param item: The collection item to serialize.
        """
        if not item.name:
            raise CX("name unset for item!")

        self.__connect()
        self.__upsert_items(
            collection.collection_types(), [self.__build_bind_vars(item)]
        )

    def serialize(self, collection: "Collection[ITEM]") -> None:
        """
        Save a collection to disk

        :param collection: The collection to serialize.
        """
        self.__connect()
        ctype = collection.collection_types()
        bind_vars: List[Optional[Dict[str, str]]] = []
        for item in collection:
            bind_vars.append(self.__build_bind_vars(item))
        self.__upsert_items(ctype, bind_vars)

    def serialize_delete(self, collection: "Collection[ITEM]", item: "ITEM") -> None:
        """
        Delete a collection item from table

        :param collection: The Cobbler collection to know the type of the item.
        :param item: The collection item to delete.
        """
        self.__connect()
        table_name = collection.collection_types()
        try:
            self.connection.execute(  # type: ignore
                f"DELETE FROM {table_name} WHERE name=:name",  # nosec
                {"name": item.name},
            )
            self.connection.commit()  # type: ignore
        except sqlite3.DatabaseError as error:
            raise CX(
                f'Unable to delete from table "{table_name}": {error}'  # nosec
            ) from error

    def deserialize_raw(self, collection_type: str) -> List[Dict[str, Any]]:
        """
        Read the collection from the table.

        :param collection_type: The collection type to read.
        :return: The list of collection dicts.
        """
        self.__connect()
        results: List[Dict[str, Any]] = []
        if not self.__is_table_exists(collection_type):
            return results

        projection = "item"
        lazy_start = self.api.settings().lazy_start
        if lazy_start:
            projection = "name"

        try:
            cursor = self.connection.execute(  # type: ignore
                f"SELECT {projection} FROM {collection_type}"  # nosec
            )
        except sqlite3.DatabaseError as error:
            raise CX(
                f'Unable to SELECT from table "{collection_type}": {error}'  # nosec
            ) from error
        cursor.arraysize = self.arraysize
        for result in cursor.fetchall():
            if lazy_start:
                _dict = {"name": result[0]}
            else:
                _dict = json.loads(result[0])
            _dict["inmemory"] = not lazy_start
            results.append(_dict)
        return results

    def deserialize(
        self, collection: "Collection[ITEM]", topological: bool = True
    ) -> None:
        """
        Load a collection from disk.

        :param collection: The Cobbler collection to know the type of the item.
        :param topological: Sort collection based on each items' depth attribute in the list of collection items. This
                            ensures properly ordered object loading from disk with objects having parent/child
                            relationships, i.e. profiles/subprofiles.  See cobbler/items/abstract/inheritable_item.py
        """
        self.__connect()
        datastruct = self.deserialize_raw(collection.collection_types())
        if topological and isinstance(datastruct, list):  # type: ignore
            datastruct.sort(key=lambda x: x.get("depth", 1))  # type: ignore
        collection.from_list(datastruct)  # type: ignore

    def deserialize_item(self, collection_type: str, name: str) -> Dict[str, Any]:
        """
        Get a collection item from disk and parse it into an object.

        :param collection_type: The collection type to deserialize.
        :param item_name: The collection item name to deserialize.
        :return: Dictionary of the collection item.
        """
        self.__connect()
        if not self.__is_table_exists(collection_type):
            raise CX(
                f"Item {name} of collection {collection_type} was not found in SQLite database {self.database_file}!"
            )

        try:
            cursor = self.connection.execute(  # type: ignore
                f"SELECT item from {collection_type} WHERE name=:name",  # nosec
                {"name": name},
            )
        except sqlite3.DatabaseError as error:
            raise CX(
                f'Unable to SELECT from table "{collection_type}": {error}'  # nosec
            ) from error
        result = cursor.fetchone()
        if result is None:
            raise CX(
                f"Item {name} of collection {collection_type} was not found in SQLite database {self.database_file}!"
            )
        _dict = json.loads(result[0])
        if _dict["name"] != name:
            raise CX(
                f"The file name {name} does not match the {_dict['name']} {collection_type}!"
            )
        _dict["inmemory"] = True
        return _dict


def storage_factory(api: "CobblerAPI") -> SQLiteSerializer:
    """
    TODO
    """
    return SQLiteSerializer(api)
