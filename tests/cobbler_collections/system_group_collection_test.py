"""
Tests that validate the functionality of the module that is responsible for managing the list of system groups.
"""

from typing import Any, Callable, Dict, List

import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import system_group
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import system_group as item_system_group


@pytest.fixture(name="system_group_collection")
def fixture_system_group_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (SystemGroups) of a generic collection.
    """
    return cobbler_api.system_groups()


def test_obj_create(collection_mgr: CollectionManager):
    """
    Test to verify that a collection object can be created.
    """
    # Arrange & Act
    collection = system_group.SystemGroups(collection_mgr)

    # Assert
    assert isinstance(collection, system_group.SystemGroups)


def test_system_group_collection_factory_produce(
    cobbler_api: CobblerAPI, collection_mgr: CollectionManager
):
    collection = system_group.SystemGroups(collection_mgr)
    item_dict = {"name": "test_group", "members": ["system1"]}
    item = collection.factory_produce(cobbler_api, item_dict)
    assert isinstance(item, item_system_group.SystemGroup)
    assert getattr(item, "name") == "test_group"
    assert getattr(item, "members") == ["system1"]


def test_get(
    create_system_group: Callable[[str], item_system_group.SystemGroup],
    system_group_collection: system_group.SystemGroups,
):
    """
    Test to verify that an item can be retrieved from the collection by name.
    """
    # Arrange
    name = "test_get"
    create_system_group(name)

    # Act
    item = system_group_collection.get(name)
    fake_item = system_group_collection.get("fake_name")

    # Assert
    assert isinstance(item, item_system_group.SystemGroup)
    assert item.name == name
    assert fake_item is None


def test_find(
    create_system_group: Callable[[str], item_system_group.SystemGroup],
    system_group_collection: system_group.SystemGroups,
):
    """
    Test to verify that an item can be found inside the collection.
    """
    # Arrange
    name = "test_find"
    create_system_group(name)

    # Act
    result = system_group_collection.find(True, True, name=name)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    create_system_group: Callable[[str], item_system_group.SystemGroup],
    system_group_collection: system_group.SystemGroups,
):
    """
    Test to verify that the collection can be converted to a list of dictionaries.
    """
    # Arrange
    name = "test_to_list"
    create_system_group(name)

    # Act
    result = system_group_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(
    system_group_collection: system_group.SystemGroups,
):
    """
    Test to verify that the collection can be populated from a list of dictionaries.
    """
    # Arrange
    item_list: List[Dict[str, Any]] = [{"name": "test_from_list", "members": []}]

    # Act
    system_group_collection.from_list(item_list)

    # Assert
    assert len(system_group_collection.listing) == 1
    assert len(system_group_collection.indexes["name"]) == 1


def test_copy(
    create_system_group: Callable[[str], item_system_group.SystemGroup],
    system_group_collection: system_group.SystemGroups,
):
    """
    Test to verify that an item can be copied inside the collection.
    """
    # Arrange
    name = "test_copy"
    item1 = create_system_group(name)

    # Act
    new_item_name = "test_copy_new"
    system_group_collection.copy(item1, new_item_name)
    item2: item_system_group.SystemGroup = system_group_collection.find(False, name=new_item_name)  # type: ignore

    # Assert
    assert len(system_group_collection.listing) == 2
    assert item1.uid in system_group_collection.listing
    assert item2.uid in system_group_collection.listing
    assert len(system_group_collection.indexes["name"]) == 2
    assert (system_group_collection.indexes["name"])[item1.name] == item1.uid
    assert (system_group_collection.indexes["name"])[item2.name] == item2.uid


@pytest.mark.parametrize(
    "input_new_name",
    [
        ("to_be_renamed"),
        ("UpperCase"),
    ],
)
def test_rename(
    create_system_group: Callable[[], item_system_group.SystemGroup],
    system_group_collection: system_group.SystemGroups,
    input_new_name: str,
):
    """
    Test to verify that an item can be renamed inside the collection.
    """
    # Arrange
    item1 = create_system_group()
    system_group_collection.add(item1)

    # Act
    system_group_collection.rename(item1, input_new_name)

    # Assert
    assert system_group_collection.listing[item1.uid].name == input_new_name
    assert (system_group_collection.indexes["name"])[input_new_name] == item1.uid


def test_collection_add(
    cobbler_api: CobblerAPI,
    system_group_collection: system_group.SystemGroups,
):
    """
    Test to verify that an item can be added to the collection.
    """
    # Arrange
    name = "test_collection_add"
    item1 = item_system_group.SystemGroup(cobbler_api)
    item1.name = name  # type: ignore[method-assign]
    system_group_collection.add(item1)

    # Act
    system_group_collection.add(item1)

    # Assert
    assert item1.uid in system_group_collection.listing
    assert name in system_group_collection.indexes["name"]


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    create_system_group: Callable[[str], item_system_group.SystemGroup],
    system_group_collection: system_group.SystemGroups,
):
    """
    Test to verify that adding a duplicate item raises an exception.
    """
    # Arrange
    name = "test_duplicate_add"
    create_system_group(name)
    item2 = item_system_group.SystemGroup(cobbler_api)
    item2.name = name  # type: ignore[method-assign]

    # Act & Assert
    with pytest.raises(CX):
        system_group_collection.add(item2, check_for_duplicate_names=True)


def test_remove(
    create_system_group: Callable[[str], item_system_group.SystemGroup],
    system_group_collection: system_group.SystemGroups,
):
    """
    Test to verify that an item can be removed from the collection.
    """
    # Arrange
    name = "test_remove"
    item1 = create_system_group(name)
    assert item1.uid in system_group_collection.listing
    assert len(system_group_collection.indexes["name"]) == 1
    assert (system_group_collection.indexes["name"])[name] == item1.uid

    # Act
    system_group_collection.remove(item1)

    # Assert
    assert item1.uid not in system_group_collection.listing
    assert len(system_group_collection.indexes["name"]) == 0


def test_indexes(
    system_group_collection: system_group.SystemGroups,
):
    """
    Test to verify that the collection's indexes are initialized correctly.
    """
    # Arrange

    # Assert
    assert len(system_group_collection.indexes) == 1
    assert len(system_group_collection.indexes["name"]) == 0


def test_add_to_indexes(
    create_system_group: Callable[[str], item_system_group.SystemGroup],
    system_group_collection: system_group.SystemGroups,
):
    """
    Test to verify that an item can be added to the collection's indexes.
    """
    # Arrange
    name = "test_add_to_indexes"
    item1 = create_system_group(name)

    # Act
    del (system_group_collection.indexes["name"])[name]
    system_group_collection.add_to_indexes(item1)

    # Assert
    assert name in system_group_collection.indexes["name"]


def test_remove_from_indexes(
    create_system_group: Callable[[str], item_system_group.SystemGroup],
    system_group_collection: system_group.SystemGroups,
):
    """
    Test to verify that an item can be removed from the collection's indexes.
    """
    # Arrange
    name = "test_remove_from_indexes"
    item1 = create_system_group(name)

    # Act
    system_group_collection.remove_from_indexes(item1)

    # Assert
    assert name not in system_group_collection.indexes["name"]


def test_update_indexes(
    create_system_group: Callable[[], item_system_group.SystemGroup],
    system_group_collection: system_group.SystemGroups,
):
    """
    Test to verify that the collection's indexes are updated correctly after modifying an item's attributes.
    """
    # Arrange
    item1 = create_system_group()
    new_name = "test_update_indicies_post"

    # Act
    item1.name = new_name  # type: ignore[method-assign]

    # Assert
    assert system_group_collection.indexes["name"][new_name] == item1.uid


def test_find_by_indexes(
    create_system_group: Callable[[], item_system_group.SystemGroup],
    system_group_collection: system_group.SystemGroups,
):
    """
    Test to verify that items can be found by various indexes.
    """
    # Arrange
    item1 = create_system_group()
    kargs1 = {"name": item1.name}
    kargs2 = {"name": "fake_name"}
    kargs3 = {"fake_index": item1.uid}

    # Act
    result1 = system_group_collection.find_by_indexes(kargs1)
    result2 = system_group_collection.find_by_indexes(kargs2)
    result3 = system_group_collection.find_by_indexes(kargs3)

    # Assert
    assert isinstance(result1, list)
    assert len(result1) == 1
    assert result1[0] == item1
    assert len(kargs1) == 0
    assert result2 is None
    assert len(kargs2) == 0
    assert result3 is None
    assert len(kargs3) == 1
