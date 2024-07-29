"""
Tests that validate the functionality of the module that is responsible for (de)serializing items to MongoDB.
"""

import copy
from typing import TYPE_CHECKING, Any

import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.modules.serializers import mongodb

from tests.conftest import does_not_raise

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def mongodb_obj(cobbler_api: CobblerAPI) -> mongodb.MongoDBSerializer:
    return mongodb.storage_factory(cobbler_api)


@pytest.fixture(scope="function", autouse=True)
def reset_database(mongodb_obj: mongodb.MongoDBSerializer):
    mongodb_obj.mongodb.drop_database("cobbler")  # type: ignore


def test_register():
    assert mongodb.register() == "serializer"


def test_what():
    assert mongodb.what() == "serializer/mongodb"


def test_storage_factory(cobbler_api: CobblerAPI):
    # Arrange & Act
    result = mongodb.storage_factory(cobbler_api)

    # Assert
    assert isinstance(result, mongodb.MongoDBSerializer)


def test_serialize_item(
    mocker: "MockerFixture", mongodb_obj: mongodb.MongoDBSerializer
):
    # Arrange
    mock_collection = mocker.MagicMock()
    mock_collection.collection_types.return_value = "distros"
    mock_item = mocker.MagicMock()
    mock_item.name = "testitem"
    mock_item.arch = "x86_64"
    mock_item.serialize.return_value = {"name": mock_item.name, "arch": mock_item.arch}

    # Act
    mongodb_obj.serialize_item(mock_collection, mock_item)

    # Assert
    assert len(list(mongodb_obj.mongodb["cobbler"]["distros"].find())) == 1  # type: ignore


def test_serialize_delete(
    mocker: "MockerFixture", mongodb_obj: mongodb.MongoDBSerializer
):
    # Arrange
    mock_collection = mocker.MagicMock()
    mock_collection.collection_types.return_value = "distros"
    mock_item = mocker.MagicMock()
    mock_item.name = "testitem"

    # Act
    mongodb_obj.serialize_delete(mock_collection, mock_item)

    # Assert
    assert len(list(mongodb_obj.mongodb["cobbler"]["distros"].find())) == 0  # type: ignore


def test_serialize(mocker: "MockerFixture", mongodb_obj: mongodb.MongoDBSerializer):
    # Arrange
    mock_collection = mocker.MagicMock()
    mock_collection.collection_types.return_value = "distros"
    mock_serialize_item = mocker.patch.object(mongodb_obj, "serialize_item")
    mock_collection.__iter__ = mocker.Mock(return_value=iter(["item1"]))

    # Act
    mongodb_obj.serialize(mock_collection)

    # Assert
    assert mock_serialize_item.call_count == 1


def test_deserialize_raw(mongodb_obj: mongodb.MongoDBSerializer):
    # Arrange
    collection_type = "distros"
    mongodb_obj.mongodb["cobbler"][collection_type].insert_one(  # type: ignore
        {"name": "testitem", "arch": "x86_64"}
    )
    mongodb_obj.mongodb["cobbler"][collection_type].insert_one(  # type: ignore
        {"name": "testitem2", "arch": "x86_64"}
    )

    # Act
    result = mongodb_obj.deserialize_raw(collection_type)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 2


def test_deserialize(mocker: "MockerFixture", mongodb_obj: mongodb.MongoDBSerializer):
    # Arrange
    mock_collection = mocker.MagicMock()
    mock_collection.collection_types.return_value = "distros"
    input_topological = True
    return_deserialize_raw = []
    mock_deserialize_raw = mocker.patch.object(
        mongodb_obj, "deserialize_raw", return_value=return_deserialize_raw
    )

    # Act
    mongodb_obj.deserialize(mock_collection, input_topological)

    # Assert
    assert mock_deserialize_raw.call_count == 1
    assert mock_collection.from_list.call_count == 1
    mock_collection.from_list.assert_called_with(return_deserialize_raw)


@pytest.mark.parametrize(
    "item_name,expected_exception",
    [
        (
            "testitem",
            does_not_raise(),
        ),
        (
            None,
            pytest.raises(CX),
        ),
    ],
)
def test_deserialize_item(
    mongodb_obj: mongodb.MongoDBSerializer, item_name: str, expected_exception: Any
):
    # Arrange
    collection_type = "distros"
    input_value = {"name": item_name, "arch": "x86_64"}
    test_item = copy.deepcopy(input_value)
    if item_name is not None:  # type: ignore
        mongodb_obj.mongodb["cobbler"][collection_type].insert_one(test_item)  # type: ignore

    expected_value = input_value.copy()
    expected_value["inmemory"] = True  # type: ignore

    # Act
    with expected_exception:
        result = mongodb_obj.deserialize_item(collection_type, item_name)
        print(result)

        # Assert
        assert result in (expected_value, {"inmemory": True})
