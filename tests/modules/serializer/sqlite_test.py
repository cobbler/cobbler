"""
Tests that validate the functionality of the module that is responsible for (de)serializing items to SQLite.
"""

import json
import os
import pathlib
from typing import Any, Dict, List, Union

import pytest
from pytest_mock import MockerFixture

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections.collection import Collection
from cobbler.items.abstract.bootable_item import BootableItem
from cobbler.modules.serializers import sqlite
from cobbler.settings import Settings

from tests.conftest import does_not_raise


@pytest.fixture(name="test_settings")
def fixture_test_settings(mocker: MockerFixture) -> Settings:
    """
    Fixture to provide mocked settings that match the tests expectations.
    """
    settings = mocker.MagicMock(name="sqlite_setting_mock", spec=Settings)
    settings.lazy_start = False
    settings.cache_enabled = False
    settings.serializer_pretty_json = False
    settings.memory_indexes = {}
    return settings


class MockBootableItem(BootableItem):
    """
    Test Item for the serializer tests.
    """

    def make_clone(self) -> "MockBootableItem":
        return MockBootableItem(self.api)


class MockCollection(Collection[MockBootableItem]):
    """
    Test Collection that is used for the serializer tests.
    """

    @staticmethod
    def collection_type() -> str:
        return "test"

    @staticmethod
    def collection_types() -> str:
        return "tests"

    def factory_produce(
        self, api: "CobblerAPI", seed_data: Dict[Any, Any]
    ) -> MockBootableItem:
        new_test = MockBootableItem(api)
        return new_test

    def remove(
        self,
        ref: MockBootableItem,
        with_delete: bool = True,
        with_sync: bool = True,
        with_triggers: bool = True,
        recursive: bool = False,
        rebuild_menu: bool = True,
    ) -> None:
        del self.listing[ref.uid]


@pytest.fixture(name="serializer_obj")
def fixture_serializer_obj(
    mocker: MockerFixture,
    cobbler_api: CobblerAPI,
    tmpdir: pathlib.Path,
    test_settings: Settings,
):
    """
    Generates an empty serializer object that is ready to be used.
    """
    mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
    sqlite_obj = sqlite.storage_factory(cobbler_api)
    sqlite_obj.database_file = os.path.join(tmpdir, "tests.db")

    try:
        sqlite_obj.deserialize_item("tests", "test")
    except CX:
        pass

    sqlite_obj.connection.execute(  # type: ignore
        "CREATE table if not exists tests(uid text primary key, item text)"
    )
    sqlite_obj.connection.commit()  # type: ignore
    yield sqlite_obj
    sqlite_obj.connection.execute("DROP table if exists tests")  # type: ignore
    sqlite_obj.connection.commit()  # type: ignore
    sqlite_obj.connection.close()  # type: ignore


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


def test_serialize_item(
    mocker: "MockerFixture",
    serializer_obj: sqlite.SQLiteSerializer,
    cobbler_api: CobblerAPI,
):
    """
    Test that will assert if a given item can be written to table successfully.
    """
    # pylint: disable=protected-access
    # Arrange
    mcollection = MockCollection(cobbler_api._collection_mgr)  # type: ignore
    mock_get_items = mocker.patch.object(cobbler_api, "get_items")
    mock_get_items.return_value = mcollection
    mitem = MockBootableItem(cobbler_api)
    mitem.name = "test_serializer_item"  # type: ignore[method-assign]

    # Act
    serializer_obj.connection.execute("DROP table if exists tests")  # type: ignore
    serializer_obj.serialize_item(mcollection, mitem)
    cursor = serializer_obj.connection.execute(  # type: ignore
        "SELECT name FROM sqlite_master WHERE name=:name", {"name": "tests"}
    )
    table_exists = cursor.fetchone() is not None
    cursor = serializer_obj.connection.execute(  # type: ignore
        "SELECT uid FROM tests WHERE uid=:uid", {"uid": mitem.uid}
    )
    row_exists = cursor.fetchone() is not None

    # Cleanup
    serializer_obj.connection.execute("DROP table if exists tests")  # type: ignore
    serializer_obj.connection.commit()  # type: ignore

    # Assert
    assert os.path.exists(serializer_obj.database_file)
    assert table_exists
    assert row_exists


def test_serialize_delete(
    mocker: "MockerFixture",
    serializer_obj: sqlite.SQLiteSerializer,
    cobbler_api: CobblerAPI,
):
    """
    Test that will assert if a given item can be deleted.
    """
    # pylint: disable=protected-access
    # Arrange
    mcollection = MockCollection(cobbler_api._collection_mgr)  # type: ignore
    mock_get_items = mocker.patch.object(cobbler_api, "get_items")
    mock_get_items.return_value = mcollection
    mitem = MockBootableItem(cobbler_api)
    mitem.name = "test_serializer_del"  # type: ignore[method-assign]
    serializer_obj.serialize_item(mcollection, mitem)

    # Act
    serializer_obj.serialize_delete(mcollection, mitem)
    cursor = serializer_obj.connection.execute(  # type: ignore
        "SELECT uid FROM tests WHERE uid=:uid", {"uid": mitem.uid}
    )
    row_exists = cursor.fetchone() is not None

    # Assert
    assert not row_exists


