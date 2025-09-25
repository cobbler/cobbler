"""
Tests that validate the functionality of the module that is responsible for (de)serializing items to MongoDB.
"""

import copy
from typing import TYPE_CHECKING, Any, Dict, List

import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.modules.serializers import mongodb

from tests.conftest import does_not_raise

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="mongodb_obj")
def fixture_mongodb_obj(cobbler_api: CobblerAPI) -> mongodb.MongoDBSerializer:
    """
    Fixture to create a fresh MongoDB Serializer for each test.
    """
    return mongodb.storage_factory(cobbler_api)


@pytest.fixture(name="reset_database", scope="function", autouse=True)
def fixture_reset_database(mongodb_obj: mongodb.MongoDBSerializer):
    """
    Fixture to reset the MongoDB database after each test.
    """
    mongodb_obj.mongodb.drop_database("cobbler")  # type: ignore


@pytest.mark.mongodb
def test_register():
    """
    Test to verify that the identifier of the MongoDB module is stable.
    """
    assert mongodb.register() == "serializer"


@pytest.mark.mongodb
def test_what():
    """
    Test to verify that the MongoDB module category is stable.
    """
    assert mongodb.what() == "serializer/mongodb"


@pytest.mark.mongodb
def test_storage_factory(cobbler_api: CobblerAPI):
    """
    Test to verify that the MongoDB Module Factory works as intended.
    """
    # Arrange & Act
    result = mongodb.storage_factory(cobbler_api)

    # Assert
    assert isinstance(result, mongodb.MongoDBSerializer)


@pytest.mark.mongodb
def test_serialize_item(
    mocker: "MockerFixture", mongodb_obj: mongodb.MongoDBSerializer
):
    """
    Test that will assert if a given item can be written to disk successfully.
    """
    # Arrange
    mock_collection = mocker.MagicMock()
    mock_collection.collection_types.return_value = "distros"
    mock_item = mocker.MagicMock()
    mock_item.uid = "8b1fe974e7a240bfb5639976ab64b4fb"
    mock_item.name = "testitem"
    mock_item.arch = "x86_64"
    mock_item.serialize.return_value = {"name": mock_item.name, "arch": mock_item.arch}

    # Act
    mongodb_obj.serialize_item(mock_collection, mock_item)

    # Assert
    assert len(list(mongodb_obj.mongodb["cobbler"]["distros"].find())) == 1  # type: ignore


@pytest.mark.mongodb
def test_serialize_delete(
    mocker: "MockerFixture", mongodb_obj: mongodb.MongoDBSerializer
):
    """
    Test that will assert if a given item can be deleted.
    """
    # Arrange
    mock_collection = mocker.MagicMock()
    mock_collection.collection_types.return_value = "distros"
    mock_item = mocker.MagicMock()
    mock_item.uid = "8b1fe974e7a240bfb5639976ab64b4fb"
    mock_item.name = "testitem"

    # Act
    mongodb_obj.serialize_delete(mock_collection, mock_item)

    # Assert
    assert len(list(mongodb_obj.mongodb["cobbler"]["distros"].find())) == 0  # type: ignore


@pytest.mark.mongodb
def test_serialize(mocker: "MockerFixture", mongodb_obj: mongodb.MongoDBSerializer):
    """
    Test that will assert if a given item can be deserialized and added to a collection.
    """
    # Arrange
    mock_collection = mocker.MagicMock()
    mock_collection.collection_types.return_value = "distros"
    mock_serialize_item = mocker.patch.object(mongodb_obj, "serialize_item")
    mock_collection.__iter__ = mocker.Mock(return_value=iter(["item1"]))

    # Act
    mongodb_obj.serialize(mock_collection)

    # Assert
    assert mock_serialize_item.call_count == 1


@pytest.mark.mongodb
def test_deserialize_raw(mongodb_obj: mongodb.MongoDBSerializer):
    """
    Test that will assert if a given item can be deserilized in raw.
    """
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


@pytest.mark.mongodb
def test_deserialize(mocker: "MockerFixture", mongodb_obj: mongodb.MongoDBSerializer):
    """
    Test that will assert if a given collection can be successfully deserialized.
    """
    # Arrange
    mock_collection = mocker.MagicMock()
    mock_collection.collection_types.return_value = "distros"
    input_topological = True
    return_deserialize_raw: List[Dict[str, Any]] = []
    mock_deserialize_raw = mocker.patch.object(
        mongodb_obj, "deserialize_raw", return_value=return_deserialize_raw
    )

    # Act
    mongodb_obj.deserialize(mock_collection, input_topological)

    # Assert
    assert mock_deserialize_raw.call_count == 1
    assert mock_collection.from_list.call_count == 1
    mock_collection.from_list.assert_called_with(return_deserialize_raw)


@pytest.mark.mongodb
@pytest.mark.parametrize(
    "item_uid,expected_exception",
    [
        (
            "8b1fe974e7a240bfb5639976ab64b4fb",
            does_not_raise(),
        ),
        (
            None,
            pytest.raises(CX),
        ),
    ],
)
def test_deserialize_item(
    mongodb_obj: mongodb.MongoDBSerializer, item_uid: str, expected_exception: Any
):
    """
    Test that will assert if a given item can be successfully deserialized.
    """
    # Arrange
    collection_type = "distros"
    input_value = {
        "uid": "8b1fe974e7a240bfb5639976ab64b4fb",
        "name": item_uid,
        "arch": "x86_64",
    }
    test_item = copy.deepcopy(input_value)
    if item_uid is not None:  # type: ignore
        mongodb_obj.mongodb["cobbler"][collection_type].insert_one(test_item)  # type: ignore

    expected_value = input_value.copy()
    expected_value["inmemory"] = True  # type: ignore

    # Act
    with expected_exception:
        result = mongodb_obj.deserialize_item(collection_type, item_uid)

        # Assert
        assert result in (expected_value, {"inmemory": True})
