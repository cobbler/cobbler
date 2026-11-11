"""
Tests that validate the functionality of the module that is responsible for abstracting access to the item
(de)serializers.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cobbler import serializer, utils
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
    filelock_mock = mocker.patch("cobbler.utils.filelock")
    mocker.patch.object(serializer_obj, "storage_object")
    input_collection = mocker.MagicMock()

    # Act
    serializer_obj.serialize(input_collection)

    # Assert
    filelock_mock.assert_called_once_with(serializer_obj.lock_file_location)


def test_serialize_item(mocker: "MockerFixture", serializer_obj: serializer.Serializer):
    """
    Verify that a single item can be written with the help of the configured serialization module.
    """
    # Arrange
    filelock_mock = mocker.patch("cobbler.utils.filelock")
    mtime_open_mock = mocker.patch("builtins.open", mocker.mock_open())
    input_collection = mocker.MagicMock()
    input_item = mocker.MagicMock()
    storage_object_mock = mocker.patch.object(serializer_obj, "storage_object")

    # Act
    serializer_obj.serialize_item(input_collection, input_item)

    # Assert
    storage_object_mock.serialize_item.assert_called_with(input_collection, input_item)
    filelock_mock.assert_called_once_with(serializer_obj.lock_file_location)
    # __touch_mtime() writes the collection mtime file while still holding the lock.
    mtime_open_mock.assert_called_once_with(
        serializer_obj.api.mtime_location, "w", encoding="UTF-8"
    )


def test_serialize_releases_lock_on_exception(
    mocker: "MockerFixture", serializer_obj: serializer.Serializer, tmp_path: Path
):
    """
    Regression test: the lock must be released even if the wrapped serialize call raises -
    otherwise every subsequent serialize/deserialize call in this process, and in any other
    process, would block forever waiting for a lock that is never coming back. Points the
    serializer at a temp lock file (not the real ``/var/lib/cobbler/lock``) so this exercises the
    real ``utils.filelock()`` mechanism end-to-end rather than mocking it away.
    """
    # Arrange
    serializer_obj.lock_file_location = str(tmp_path / "test.lock")
    storage_object_mock = mocker.patch.object(serializer_obj, "storage_object")
    storage_object_mock.serialize.side_effect = RuntimeError("boom")
    input_collection = mocker.MagicMock()

    # Act
    with pytest.raises(RuntimeError, match="boom"):
        serializer_obj.serialize(input_collection)

    # Assert - the lock was actually released: a fresh acquisition must succeed immediately
    # instead of blocking forever on a lock nothing will ever release.
    with utils.filelock(serializer_obj.lock_file_location):
        pass


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
