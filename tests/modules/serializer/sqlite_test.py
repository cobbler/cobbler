import json
import os
import pathlib
from typing import Any, Dict, List, Union
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections.collection import Collection
from cobbler.items.abstract.base_item import BaseItem
from cobbler.modules.serializers import sqlite
from cobbler.settings import Settings

from tests.conftest import does_not_raise


class MockItem(BaseItem):
    """
    Test Item for the serializer tests.
    """

    def make_clone(self) -> "MockItem":
        return MockItem(self.api)


class MockCollection(Collection[MockItem]):
    """
    Test Collection that is used for the serializer tests.
    """

    @staticmethod
    def collection_type() -> str:
        return "test"

    @staticmethod
    def collection_types() -> str:
        return "tests"

    def factory_produce(self, api: "CobblerAPI", seed_data: Dict[Any, Any]) -> MockItem:
        new_test = MockItem(api)
        return new_test

    def remove(
        self,
        name: str,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
    ) -> None:
        del self.listing[name]


@pytest.fixture()
def serializer_obj(cobbler_api: CobblerAPI, tmpdir: pathlib.Path):
    """
    Generates an empty serializer object that is ready to be used.
    """
    sqlite_obj = sqlite.storage_factory(cobbler_api)
    sqlite_obj.database_file = os.path.join(tmpdir, "tests.db")

    try:
        sqlite_obj.deserialize_item("tests", "test")
    except CX:
        pass

    sqlite_obj.connection.execute(  # type: ignore
        f"CREATE table if not exists tests(name text primary key, item text)"
    )
    sqlite_obj.connection.commit()  # type: ignore
    return sqlite_obj


def test_register():
    """
    Test that will assert if the return value of the register method is correct.
    """
    # Arrange
    # Act
    result = sqlite.register()

    # Assert
    assert isinstance(result, str)
    assert result == "serializer"


def test_what():
    """
    Test that will assert if the return value of the identity hook of the module is correct.
    """
    # Arrange
    # Act
    result = sqlite.what()

    # Assert
    assert isinstance(result, str)
    assert result == "serializer/sqlite"


def test_storage_factory(cobbler_api: CobblerAPI):
    """
    Test that will assert if the factory can successfully generate a SQLiteSerializer object.
    """
    # Arrange

    # Act
    result = sqlite.storage_factory(cobbler_api)

    # Assert
    assert isinstance(result, sqlite.SQLiteSerializer)


def test_serialize_item_raise(
    mocker: MockerFixture, serializer_obj: sqlite.SQLiteSerializer
):
    # Arrange
    mitem = mocker.Mock()
    mcollection = mocker.Mock()
    mitem.name = ""

    # Act and assert
    with pytest.raises(CX):
        serializer_obj.serialize_item(mcollection, mitem)

    # Cleanup
    serializer_obj.connection.execute("DROP table if exists tests")  # type: ignore
    serializer_obj.connection.commit()  # type: ignore
    serializer_obj.connection.close()  # type: ignore


def test_serialize_item(
    serializer_obj: sqlite.SQLiteSerializer, cobbler_api: CobblerAPI
):
    """
    Test that will assert if a given item can be written to table successfully.
    """
    # Arrange
    mitem = MockItem(cobbler_api)
    mitem.name = "test_serializer_item"
    mcollection = MockCollection(cobbler_api._collection_mgr)  # type: ignore

    # Act
    serializer_obj.connection.execute("DROP table if exists tests")  # type: ignore
    serializer_obj.serialize_item(mcollection, mitem)
    cursor = serializer_obj.connection.execute(  # type: ignore
        "SELECT name FROM sqlite_master WHERE name=:name", {"name": "tests"}
    )
    table_exists = cursor.fetchone() is not None
    cursor = serializer_obj.connection.execute(  # type: ignore
        "SELECT name FROM tests WHERE name=:name", {"name": mitem.name}
    )
    row_exists = cursor.fetchone() is not None

    # Cleanup
    serializer_obj.connection.execute("DROP table if exists tests")  # type: ignore
    serializer_obj.connection.commit()  # type: ignore
    serializer_obj.connection.close()  # type: ignore

    # Assert
    assert os.path.exists(serializer_obj.database_file)
    assert table_exists
    assert row_exists


def test_serialize_delete(
    serializer_obj: sqlite.SQLiteSerializer, cobbler_api: CobblerAPI
):
    """
    Test that will assert if a given item can be deleted.
    """
    # Arrange
    mitem = MockItem(cobbler_api)
    mitem.name = "test_serializer_del"
    mcollection = MockCollection(cobbler_api._collection_mgr)  # type: ignore
    serializer_obj.serialize_item(mcollection, mitem)

    # Act
    serializer_obj.serialize_delete(mcollection, mitem)
    cursor = serializer_obj.connection.execute(  # type: ignore
        "SELECT name FROM tests WHERE name=:name", {"name": mitem.name}
    )
    row_exists = cursor.fetchone() is not None

    # Cleanup
    serializer_obj.connection.execute("DROP table if exists tests")  # type: ignore
    serializer_obj.connection.commit()  # type: ignore
    serializer_obj.connection.close()  # type: ignore

    # Assert
    assert not row_exists