@pytest.mark.parametrize(
    "input_collection_type",
    ["tests"],
)
def test_serialize(
    mocker: "MockerFixture",
    input_collection_type: str,
    serializer_obj: sqlite.SQLiteSerializer,
    cobbler_api: CobblerAPI,
):
    """
    Test to verify that serializing a whole collection is working as expected.
    """
    # pylint: disable=protected-access
    # Arrange
    mcollection = MockCollection(cobbler_api._collection_mgr)  # type: ignore
    mock_get_items = mocker.patch.object(cobbler_api, "get_items")
    mock_get_items.return_value = mcollection
    mitem = MockBootableItem(cobbler_api)
    mitem.name = "test_serialize"  # type: ignore[method-assign]

    mcollection.listing[mitem.uid] = mitem

    # Act
    serializer_obj.serialize(mcollection)  # type: ignore
    cursor = serializer_obj.connection.execute(  # type: ignore
        "SELECT name FROM sqlite_master WHERE name=:name",
        {"name": input_collection_type},
    )
    table_exists = cursor.fetchone() is not None
    cursor = serializer_obj.connection.execute(  # type: ignore
        f"SELECT uid FROM {input_collection_type} WHERE uid=:uid",
        {"uid": mitem.uid},  # type: ignore
    )
    row_exists = cursor.fetchone() is not None

    # Assert
    assert os.path.exists(serializer_obj.database_file)
    assert table_exists  # type: ignore[reportUnboundVariable]
    assert row_exists  # type: ignore[reportUnboundVariable]


@pytest.mark.parametrize(
    "input_collection_type,lazy_start,expected_inmemory",
    [
        ("tests", False, True),
        ("tests", True, False),
    ],
)
def test_deserialize_raw(
    mocker: MockerFixture,
    input_collection_type: str,
    lazy_start: bool,
    expected_inmemory: bool,
    serializer_obj: sqlite.SQLiteSerializer,
    cobbler_api: CobblerAPI,
    test_settings: Settings,
):
    """
    Test that will assert if a given item can be deserilized in raw.
    """
    # pylint: disable=protected-access,attribute-defined-outside-init
    # Arrange
    read_settings_file_mock = mocker.patch("cobbler.settings.read_settings_file")
    mcollection = MockCollection(cobbler_api._collection_mgr)  # type: ignore
    mock_get_items = mocker.patch.object(cobbler_api, "get_items")
    mock_get_items.return_value = mcollection
    mitem = MockBootableItem(cobbler_api)
    mitem.name = "test_deserialize_raw"  # type: ignore[method-assign]
    mitem.item = "{'name': 'test_deserialize_raw'}"

    mcollection.listing[mitem.name] = mitem
    serializer_obj.serialize(mcollection)  # type: ignore
    test_settings.lazy_start = lazy_start

    # Act
    result = serializer_obj.deserialize_raw(input_collection_type)

    # Assert
    read_settings_file_mock.assert_not_called()
    assert result[0]["uid"] == mitem.uid  # type: ignore
    assert result[0]["inmemory"] == expected_inmemory  # type: ignore


@pytest.mark.parametrize(
    "input_collection_type,input_collection,input_topological,expected_result",
    [
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
    stub_from = mocker.stub(name="from_list_stub")
    mock = MockCollection(mocker.MagicMock())
    mocker.patch.object(mock, "from_list", new=stub_from)
    mocker.patch.object(mock, "collection_types", return_value=input_collection_type)

    # Act
    serializer_obj.deserialize(mock, input_topological)  # type: ignore

    # Assert
    assert stub_from.called
    stub_from.assert_called_with(expected_result)


@pytest.mark.parametrize(
    "input_collection_type,input_item,expected_result,expected_exception",
    [
        (
            "tests",
            {"uid": "8b1fe974e7a240bfb5639976ab64b4fb", "name": "test1"},
            {
                "uid": "8b1fe974e7a240bfb5639976ab64b4fb",
                "name": "test1",
                "inmemory": True,
            },
            does_not_raise(),
        ),
        (
            "tests",
            {"uid": "8b1fe974e7a240bfb5639976ab64b4fb", "name": "test2"},
            {
                "uid": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "name": "test2",
                "inmemory": True,
            },
            pytest.raises(CX),
        ),
    ],
)
def test_deserialize_item(
    input_collection_type: str,
    input_item: Dict[str, str],
    expected_result: Dict[str, Union[str, bool]],
    expected_exception: Any,
    serializer_obj: sqlite.SQLiteSerializer,
):
    """
    Test to verify that deserializing a single item works.
    """
    # Arrange
    serializer_obj.connection.execute(  # type: ignore
        f"INSERT INTO {input_collection_type}(uid, item) VALUES(:uid,:item)",
        {"uid": input_item["uid"], "item": json.dumps(input_item)},
    )
    serializer_obj.connection.commit()  # type: ignore

    # Act
    with expected_exception:
        result = serializer_obj.deserialize_item(
            input_collection_type, expected_result["uid"]  # type: ignore[reportGeneralTypeIssues,arg-type]
        )

        # Assert
        assert result == expected_result
