"""
Tests that validate the functionality of the module that is responsible for managing the list of profile groups.
"""

from typing import Any, Callable, Dict, List

import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import profile_group
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import profile_group as item_profile_group


@pytest.fixture(name="profile_group_collection")
def fixture_profile_group_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (ProfileGroups) of a generic collection.
    """
    return cobbler_api.profile_groups()


def test_obj_create(collection_mgr: CollectionManager):
    """
    Test to verify that a collection object can be created.
    """
    # Arrange & Act
    collection = profile_group.ProfileGroups(collection_mgr)

    # Assert
    assert isinstance(collection, profile_group.ProfileGroups)


def test_profile_group_collection_factory_produce(
    cobbler_api: CobblerAPI, collection_mgr: CollectionManager
):
    collection = profile_group.ProfileGroups(collection_mgr)
    item_dict = {"name": "test_group", "members": ["profile1"]}
    item = collection.factory_produce(cobbler_api, item_dict)
    assert isinstance(item, item_profile_group.ProfileGroup)
    assert getattr(item, "name") == "test_group"
    assert getattr(item, "members") == ["profile1"]


def test_get(
    create_profile_group: Callable[[str], item_profile_group.ProfileGroup],
    profile_group_collection: profile_group.ProfileGroups,
):
    """
    Test to verify that an item can be retrieved from the collection by name.
    """
    # Arrange
    name = "test_get"
    create_profile_group(name)

    # Act
    item = profile_group_collection.get(name)
    fake_item = profile_group_collection.get("fake_name")

    # Assert
    assert isinstance(item, item_profile_group.ProfileGroup)
    assert item.name == name
    assert fake_item is None


def test_find(
    create_profile_group: Callable[[str], item_profile_group.ProfileGroup],
    profile_group_collection: profile_group.ProfileGroups,
):
    """
    Test to verify that an item can be found inside the collection.
    """
    # Arrange
    name = "test_find"
    create_profile_group(name)

    # Act
    result = profile_group_collection.find(True, True, name=name)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    create_profile_group: Callable[[str], item_profile_group.ProfileGroup],
    profile_group_collection: profile_group.ProfileGroups,
):
    """
    Test to verify that the collection can be converted to a list of dictionaries.
    """
    # Arrange
    name = "test_to_list"
    create_profile_group(name)

    # Act
    result = profile_group_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(
    profile_group_collection: profile_group.ProfileGroups,
):
    """
    Test to verify that the collection can be populated from a list of dictionaries.
    """
    # Arrange
    item_list: List[Dict[str, Any]] = [{"name": "test_from_list", "members": []}]

    # Act
    profile_group_collection.from_list(item_list)

    # Assert
    assert len(profile_group_collection.listing) == 1
    assert len(profile_group_collection.indexes["name"]) == 1


def test_copy(
    create_profile_group: Callable[[str], item_profile_group.ProfileGroup],
    profile_group_collection: profile_group.ProfileGroups,
):
    """
    Test to verify that an item can be copied inside the collection.
    """
    # Arrange
    name = "test_copy"
    item1 = create_profile_group(name)

    # Act
    new_item_name = "test_copy_new"
    profile_group_collection.copy(item1, new_item_name)
    item2: item_profile_group.ProfileGroup = profile_group_collection.find(False, name=new_item_name)  # type: ignore

    # Assert
    assert len(profile_group_collection.listing) == 2
    assert item1.uid in profile_group_collection.listing
    assert item2.uid in profile_group_collection.listing
    assert len(profile_group_collection.indexes["name"]) == 2
    assert (profile_group_collection.indexes["name"])[item1.name] == item1.uid
    assert (profile_group_collection.indexes["name"])[item2.name] == item2.uid


@pytest.mark.parametrize(
    "input_new_name",
    [
        "to_be_renamed",
        "UpperCase",
    ],
)
def test_rename(
    create_profile_group: Callable[[], item_profile_group.ProfileGroup],
    profile_group_collection: profile_group.ProfileGroups,
    input_new_name: str,
):
    """
    Test to verify that an item can be renamed inside the collection.
    """
    # Arrange
    item1 = create_profile_group()
    profile_group_collection.add(item1)

    # Act
    profile_group_collection.rename(item1, input_new_name)

    # Assert
    assert profile_group_collection.listing[item1.uid].name == input_new_name
    assert (profile_group_collection.indexes["name"])[input_new_name] == item1.uid


def test_collection_add(
    cobbler_api: CobblerAPI,
    profile_group_collection: profile_group.ProfileGroups,
):
    """
    Test to verify that an item can be added to the collection.
    """
    # Arrange
    name = "test_collection_add"
    item1 = item_profile_group.ProfileGroup(cobbler_api)
    item1.name = name  # type: ignore[method-assign]
    profile_group_collection.add(item1)

    # Act
    profile_group_collection.add(item1)

    # Assert
    assert item1.uid in profile_group_collection.listing
    assert name in profile_group_collection.indexes["name"]


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    create_profile_group: Callable[[str], item_profile_group.ProfileGroup],
    profile_group_collection: profile_group.ProfileGroups,
):
    """
    Test to verify that adding a duplicate item raises an exception.
    """
    # Arrange
    name = "test_duplicate_add"
    create_profile_group(name)
    item2 = item_profile_group.ProfileGroup(cobbler_api)
    item2.name = name  # type: ignore[method-assign]

    # Act & Assert
    with pytest.raises(CX):
        profile_group_collection.add(item2, check_for_duplicate_names=True)


def test_remove(
    create_profile_group: Callable[[str], item_profile_group.ProfileGroup],
    profile_group_collection: profile_group.ProfileGroups,
):
    """
    Test to verify that an item can be removed from the collection.
    """
    # Arrange
    name = "test_remove"
    item1 = create_profile_group(name)
    assert item1.uid in profile_group_collection.listing
    assert len(profile_group_collection.indexes["name"]) == 1
    assert (profile_group_collection.indexes["name"])[name] == item1.uid

    # Act
    profile_group_collection.remove(item1)

    # Assert
    assert item1.uid not in profile_group_collection.listing
    assert len(profile_group_collection.indexes["name"]) == 0


def test_indexes(
    profile_group_collection: profile_group.ProfileGroups,
):
    """
    Test to verify that the collection's indexes are initialized correctly.
    """
    # Arrange

    # Assert
    assert len(profile_group_collection.indexes) == 1
    assert len(profile_group_collection.indexes["name"]) == 0


def test_add_to_indexes(
    create_profile_group: Callable[[str], item_profile_group.ProfileGroup],
    profile_group_collection: profile_group.ProfileGroups,
):
    """
    Test to verify that an item can be added to the collection's indexes.
    """
    # Arrange
    name = "test_add_to_indexes"
    item1 = create_profile_group(name)

    # Act
    del (profile_group_collection.indexes["name"])[name]
    profile_group_collection.add_to_indexes(item1)

    # Assert
    assert name in profile_group_collection.indexes["name"]


def test_remove_from_indexes(
    create_profile_group: Callable[[str], item_profile_group.ProfileGroup],
    profile_group_collection: profile_group.ProfileGroups,
):
    """
    Test to verify that an item can be removed from the collection's indexes.
    """
    # Arrange
    name = "test_remove_from_indexes"
    item1 = create_profile_group(name)

    # Act
    profile_group_collection.remove_from_indexes(item1)

    # Assert
    assert name not in profile_group_collection.indexes["name"]


def test_update_indexes(
    create_profile_group: Callable[[], item_profile_group.ProfileGroup],
    profile_group_collection: profile_group.ProfileGroups,
):
    """
    Test to verify that the collection's indexes are updated correctly after modifying an item's attributes.
    """
    # Arrange
    item1 = create_profile_group()
    new_name = "test_update_indicies_post"

    # Act
    item1.name = new_name  # type: ignore[method-assign]

    # Assert
    assert profile_group_collection.indexes["name"][new_name] == item1.uid


def test_find_by_indexes(
    create_profile_group: Callable[[], item_profile_group.ProfileGroup],
    profile_group_collection: profile_group.ProfileGroups,
):
    """
    Test to verify that items can be found by various indexes.
    """
    # Arrange
    item1 = create_profile_group()
    kargs1 = {"name": item1.name}
    kargs2 = {"name": "fake_name"}
    kargs3 = {"fake_index": item1.uid}

    # Act
    result1 = profile_group_collection.find_by_indexes(kargs1)
    result2 = profile_group_collection.find_by_indexes(kargs2)
    result3 = profile_group_collection.find_by_indexes(kargs3)

    # Assert
    assert isinstance(result1, list)
    assert len(result1) == 1
    assert result1[0] == item1
    assert len(kargs1) == 0
    assert result2 is None
    assert len(kargs2) == 0
    assert result3 is None
    assert len(kargs3) == 1
