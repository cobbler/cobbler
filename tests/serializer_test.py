"""
Tests that validate the functionality of the module that is responsible for abstracting access to the item
(de)serializers.
"""

import fcntl
from typing import TYPE_CHECKING

import pytest

from cobbler import serializer
from cobbler.api import CobblerAPI

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="serializer_obj")
def fixture_serializer_obj(cobbler_api: CobblerAPI) -> serializer.Serializer:
    """
    Fixture to provide a fresh serializer instance object for every test.
    """
    return serializer.Serializer(cobbler_api)


def test_create_object(cobbler_api: CobblerAPI):
    """
    Verify if the serializer can be initialized with a valid cobbler_api instance.
    """
    # Arrange, Act & Assert
    assert isinstance(serializer.Serializer(cobbler_api), serializer.Serializer)


def test_serialize(mocker: "MockerFixture", serializer_obj: serializer.Serializer):
    """
    Verify that a full collection can be written with the help of the configured serialization module.
    """
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
    # One access for __grab_lock; releasing reuses that same handle rather than reopening the
    # lock file (reopening it would unlock/close a different, unrelated open file description
    # and leak the one that actually holds the flock - see the real root-cause bug this guards
    # against).
    assert mock_lock_file_location.call_count == 1


def test_serialize_item(mocker: "MockerFixture", serializer_obj: serializer.Serializer):
    """
    Verify that a single item can be written with the help of the configured serialization module.
    """
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
    # One access for __grab_lock, one for the mtime file write - releasing the lock no longer
    # reopens the lock file itself.
    assert mock_lock_file_location.call_count == 2


def test_serialize_releases_lock_on_exception(
    mocker: "MockerFixture", serializer_obj: serializer.Serializer
):
    """
    Regression test: the lock must be released even if the wrapped serialize call raises -
    otherwise every subsequent serialize/deserialize call in this process, and in any other
    process, would block forever waiting for a lock that is never coming back.
    """
    # Arrange
    open_mock = mocker.MagicMock()
    open_mock.fileno.return_value = 5
    mocker.patch("builtins.open", return_value=mocker.mock_open(mock=open_mock))
    flock_mock = mocker.patch("fcntl.flock")
    mocker.patch("os.path.exists", return_value=True)
    storage_object_mock = mocker.patch.object(serializer_obj, "storage_object")
    storage_object_mock.serialize.side_effect = RuntimeError("boom")
    input_collection = mocker.MagicMock()

    # Act
    with pytest.raises(RuntimeError, match="boom"):
        serializer_obj.serialize(input_collection)

    # Assert - the lock was still unlocked and the handle closed despite the exception.
    flock_mock.assert_called_with(5, fcntl.LOCK_UN)
    open_mock.close.assert_called_once()


def test_serialize_delete(
    mocker: "MockerFixture", serializer_obj: serializer.Serializer
):
    """
    Verify that a single item can be deleted with the help of the configured serialization module.
    """
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


def test_deserialize(mocker: "MockerFixture", serializer_obj: serializer.Serializer):
    """
    Verify that a full collection can be read with the help of the configured serialization module.
    """
    # Arrange
    storage_object_mock = mocker.patch.object(serializer_obj, "storage_object")
    input_collection = mocker.MagicMock()

    # Act
    serializer_obj.deserialize(input_collection)

    # Assert
    storage_object_mock.deserialize.assert_called_with(input_collection, True)


def test_deserialize_item(
    mocker: "MockerFixture", serializer_obj: serializer.Serializer
):
    """
    Verify that a single item can be read with the help of the configured serialization module.
    """
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
