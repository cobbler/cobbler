"""
Tests that validate the functionality of the module that is responsible for managing the list of distro groups.
"""

from typing import Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import distro_group
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items.distro_group import DistroGroup


@pytest.fixture(name="distro_group_collection")
def fixture_distro_group_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (DistroGroups) of a generic collection.
    """
    return cobbler_api.distro_groups()


def test_obj_create(collection_mgr: CollectionManager):
    """
    Test to verify that a collection object can be created.
    """
    # Arrange & Act
    distro_group_collection = distro_group.DistroGroups(collection_mgr)

    # Assert
    assert isinstance(distro_group_collection, distro_group.DistroGroups)


def test_distro_group_factory_produce(
    cobbler_api: CobblerAPI, distro_group_collection: distro_group.DistroGroups
):
    """
    Test to verify that a distro group object can be created by the factory method of the collection.
    """
    # Arrange & Act
    result_distro_group = distro_group_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_distro_group, DistroGroup)


def test_get(
    create_distro_group: Callable[[str], DistroGroup],
    distro_group_collection: distro_group.DistroGroups,
):
    """
    Test to verify that a distro group can be retrieved from the collection by name.
    """
    # Arrange
    name = "test_get"
    create_distro_group(name)

    # Act
    item = distro_group_collection.get(name)
    fake_item = distro_group_collection.get("fake_name")

    # Assert
    assert isinstance(item, DistroGroup)
    assert item.name == name
    assert fake_item is None


def test_find(
    create_distro_group: Callable[[str], DistroGroup],
    distro_group_collection: distro_group.DistroGroups,
):
    """
    Test to verify that a distro group can be found inside the collection.
    """
    # Arrange
    name = "test_find"
    create_distro_group(name)

    # Act
    result = distro_group_collection.find(True, True, name=name)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    create_distro_group: Callable[[str], DistroGroup],
    distro_group_collection: distro_group.DistroGroups,
):
    """
    Test to verify that the collection can be converted to a list of dictionaries.
    """
    # Arrange
    name = "test_to_list"
    create_distro_group(name)

    # Act
    result = distro_group_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(
    distro_group_collection: distro_group.DistroGroups,
):
    """
    Test to verify that the collection can be populated from a list of dictionaries.
    """
    # Arrange
    item_list = [{"name": "test_from_list"}]

    # Act
    distro_group_collection.from_list(item_list)

    # Assert
    assert len(distro_group_collection.listing) == 1
    assert len(distro_group_collection.indexes["name"]) == 1


def test_copy(
    create_distro_group: Callable[[str], DistroGroup],
    distro_group_collection: distro_group.DistroGroups,
):
    """
    Test to verify that a distro group can be copied inside the collection.
    """
    # Arrange
    name = "test_copy"
    item1 = create_distro_group(name)

    # Act
    new_item_name = "test_copy_new"
    distro_group_collection.copy(item1, new_item_name)
    item2: DistroGroup = distro_group_collection.find(False, name=new_item_name)  # type: ignore

    # Assert
    assert len(distro_group_collection.listing) == 2
    assert item1.uid in distro_group_collection.listing
    assert item2.uid in distro_group_collection.listing
    assert len(distro_group_collection.indexes["name"]) == 2
    assert (distro_group_collection.indexes["name"])[item1.name] == item1.uid
    assert (distro_group_collection.indexes["name"])[item2.name] == item2.uid


@pytest.mark.parametrize(
    "input_new_name",
    [
        ("to_be_renamed"),
        ("UpperCase"),
    ],
)
def test_rename(
    create_distro_group: Callable[[], DistroGroup],
    distro_group_collection: distro_group.DistroGroups,
    input_new_name: str,
):
    """
    Test to verify that a distro group can be renamed inside the collection.
    """
    # Arrange
    item1 = create_distro_group()
    distro_group_collection.add(item1)

    # Act
    distro_group_collection.rename(item1, input_new_name)

    # Assert
    assert distro_group_collection.listing[item1.uid].name == input_new_name
    assert (distro_group_collection.indexes["name"])[input_new_name] == item1.uid


def test_collection_add(
    cobbler_api: CobblerAPI,
    distro_group_collection: distro_group.DistroGroups,
):
    """
    Test to verify that a distro group can be added to the collection.
    """
    # Arrange
    name = "test_collection_add"
    item1 = DistroGroup(cobbler_api)
    item1.name = name  # type: ignore[method-assign]

    # Act
    distro_group_collection.add(item1)

    # Assert
    assert item1.uid in distro_group_collection.listing
    assert name in distro_group_collection.indexes["name"]


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    create_distro_group: Callable[[str], DistroGroup],
    distro_group_collection: distro_group.DistroGroups,
):
    """
    Test to verify that adding a duplicate distro group raises an exception.
    """
    # Arrange
    name = "test_duplicate_add"
    create_distro_group(name)
    item2 = DistroGroup(cobbler_api)
    item2.name = name  # type: ignore[method-assign]

    # Act & Assert
    with pytest.raises(CX):
        distro_group_collection.add(item2, check_for_duplicate_names=True)


def test_remove(
    create_distro_group: Callable[[str], DistroGroup],
    distro_group_collection: distro_group.DistroGroups,
):
    """
    Test to verify that a distro group can be removed from the collection.
    """
    # Arrange
    name = "test_remove"
    item1 = create_distro_group(name)
    assert item1.uid in distro_group_collection.listing
    assert len(distro_group_collection.indexes["name"]) == 1
    assert (distro_group_collection.indexes["name"])[name] == item1.uid

    # Act
    distro_group_collection.remove(item1)

    # Assert
    assert item1.uid not in distro_group_collection.listing
    assert len(distro_group_collection.indexes["name"]) == 0


def test_indexes(
    distro_group_collection: distro_group.DistroGroups,
):
    """
    Test to verify that the collection's indexes are initialized correctly.
    """
    # Arrange

    # Assert
    assert len(distro_group_collection.indexes) == 1
    assert len(distro_group_collection.indexes["name"]) == 0


def test_add_to_indexes(
    create_distro_group: Callable[[str], DistroGroup],
    distro_group_collection: distro_group.DistroGroups,
):
    """
    Test to verify that an item can be added to the collection's indexes.
    """
    # Arrange
    name = "test_add_to_indexes"
    item1 = create_distro_group(name)

    # Act
    del (distro_group_collection.indexes["name"])[name]
    distro_group_collection.add_to_indexes(item1)

    # Assert
    assert name in distro_group_collection.indexes["name"]


def test_remove_from_indexes(
    create_distro_group: Callable[[str], DistroGroup],
    distro_group_collection: distro_group.DistroGroups,
):
    """
    Test to verify that an item can be removed from the collection's indexes.
    """
    # Arrange
    name = "test_remove_from_indexes"
    item1 = create_distro_group(name)

    # Act
    distro_group_collection.remove_from_indexes(item1)

    # Assert
    assert name not in distro_group_collection.indexes["name"]


def test_update_indexes(
    create_distro_group: Callable[[], DistroGroup],
    distro_group_collection: distro_group.DistroGroups,
):
    """
    Test to verify that the collection's indexes are updated correctly after modifying an item's attributes.
    """
    # Arrange
    item1 = create_distro_group()
    new_name = "test_update_indicies_post"

    # Act
    item1.name = new_name  # type: ignore[method-assign]

    # Assert
    assert distro_group_collection.indexes["name"][new_name] == item1.uid


def test_find_by_indexes(
    create_distro_group: Callable[[], DistroGroup],
    distro_group_collection: distro_group.DistroGroups,
):
    """
    Test to verify that items can be found by various indexes.
    """
    # Arrange
    item1 = create_distro_group()
    kargs1 = {"name": item1.name}
    kargs2 = {"name": "fake_name"}
    kargs3 = {"fake_index": item1.uid}

    # Act
    result1 = distro_group_collection.find_by_indexes(kargs1)
    result2 = distro_group_collection.find_by_indexes(kargs2)
    result3 = distro_group_collection.find_by_indexes(kargs3)

    # Assert
    assert isinstance(result1, list)
    assert len(result1) == 1
    assert result1[0] == item1
    assert len(kargs1) == 0
    assert result2 is None
    assert len(kargs2) == 0
    assert result3 is None
    assert len(kargs3) == 1
