"""
Tests that validate the functionality of the module that is responsible for (de)serializing items to JSON files.
"""

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
from cobbler.items.abstract.bootable_item import BootableItem
from cobbler.modules.serializers import file
from cobbler.settings import Settings

from tests.conftest import does_not_raise


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
def fixture_serializer_obj(cobbler_api: CobblerAPI):
    """
    Generates an empty serializer object that is ready to be used.
    """
    return file.FileSerializer(cobbler_api)


def test_register():
    """
    Test that will assert if the return value of the register method is correct.
    """
    # Arrange
    # Act
    result = file.register()

    # Assert
    assert isinstance(result, str)
    assert result == "serializer"


def test_what():
    """
    Test that will assert if the return value of the identity hook of the module is correct.
    """
    # Arrange
    # Act
    result = file.what()

    # Assert
    assert isinstance(result, str)
    assert result == "serializer/file"


def test_storage_factory(cobbler_api: CobblerAPI):
    """
    Test that will assert if the factory can successfully generate a FileSerializer object.
    """
    # Arrange

    # Act
    result = file.storage_factory(cobbler_api)

    # Assert
    assert isinstance(result, file.FileSerializer)


def test_serialize_item(
    mocker: "MockerFixture",
    tmpdir: pathlib.Path,
    serializer_obj: file.FileSerializer,
    cobbler_api: CobblerAPI,
):
    """
    Test that will assert if a given item can be written to disk successfully.
    """
    # pylint: disable=protected-access
    # Arrange
    mcollection = MockCollection(cobbler_api._collection_mgr)  # type: ignore
    mock_get_items = mocker.patch.object(cobbler_api, "get_items")
    mock_get_items.return_value = mcollection
    serializer_obj.libpath = str(tmpdir)
    mitem = MockBootableItem(cobbler_api)
    mitem.name = "test_serializer"  # type: ignore[method-assign]

    os.mkdir(os.path.join(tmpdir, mcollection.collection_types()))
    expected_file = os.path.join(
        tmpdir, mcollection.collection_types(), f"{mitem.uid}.json"
    )

    # Act
    serializer_obj.serialize_item(mcollection, mitem)

    # Assert
    assert os.path.exists(expected_file)
    with open(expected_file, "r", encoding="UTF-8") as json_file:
        assert json.load(json_file) == mitem.serialize()


def test_serialize_delete(
    mocker: "MockerFixture",
    tmpdir: pathlib.Path,
    serializer_obj: file.FileSerializer,
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
    serializer_obj.libpath = str(tmpdir)
    os.mkdir(os.path.join(tmpdir, mcollection.collection_types()))
    expected_path = os.path.join(
        tmpdir, mcollection.collection_types(), mitem.uid + ".json"
    )
    pathlib.Path(expected_path).touch()

    # Act
    serializer_obj.serialize_delete(mcollection, mitem)

    # Assert
    assert not os.path.exists(expected_path)


@pytest.mark.parametrize(
    "input_collection_type,input_collection",
    [("distros", MagicMock())],
)
def test_serialize(
    mocker: MockerFixture,
    input_collection_type: str,
    input_collection: Union[Dict[Any, Any], MagicMock],
    serializer_obj: file.FileSerializer,
):
    """
    Test to verify that serializing a whole collection is working as expected.
    """
    # Arrange
    stub = mocker.stub()
    mocker.patch.object(serializer_obj, "serialize_item", new=stub)
    mock: Union[Settings, MockCollection]
    if input_collection_type == "settings":
        mock = Settings()
    else:
        mock = MockCollection(mocker.MagicMock())
        mock.listing["test"] = input_collection  # type: ignore
        mocker.patch.object(mock, "collection_type", return_value="")
        mocker.patch.object(
            mock, "collection_types", return_value=input_collection_type
        )

    # Act
    serializer_obj.serialize(mock)  # type: ignore

    # Assert
    if input_collection_type == "settings":
        assert not stub.called
    else:
        assert stub.called
        stub.assert_called_with(mock, input_collection)


@pytest.mark.parametrize(
    "input_collection_type,expected_result",
    [
        ("distros", []),
    ],
)
def test_deserialize_raw(
    mocker: MockerFixture,
    input_collection_type: str,
    expected_result: Union[List[Any], Dict[Any, Any]],
    serializer_obj: file.FileSerializer,
):
    """
    Test that will assert if a given item can be deserilized in raw.
    """
    # Arrange
    mocker.patch("cobbler.settings.read_settings_file", return_value=expected_result)

    # Act
    result = serializer_obj.deserialize_raw(input_collection_type)

    # Assert
    assert result == expected_result


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
    serializer_obj: file.FileSerializer,
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
    mock: Union[Settings, MockCollection]
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

    # Assert
    assert stub_from.called
    stub_from.assert_called_with(expected_result)


@pytest.mark.parametrize(
    "input_collection_type,input_item,expected_result,expected_exception",
    [
        (
            "distros",
            {"uid": "8b1fe974e7a240bfb5639976ab64b4fb", "name": "test"},
            {
                "uid": "8b1fe974e7a240bfb5639976ab64b4fb",
                "name": "test",
                "inmemory": True,
            },
            does_not_raise(),
        ),
        (
            "distros",
            {"uid": "8b1fe974e7a240bfb5639976ab64b4fb", "name": "test"},
            {
                "uid": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "name": "fake",
                "inmemory": True,
            },
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
    serializer_obj: file.FileSerializer,
):
    """
    Test to verify that deserializing a single item works.
    """
    # Arrange
    mocked_input = mocker.mock_open(read_data=json.dumps(input_item))()
    mocker.patch("builtins.open", return_value=mocked_input)

    # Act
    with expected_exception:
        result = serializer_obj.deserialize_item(
            input_collection_type, expected_result["uid"]  # type: ignore[reportGeneralTypeIssues,arg-type]
        )

        # Assert
        assert result == expected_result
