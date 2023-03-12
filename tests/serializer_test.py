import pytest

from cobbler import serializer


@pytest.fixture()
def serializer_obj(cobbler_api):
    return serializer.Serializer(cobbler_api)


def test_create_object(cobbler_api):
    # Arrange, Act & Assert
    assert isinstance(serializer.Serializer(cobbler_api), serializer.Serializer)


def test_serialize(mocker, serializer_obj):
    # Arrange
    open_mock = mocker.MagicMock()
    open_mock.fileno.return_value = 5
    mock_lock_file_location = mocker.patch(
        "builtins.open", return_value=mocker.mock_open(mock=open_mock)
    )
    mocker.patch("fcntl.flock")
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch.object(serializer_obj, "storage_object")
    input_collection = mocker.MagicMock()

    # Act
    serializer_obj.serialize(input_collection)

    # Assert
    # One access for __grab_lock and one for __release_lock
    assert mock_lock_file_location.call_count == 2


def test_serialize_item(mocker, serializer_obj):
    # Arrange
    open_mock = mocker.MagicMock()
    open_mock.fileno.return_value = 5
    mock_lock_file_location = mocker.patch(
        "builtins.open", return_value=mocker.mock_open(mock=open_mock)
    )
    mocker.patch("fcntl.flock")
    mocker.patch("os.path.exists", return_value=True)
    input_collection = mocker.MagicMock()
    input_item = mocker.MagicMock()
    storage_object_mock = mocker.patch.object(serializer_obj, "storage_object")

    # Act
    serializer_obj.serialize_item(input_collection, input_item)

    # Assert
    storage_object_mock.serialize_item.assert_called_with(input_collection, input_item)
    # One access for __grab_lock
    # Two access for __release_lock (mtime is true in this case)
    assert mock_lock_file_location.call_count == 3


def test_serialize_delete(mocker, serializer_obj):
    # Arrange
    input_collection = mocker.MagicMock()
    input_item = mocker.MagicMock()
    storage_object_mock = mocker.patch.object(serializer_obj, "storage_object")

    # Act
    serializer_obj.serialize_delete(input_collection, input_item)

    # Assert
    storage_object_mock.serialize_delete.assert_called_with(
        input_collection, input_item
    )


def test_deserialize(mocker, serializer_obj):
    # Arrange
    storage_object_mock = mocker.patch.object(serializer_obj, "storage_object")
    input_collection = mocker.MagicMock()

    # Act
    serializer_obj.deserialize(input_collection)

    # Assert
    storage_object_mock.deserialize.assert_called_with(input_collection, True)


def test_deserialize_item(mocker, serializer_obj):
    # Arrange
    storage_object_mock = mocker.patch.object(serializer_obj, "storage_object")
    input_collection_type = mocker.MagicMock()
    input_name = mocker.MagicMock()

    # Act
    serializer_obj.deserialize_item(input_collection_type, input_name)

    # Assert
    storage_object_mock.deserialize_item.assert_called_with(
        input_collection_type, input_name
    )