@pytest.mark.parametrize(
    "input_collection_type,input_collection",
    [("settings", {}), ("tests", MagicMock())],
)
def test_serialize(
    #    mocker: MockerFixture,
    input_collection_type: str,
    input_collection: Union[Dict[Any, Any], MagicMock],
    serializer_obj: sqlite.SQLiteSerializer,
    cobbler_api: CobblerAPI,
):
    # Arrange
    if input_collection_type == "settings":
        mcollection = Settings()
    else:
        mitem = MockItem(cobbler_api)
        mitem.name = "test_serialize"
        mcollection = MockCollection(cobbler_api._collection_mgr)  # type: ignore
        mcollection.listing[mitem.name] = mitem

    # Act
    serializer_obj.serialize(mcollection)  # type: ignore
    if input_collection_type != "settings":
        cursor = serializer_obj.connection.execute(  # type: ignore
            "SELECT name FROM sqlite_master WHERE name=:name",
            {"name": input_collection_type},
        )
        table_exists = cursor.fetchone() is not None
        cursor = serializer_obj.connection.execute(  # type: ignore
            f"SELECT name FROM {input_collection_type} WHERE name=:name",
            {"name": mitem.name},  # type: ignore
        )
        row_exists = cursor.fetchone() is not None

        # Cleanup
        serializer_obj.connection.execute("DROP table if exists tests")  # type: ignore
        serializer_obj.connection.commit()  # type: ignore
        serializer_obj.connection.close()  # type: ignore

    # Assert
    if input_collection_type == "settings":
        assert mcollection.collection_types() == "settings"
    else:
        assert os.path.exists(serializer_obj.database_file)
        assert table_exists  # type: ignore[reportUnboundVariable]
        assert row_exists  # type: ignore[reportUnboundVariable]


@pytest.mark.parametrize(
    "input_collection_type,expected_result,settings_read",
    [
        ("settings", {}, True),
        ("distros", [], False),
    ],
)
def test_deserialize_raw(
    mocker: MockerFixture,
    input_collection_type: str,
    expected_result: Union[List[Any], Dict[Any, Any]],
    settings_read: bool,
    serializer_obj: sqlite.SQLiteSerializer,
):
    """
    Test that will assert if a given item can be deserilized in raw.
    """
    # Arrange
    mocker.patch("cobbler.settings.read_settings_file", return_value=expected_result)

    # Act
    result = serializer_obj.deserialize_raw(input_collection_type)

    # Cleanup
    serializer_obj.connection.execute("DROP table if exists tests")  # type: ignore
    serializer_obj.connection.commit()  # type: ignore
    serializer_obj.connection.close()  # type: ignore

    # Assert
    assert result == expected_result


@pytest.mark.parametrize(
    "input_collection_type,input_collection,input_topological,expected_result",
    [
        ("settings", {}, True, {}),
        ("settings", {}, False, {}),
        (
            "distros",
            [{"depth": 2, "name": False}, {"depth": 1, "name": True}],
            True,
            [{"depth": 1, "name": True}, {"depth": 2, "name": False}],
        ),
        (
            "distros",
            [{"depth": 2, "name": False}, {"depth": 1, "name": True}],
            False,
            [{"depth": 2, "name": False}, {"depth": 1, "name": True}],
        ),
        (
            "distros",
            [{"name": False}, {"name": True}],
            True,
            [{"name": False}, {"name": True}],
        ),
        (
            "distros",
            [{"name": False}, {"name": True}],
            False,
            [{"name": False}, {"name": True}],
        ),
    ],
)
def test_deserialize(
    mocker: MockerFixture,
    input_collection_type: str,
    input_collection: Union[Dict[Any, Any], List[Dict[Any, Any]]],
    input_topological: bool,
    expected_result: Union[Dict[Any, Any], List[Dict[Any, Any]]],
    serializer_obj: sqlite.SQLiteSerializer,
):
    """
    Test that will assert if a given item can be successfully deserialized.
    """
    # Arrange
    mocker.patch.object(
        serializer_obj,
        "deserialize_raw",
        return_value=input_collection,
    )
    if input_collection_type == "settings":
        stub_from = mocker.stub(name="from_dict_stub")
        mock = Settings()
        mocker.patch.object(mock, "from_dict", new=stub_from)
    else:
        stub_from = mocker.stub(name="from_list_stub")
        mock = MockCollection(mocker.MagicMock())
        mocker.patch.object(mock, "from_list", new=stub_from)
        mocker.patch.object(
            mock, "collection_types", return_value=input_collection_type
        )

    # Act
    serializer_obj.deserialize(mock, input_topological)  # type: ignore

    # Cleanup
    serializer_obj.connection.execute("DROP table if exists tests")  # type: ignore
    serializer_obj.connection.commit()  # type: ignore
    serializer_obj.connection.close()  # type: ignore

    # Assert
    assert stub_from.called
    stub_from.assert_called_with(expected_result)


@pytest.mark.parametrize(
    "input_collection_type,input_item,expected_result,expected_exception",
    [
        (
            "tests",
            {"name": "test1"},
            {"name": "test1", "inmemory": True},
            does_not_raise(),
        ),
        (
            "tests",
            {"name": "test2"},
            {"name": "fake", "inmemory": True},
            pytest.raises(CX),
        ),
    ],
)
def test_deserialize_item(
    mocker: MockerFixture,
    input_collection_type: str,
    input_item: Dict[str, str],
    expected_result: Dict[str, Union[str, bool]],
    expected_exception: Any,
    serializer_obj: sqlite.SQLiteSerializer,
):
    """
    TODO
    """
    # Arrange
    serializer_obj.connection.execute(  # type: ignore
        f"INSERT INTO {input_collection_type}(name, item) VALUES(:name,:item)",
        {"name": input_item["name"], "item": json.dumps(input_item)},
    )
    serializer_obj.connection.commit()  # type: ignore

    # Act
    with expected_exception:
        result = serializer_obj.deserialize_item(
            input_collection_type, expected_result["name"]  # type: ignore[reportGeneralTypeIssues]
        )

        # Assert
        assert result == expected_result

    # Cleanup
    serializer_obj.connection.execute("DROP table if exists tests")  # type: ignore
    serializer_obj.connection.commit()  # type: ignore
    serializer_obj.connection.close()  # type: ignore
