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
from cobbler.modules.serializers import file
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
def serializer_obj(cobbler_api: CobblerAPI):
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


def test_find_double_json_files_1(tmpdir: pathlib.Path):
    """
    Test that will assert if JSON files with duplicated file extension are correctly cleaned up.
    """
    # Arrange
    file_one = tmpdir / "double.json"
    file_double = tmpdir / "double.json.json"
    with open(file_double, "w") as duplicate:
        duplicate.write("double\n")

    # Act
    file._find_double_json_files(str(file_one))  # type: ignore

    # Assert
    assert os.path.isfile(file_one)


def test_find_double_json_files_raise(tmpdir: pathlib.Path):
    """
    Test that will assert if a rename operation for a duplicated JSON fill will correctly raise.
    """
    # Arrange
    file_one = tmpdir / "double.json"
    file_double = tmpdir / "double.json.json"
    with open(file_one, "w", encoding="UTF-8") as duplicate:
        duplicate.write("one\n")
    with open(file_double, "w", encoding="UTF-8") as duplicate:
        duplicate.write("double\n")

    # Act and assert
    with pytest.raises(FileExistsError):
        file._find_double_json_files(str(file_one))  # type: ignore


def test_serialize_item_raise(
    mocker: MockerFixture, serializer_obj: file.FileSerializer
):
    # Arrange
    mitem = mocker.Mock()
    mcollection = mocker.Mock()
    mitem.name = ""

    # Act and assert
    with pytest.raises(CX):
        serializer_obj.serialize_item(mcollection, mitem)


def test_serialize_item(
    tmpdir: pathlib.Path, serializer_obj: file.FileSerializer, cobbler_api: CobblerAPI
):
    """
    Test that will assert if a given item can be written to disk successfully.
    """
    # Arrange
    serializer_obj.libpath = str(tmpdir)
    mitem = MockItem(cobbler_api)
    mitem.name = "test_serializer"
    mcollection = MockCollection(cobbler_api._collection_mgr)  # type: ignore
    os.mkdir(os.path.join(tmpdir, mcollection.collection_types()))
    expected_file = os.path.join(
        tmpdir, mcollection.collection_types(), f"{mitem.name}.json"
    )

    # Act
    serializer_obj.serialize_item(mcollection, mitem)

    # Assert
    assert os.path.exists(expected_file)
    with open(expected_file, "r", encoding="UTF-8") as json_file:
        assert json.load(json_file) == mitem.serialize()


def test_serialize_delete(
    tmpdir: pathlib.Path, serializer_obj: file.FileSerializer, cobbler_api: CobblerAPI
):
    """
    Test that will assert if a given item can be deleted.
    """
    # Arrange
    mitem = MockItem(cobbler_api)
    mitem.name = "test_serializer_del"
    mcollection = MockCollection(cobbler_api._collection_mgr)  # type: ignore
    serializer_obj.libpath = str(tmpdir)
    os.mkdir(os.path.join(tmpdir, mcollection.collection_types()))
    expected_path = os.path.join(
        tmpdir, mcollection.collection_types(), mitem.name + ".json"
    )
    pathlib.Path(expected_path).touch()

    # Act
    serializer_obj.serialize_delete(mcollection, mitem)

    # Assert
    assert not os.path.exists(expected_path)


@pytest.mark.parametrize(
    "input_collection_type,input_collection",
    [("settings", {}), ("distros", MagicMock())],
)
def test_serialize(
    mocker: MockerFixture,
    input_collection_type: str,
    input_collection: Union[Dict[Any, Any], MagicMock],
    serializer_obj: file.FileSerializer,
):
    # Arrange
    stub = mocker.stub()
    mocker.patch.object(serializer_obj, "serialize_item", new=stub)
    if input_collection_type == "settings":
        mock = Settings()
    else:
        mock = MockCollection(mocker.MagicMock())
        mock.listing["test"] = input_collection
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
            {"name": "test"},
            {"name": "test", "inmemory": True},
            does_not_raise(),
        ),
        (
            "distros",
            {"name": "test"},
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
    serializer_obj: file.FileSerializer,
):
    """
    TODO
    """
    # Arrange
    mocked_input = mocker.mock_open(read_data=json.dumps(input_item))()
    mocker.patch("builtins.open", return_value=mocked_input)

    # Act
    with expected_exception:
        result = serializer_obj.deserialize_item(
            input_collection_type, expected_result["name"]  # type: ignore[reportGeneralTypeIssues]
        )

        # Assert
        assert result == expected_result
