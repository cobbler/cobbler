import pytest

from cobbler.modules.serializers import mongodb


@pytest.fixture
def mongodb_obj(cobbler_api):
    return mongodb.storage_factory(cobbler_api)


@pytest.fixture(scope="function", autouse=True)
def reset_database(mongodb_obj):
    mongodb_obj.mongodb.drop_database("cobbler")


def test_register():
    assert mongodb.register() == "serializer"


def test_what():
    assert mongodb.what() == "serializer/mongodb"


def test_storage_factory(cobbler_api):
    # Arrange & Act
    result = mongodb.storage_factory(cobbler_api)

    # Assert
    assert isinstance(result, mongodb.MongoDBSerializer)


def test_serialize_item(mocker, mongodb_obj):
    # Arrange
    mock_collection = mocker.MagicMock()
    mock_collection.collection_type.return_value = "distro"
    mock_item = mocker.MagicMock()
    mock_item.name = "testitem"
    mock_item.arch = "x86_64"
    mock_item.serialize.return_value = {"name": mock_item.name, "arch": mock_item.arch}

    # Act
    mongodb_obj.serialize_item(mock_collection, mock_item)

    # Assert
    assert len(list(mongodb_obj.mongodb["cobbler"]["distro"].find())) == 1


def test_serialize_delete(mocker, mongodb_obj):
    # Arrange
    mock_collection = mocker.MagicMock()
    mock_collection.collection_type.return_value = "distro"
    mock_item = mocker.MagicMock()
    mock_item.name = "testitem"

    # Act
    mongodb_obj.serialize_delete(mock_collection, mock_item)

    # Assert
    assert len(list(mongodb_obj.mongodb["cobbler"]["distro"].find())) == 0


def test_serialize(mocker, mongodb_obj):
    # Arrange
    mock_collection = mocker.MagicMock()
    mock_collection.collection_type.return_value = "distro"
    mock_serialize_item = mocker.patch.object(mongodb_obj, "serialize_item")
    mock_collection.__iter__ = mocker.Mock(return_value=iter(["item1"]))

    # Act
    mongodb_obj.serialize(mock_collection)

    # Assert
    assert mock_serialize_item.call_count == 1


def test_deserialize_raw(mongodb_obj):
    # Arrange
    collection_type = "distro"
    mongodb_obj.mongodb["cobbler"][collection_type].insert_one(
        {"name": "testitem", "arch": "x86_64"}
    )
    mongodb_obj.mongodb["cobbler"][collection_type].insert_one(
        {"name": "testitem2", "arch": "x86_64"}
    )

    # Act
    result = mongodb_obj.deserialize_raw(collection_type)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 2


def test_deserialize(mocker, mongodb_obj):
    # Arrange
    mock_collection = mocker.MagicMock()
    mock_collection.collection_type.return_value = "distro"
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
