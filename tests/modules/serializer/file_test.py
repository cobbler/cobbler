import json
import os
import pathlib

from unittest.mock import Mock, MagicMock
import pytest
from cobbler.cobbler_collections.collection import Collection
from cobbler.modules.serializers import file
from cobbler.cexceptions import CX
from cobbler.settings import Settings
from tests.conftest import does_not_raise


@pytest.fixture(scope="function", autouse=True)
def restore_libpath():
    file.libpath = "/var/lib/cobbler/collections"


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


def test_find_double_json_files_1(tmpdir: pathlib.Path):
    # Arrange
    file_one = tmpdir.join("double.json")
    file_double = tmpdir.join("double.json.json")
    with open(file_double, "w") as duplicate:
        duplicate.write('double\n')

    # Act
    file.__find_double_json_files(file_one)

    # Assert
    assert os.path.isfile(file_one)


def test_find_double_json_files_raise(tmpdir: pathlib.Path):
    # Arrange
    file_one = tmpdir.join("double.json")
    file_double = tmpdir.join("double.json.json")
    with open(file_one, "w") as duplicate:
        duplicate.write('one\n')
    with open(file_double, "w") as duplicate:
        duplicate.write('double\n')

    # Act and assert
    with pytest.raises(FileExistsError):
        file.__find_double_json_files(file_one)


def test_serialize_item_raise():
    # Arrange
    mitem = Mock()
    mcollection = Mock()
    mitem.name = ""

    # Act and assert
    with pytest.raises(CX):
        file.serialize_item(mcollection, mitem)


def test_serialize_item(tmpdir: pathlib.Path):
    # Arrange
    file.libpath = tmpdir
    os.mkdir(os.path.join(tmpdir, "distros"))
    expected_file = os.path.join(tmpdir, "distros", "test_serializer.json")
    mitem = Mock()
    mitem.name = "test_serializer"
    mcollection = Mock()
    mcollection.collection_types.return_value = "distros"
    mitem.serialize.return_value = {"name": mitem.name}

    # Act
    file.serialize_item(mcollection, mitem)

    # Assert
    assert os.path.exists(expected_file)
    with open(expected_file, "r") as json_file:
        assert json.load(json_file) == mitem.serialize()


def test_serialize_delete(tmpdir: pathlib.Path):
    # Arrange
    mitem = Mock()
    mitem.name = "test_serializer_del"
    mcollection = Mock()
    file.libpath = tmpdir
    mcollection.collection_types.return_value = "distros"
    os.mkdir(os.path.join(tmpdir, mcollection.collection_types()))
    expected_path = os.path.join(tmpdir, mcollection.collection_types(), mitem.name + ".json")
    pathlib.Path(expected_path).touch()

    # Act
    file.serialize_delete(mcollection, mitem)

    # Assert
    assert not os.path.exists(expected_path)


@pytest.mark.parametrize("input_collection_type,input_collection", [
    ("settings", {}),
    ("distros", MagicMock())
])
def test_serialize(input_collection_type, input_collection, mocker):
    # Arrange
    stub = mocker.stub()
    mocker.patch("cobbler.modules.serializers.file.serialize_item", new=stub)
    if input_collection_type == "settings":
        mock = Settings()
    else:
        mocker.patch("cobbler.cobbler_collections.collection.Collection.collection_types",
                     return_value=input_collection_type)
        mocker.patch("cobbler.cobbler_collections.collection.Collection.collection_type",
                     return_value="")
        mock = Collection(MagicMock())
        mock.listing["test"] = input_collection

    # Act
    file.serialize(mock)

    # Assert
    if input_collection_type == "settings":
        assert not stub.called
    else:
        assert stub.called
        stub.assert_called_with(mock, input_collection)


@pytest.mark.parametrize("input_collection_type,expected_result,settings_read", [
    ("settings", {}, True),
    ("distros", [], False),
])
def test_deserialize_raw(input_collection_type, expected_result, settings_read, mocker):
    # Arrange
    mocker.patch("cobbler.settings.read_settings_file", return_value=expected_result)

    # Act
    result = file.deserialize_raw(input_collection_type)

    # Assert
    assert result == expected_result


@pytest.mark.parametrize("input_collection_type,input_collection,input_topological,expected_result", [
    ("settings", {}, True, {}),
    ("settings", {}, False, {}),
    ("distros", [{'depth': 2, 'name': False}, {'depth': 1, 'name': True}], True,
     [{'depth': 1, 'name': True}, {'depth': 2, 'name': False}]),
    ("distros", [{'depth': 2, 'name': False}, {'depth': 1, 'name': True}], False,
     [{'depth': 2, 'name': False}, {'depth': 1, 'name': True}]),
    ("distros", [{'name': False}, {'name': True}], True, [{'name': False}, {'name': True}]),
    ("distros", [{'name': False}, {'name': True}], False, [{'name': False}, {'name': True}]),
])
def test_deserialize(input_collection_type, input_collection, input_topological, expected_result, mocker):
    # Arrange
    mocker.patch("cobbler.modules.serializers.file.deserialize_raw", return_value=input_collection)
    if input_collection_type == "settings":
        stub_from = mocker.stub(name="from_dict_stub")
        mock = Settings()
        mocker.patch.object(mock, "from_dict", new=stub_from)
    else:
        stub_from = mocker.stub(name="from_list_stub")
        mock = Collection(MagicMock())
        mocker.patch.object(mock, "from_list", new=stub_from)
        mocker.patch("cobbler.cobbler_collections.collection.Collection.collection_types",
                     return_value=input_collection_type)

    # Act
    file.deserialize(mock, input_topological)

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
    mocker,
    input_collection_type,
    input_item,
    expected_result,
    expected_exception,
):
    # Arrange
    mocked_input = mocker.mock_open(read_data=json.dumps(input_item))()
    mocker.patch("builtins.open", return_value=mocked_input)

    # Act
    with expected_exception:
        result = file.deserialize_item(
            input_collection_type, expected_result["name"]
        )

        # Assert
        assert result == expected_result
