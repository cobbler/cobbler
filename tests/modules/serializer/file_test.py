import json
import os
import pathlib
from unittest.mock import MagicMock

import pytest

from cobbler.cobbler_collections.collection import Collection
from cobbler.modules.serializers import file
from cobbler.cexceptions import CX
from cobbler.settings import Settings


@pytest.fixture()
def serializer_obj(cobbler_api):
    return file.FileSerializer(cobbler_api)


def test_register():
    # Arrange
    # Act
    result = file.register()

    # Assert
    assert isinstance(result, str)
    assert result == "serializer"


def test_what():
    # Arrange
    # Act
    result = file.what()

    # Assert
    assert isinstance(result, str)
    assert result == "serializer/file"


def test_storage_factory(cobbler_api):
    # Arrange

    # Act
    result = file.storage_factory(cobbler_api)

    # Assert
    assert isinstance(result, file.FileSerializer)


def test_find_double_json_files_1(tmpdir: pathlib.Path):
    # Arrange
    file_one = tmpdir / "double.json"
    file_double = tmpdir / "double.json.json"
    with open(file_double, "w") as duplicate:
        duplicate.write("double\n")

    # Act
    file._find_double_json_files(str(file_one))

    # Assert
    assert os.path.isfile(file_one)


def test_find_double_json_files_raise(tmpdir: pathlib.Path):
    # Arrange
    file_one = tmpdir / "double.json"
    file_double = tmpdir / "double.json.json"
    with open(file_one, "w") as duplicate:
        duplicate.write("one\n")
    with open(file_double, "w") as duplicate:
        duplicate.write("double\n")

    # Act and assert
    with pytest.raises(FileExistsError):
        file._find_double_json_files(str(file_one))


def test_serialize_item_raise(mocker, serializer_obj):
    # Arrange
    mitem = mocker.Mock()
    mcollection = mocker.Mock()
    mitem.name = ""

    # Act and assert
    with pytest.raises(CX):
        serializer_obj.serialize_item(mcollection, mitem)


def test_serialize_item(mocker, tmpdir: pathlib.Path, serializer_obj):
    # Arrange
    serializer_obj.libpath = tmpdir
    os.mkdir(os.path.join(tmpdir, "distros"))
    expected_file = os.path.join(tmpdir, "distros", "test_serializer.json")
    mitem = mocker.Mock()
    mitem.name = "test_serializer"
    mcollection = mocker.Mock()
    mcollection.collection_types.return_value = "distros"
    mitem.serialize.return_value = {"name": mitem.name}

    # Act
    serializer_obj.serialize_item(mcollection, mitem)

    # Assert
    assert os.path.exists(expected_file)
    with open(expected_file, "r") as json_file:
        assert json.load(json_file) == mitem.serialize()


def test_serialize_delete(mocker, tmpdir: pathlib.Path, serializer_obj):
    # Arrange
    mitem = mocker.Mock()
    mitem.name = "test_serializer_del"
    mcollection = mocker.Mock()
    serializer_obj.libpath = tmpdir
    mcollection.collection_types.return_value = "distros"
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
def test_serialize(mocker, input_collection_type, input_collection, serializer_obj):
    # Arrange
    stub = mocker.stub()
    mocker.patch.object(serializer_obj, "serialize_item", new=stub)
    if input_collection_type == "settings":
        mock = Settings()
    else:
        mocker.patch(
            "cobbler.cobbler_collections.collection.Collection.collection_types",
            return_value=input_collection_type,
        )
        mocker.patch(
            "cobbler.cobbler_collections.collection.Collection.collection_type",
            return_value="",
        )
        mock = Collection(mocker.MagicMock())
        mock.listing["test"] = input_collection

    # Act
    serializer_obj.serialize(mock)

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
    mocker, input_collection_type, expected_result, settings_read, serializer_obj
):
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
    mocker,
    input_collection_type,
    input_collection,
    input_topological,
    expected_result,
    serializer_obj,
):
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
        mock = Collection(MagicMock())
        mocker.patch.object(mock, "from_list", new=stub_from)
        mocker.patch(
            "cobbler.cobbler_collections.collection.Collection.collection_types",
            return_value=input_collection_type,
        )

    # Act
    serializer_obj.deserialize(mock, input_topological)

    # Assert
    assert stub_from.called
    stub_from.assert_called_with(expected_result)
