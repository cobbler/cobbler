"""
Tests that validate the functionality of the module that is responsible for managing the list of distros.
"""

import os.path
from typing import Callable

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import distros
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import distro


@pytest.fixture(name="distro_collection")
def fixture_distro_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (Distros) of a generic collection.
    """
    return cobbler_api.distros()


def test_obj_create(collection_mgr: CollectionManager):
    """
    Test to verify that a collection object can be created.
    """
    # Arrange & Act
    distro_collection = distros.Distros(collection_mgr)

    # Assert
    assert isinstance(distro_collection, distros.Distros)


def test_factory_produce(cobbler_api: CobblerAPI, distro_collection: distros.Distros):
    """
    Test to verify that a distro object can be created by the factory method of the collection.
    """
    # Arrange & Act
    result_distro = distro_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_distro, distro.Distro)


def test_get(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that a distro can be retrieved from the collection by name.
    """
    # Arrange
    name = "test_get"
    create_distro(name)

    # Act
    item = distro_collection.get(name)
    fake_item = distro_collection.get("fake_name")

    # Assert
    assert isinstance(item, distro.Distro)
    assert item.name == name
    assert fake_item is None


def test_find(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that a distro can be found inside the collection.
    """
    # Arrange
    name = "test_find"
    create_distro(name)

    # Act
    result = distro_collection.find(True, True, name=name)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that the collection can be converted to a list of dictionaries.
    """
    # Arrange
    name = "test_to_list"
    create_distro(name)

    # Act
    result = distro_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(
    distro_collection: distros.Distros,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
):
    """
    Test to verify that the collection can be populated from a list of dictionaries.
    """
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    test_kernel = os.path.join(folder, fk_kernel)
    item_list = [{"name": "test_from_list", "kernel": test_kernel}]

    # Act
    distro_collection.from_list(item_list)

    # Assert
    assert len(distro_collection.listing) == 1
    assert len(distro_collection.indexes["name"]) == 1
    assert len(distro_collection.indexes["arch"]) == 1


def test_copy(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that a distro can be copied inside the collection.
    """
    # Arrange
    name = "test_copy"
    item1 = create_distro(name)

    # Act
    new_item_name = "test_copy_new"
    distro_collection.copy(item1, new_item_name)
    item2: distro.Distro = distro_collection.find(False, name=new_item_name)  # type: ignore

    # Assert
    assert len(distro_collection.listing) == 2
    assert item1.uid in distro_collection.listing
    assert item2.uid in distro_collection.listing
    assert len(distro_collection.indexes["name"]) == 2
    assert (distro_collection.indexes["name"])[item1.name] == item1.uid
    assert (distro_collection.indexes["name"])[item2.name] == item2.uid
    assert (distro_collection.indexes["arch"])[item2.arch.value] == {
        item1.uid,
        item2.uid,
    }


@pytest.mark.parametrize(
    "input_new_name",
    [
        ("to_be_renamed"),
        ("UpperCase"),
    ],
)
def test_rename(
    create_distro: Callable[[], distro.Distro],
    distro_collection: distros.Distros,
    input_new_name: str,
):
    """
    Test to verify that a distro can be renamed inside the collection.
    """
    # Arrange
    item1 = create_distro()
    distro_collection.add(item1)

    # Act
    distro_collection.rename(item1, input_new_name)

    # Assert
    assert distro_collection.listing[item1.uid].name == input_new_name
    assert (distro_collection.indexes["name"])[input_new_name] == item1.uid
    assert (distro_collection.indexes["arch"])[item1.arch.value] == {item1.uid}


def test_collection_add(
    cobbler_api: CobblerAPI,
    distro_collection: distros.Distros,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
):
    """
    Test to verify that a distro can be added to the collection.
    """
    # Arrange
    name = "test_collection_add"
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    item1 = distro.Distro(cobbler_api)
    item1.name = name  # type: ignore[method-assign]
    item1.initrd = os.path.join(folder, fk_initrd)  # type: ignore
    item1.kernel = os.path.join(folder, fk_kernel)  # type: ignore
    distro_collection.add(item1)

    # Act
    distro_collection.add(item1)

    # Assert
    assert item1.uid in distro_collection.listing
    assert name in distro_collection.indexes["name"]
    assert item1.arch.value in distro_collection.indexes["arch"]


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
):
    """
    Test to verify that adding a duplicate distro raises an exception.
    """
    # Arrange
    name = "test_duplicate_add"
    create_distro(name)
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    item2 = distro.Distro(cobbler_api)
    item2.name = name  # type: ignore[method-assign]
    item2.initrd = os.path.join(folder, fk_initrd)  # type: ignore
    item2.kernel = os.path.join(folder, fk_kernel)  # type: ignore

    # Act & Assert
    with pytest.raises(CX):
        distro_collection.add(item2, check_for_duplicate_names=True)


def test_remove(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that a distro can be removed from the collection.
    """
    # Arrange
    name = "test_remove"
    item1 = create_distro(name)
    assert item1.uid in distro_collection.listing
    assert len(distro_collection.indexes["name"]) == 1
    assert (distro_collection.indexes["name"])[name] == item1.uid
    assert (distro_collection.indexes["arch"])[item1.arch.value] == {item1.uid}

    # Act
    distro_collection.remove(item1)

    # Assert
    assert item1.uid not in distro_collection.listing
    assert len(distro_collection.indexes["name"]) == 0
    assert len(distro_collection.indexes["arch"]) == 0


def test_indexes(
    distro_collection: distros.Distros,
):
    """
    Test to verify that the collection's indexes are initialized correctly.
    """
    # Arrange

    # Assert
    assert len(distro_collection.indexes) == 2
    assert len(distro_collection.indexes["name"]) == 0
    assert len(distro_collection.indexes["arch"]) == 0


def test_add_to_indexes(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that an item can be added to the collection's indexes.
    """
    # Arrange
    name = "test_add_to_indexes"
    item1 = create_distro(name)

    # Act
    del (distro_collection.indexes["name"])[name]
    del (distro_collection.indexes["arch"])[item1.arch.value]
    distro_collection.add_to_indexes(item1)

    # Assert
    assert name in distro_collection.indexes["name"]
    assert item1.arch.value in distro_collection.indexes["arch"]


def test_remove_from_indexes(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that an item can be removed from the collection's indexes.
    """
    # Arrange
    name = "test_remove_from_indexes"
    item1 = create_distro(name)

    # Act
    distro_collection.remove_from_indexes(item1)

    # Assert
    assert name not in distro_collection.indexes["name"]
    assert item1.arch.value not in distro_collection.indexes["arch"]


def test_update_indexes(
    create_distro: Callable[[], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that the collection's indexes are updated correctly after modifying an item's attributes.
    """
    # Arrange
    item1 = create_distro()
    new_name = "test_update_indicies_post"

    # Act
    item1.name = new_name  # type: ignore[method-assign]
    item1.arch = enums.Archs.I386  # type: ignore[method-assign]

    # Assert
    assert distro_collection.indexes["name"][new_name] == item1.uid
    assert distro_collection.indexes["arch"][enums.Archs.I386.value] == {item1.uid}


def test_find_by_indexes(
    create_distro: Callable[[], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that items can be found by various indexes.
    """
    # Arrange
    item1 = create_distro()
    kwargs1 = {"name": item1.name}
    kwargs2 = {"name": "fake_name"}
    kwargs3 = {"fake_index": item1.uid}
    kwargs4 = {"arch": item1.arch.value}
    kwargs5 = {"arch": "fake_arch"}

    # Act
    result1 = distro_collection.find_by_indexes(kwargs1)
    result2 = distro_collection.find_by_indexes(kwargs2)
    result3 = distro_collection.find_by_indexes(kwargs3)
    result4 = distro_collection.find_by_indexes(kwargs4)
    result5 = distro_collection.find_by_indexes(kwargs5)

    # Assert
    assert isinstance(result1, list)
    assert len(result1) == 1
    assert result1[0] == item1
    assert len(kwargs1) == 0
    assert result2 is None
    assert len(kwargs2) == 0
    assert result3 is None
    assert len(kwargs3) == 1
    assert result4 is not None
    assert len(result4) == 1
    assert len(kwargs4) == 0
    assert result5 is None
    assert len(kwargs5) == 0
