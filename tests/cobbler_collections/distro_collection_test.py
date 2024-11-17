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


@pytest.fixture
def distro_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (Distros) of a generic collection.
    """
    return cobbler_api.distros()


def test_obj_create(collection_mgr: CollectionManager):
    # Arrange & Act
    distro_collection = distros.Distros(collection_mgr)

    # Assert
    assert isinstance(distro_collection, distros.Distros)


def test_factory_produce(cobbler_api: CobblerAPI, distro_collection: distros.Distros):
    # Arrange & Act
    result_distro = distro_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_distro, distro.Distro)


def test_get(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
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
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    # Arrange
    name = "test_find"
    create_distro(name)

    # Act
    result = distro_collection.find(name, True, True)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
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
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    test_kernel = os.path.join(folder, fk_kernel)
    item_list = [{"name": "test_from_list", "kernel": test_kernel}]

    # Act
    distro_collection.from_list(item_list)

    # Assert
    assert len(distro_collection.listing) == 1
    assert len(distro_collection.indexes["uid"]) == 1
    assert len(distro_collection.indexes["arch"]) == 1


def test_copy(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    # Arrange
    name = "test_copy"
    item1 = create_distro(name)

    # Act
    new_item_name = "test_copy_new"
    distro_collection.copy(item1, new_item_name)
    item2: distro.Distro = distro_collection.find(new_item_name, False)  # type: ignore

    # Assert
    assert len(distro_collection.listing) == 2
    assert name in distro_collection.listing
    assert new_item_name in distro_collection.listing
    assert len(distro_collection.indexes["uid"]) == 2
    assert (distro_collection.indexes["uid"])[item1.uid] == name
    assert (distro_collection.indexes["uid"])[item2.uid] == new_item_name
    assert (distro_collection.indexes["arch"])[item2.arch.value] == {
        name,
        new_item_name,
    }


@pytest.mark.parametrize(
    "input_new_name",
    [
        ("to_be_renamed"),
        ("UpperCase"),
    ],
)
def test_rename(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    distro_collection: distros.Distros,
    input_new_name: str,
):
    # Arrange
    item1 = create_distro()
    distro_collection.add(item1)

    # Act
    distro_collection.rename(item1, input_new_name)

    # Assert
    assert input_new_name in distro_collection.listing
    assert distro_collection.listing[input_new_name].name == input_new_name
    assert (distro_collection.indexes["uid"])[item1.uid] == input_new_name
    assert (distro_collection.indexes["arch"])[item1.arch.value] == {input_new_name}


def test_collection_add(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
):
    # Arrange
    name = "test_collection_add"
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    item1 = distro.Distro(cobbler_api)
    item1.name = name
    item1.initrd = os.path.join(folder, fk_initrd)
    item1.kernel = os.path.join(folder, fk_kernel)
    distro_collection.add(item1)

    # Act
    distro_collection.add(item1)

    # Assert
    assert name in distro_collection.listing
    assert item1.uid in distro_collection.indexes["uid"]
    assert item1.arch.value in distro_collection.indexes["arch"]


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
):
    # Arrange
    name = "test_duplicate_add"
    create_distro(name)
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    item2 = distro.Distro(cobbler_api)
    item2.name = name
    item2.initrd = os.path.join(folder, fk_initrd)
    item2.kernel = os.path.join(folder, fk_kernel)

    # Act & Assert
    with pytest.raises(CX):
        distro_collection.add(item2, check_for_duplicate_names=True)


def test_remove(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    # Arrange
    name = "test_remove"
    item1 = create_distro(name)
    assert name in distro_collection.listing
    assert len(distro_collection.indexes["uid"]) == 1
    assert (distro_collection.indexes["uid"])[item1.uid] == item1.name
    assert (distro_collection.indexes["arch"])[item1.arch.value] == {item1.name}

    # Act
    distro_collection.remove(name)

    # Assert
    assert name not in distro_collection.listing
    assert len(distro_collection.indexes["uid"]) == 0
    assert len(distro_collection.indexes["arch"]) == 0


def test_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    # Arrange

    # Assert
    assert len(distro_collection.indexes) == 2
    assert len(distro_collection.indexes["uid"]) == 0
    assert len(distro_collection.indexes["arch"]) == 0


def test_add_to_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    # Arrange
    name = "test_add_to_indexes"
    item1 = create_distro(name)

    # Act
    del (distro_collection.indexes["uid"])[item1.uid]
    del (distro_collection.indexes["arch"])[item1.arch.value]
    distro_collection.add_to_indexes(item1)

    # Assert
    assert item1.uid in distro_collection.indexes["uid"]
    assert item1.arch.value in distro_collection.indexes["arch"]


def test_remove_from_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    # Arrange
    name = "test_remove_from_indexes"
    item1 = create_distro(name)

    # Act
    distro_collection.remove_from_indexes(item1)

    # Assert
    assert item1.uid not in distro_collection.indexes["uid"]
    assert item1.arch.value not in distro_collection.indexes["arch"]


def test_update_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    distro_collection: distros.Distros,
):
    # Arrange
    name = "test_update_indexes"
    item1 = create_distro()
    uid1_test = "test_uid"

    # Act
    item1.uid = uid1_test
    item1.arch = enums.Archs.I386

    # Assert
    assert distro_collection.indexes["uid"][uid1_test] == name
    assert distro_collection.indexes["arch"][enums.Archs.I386.value] == {name}


def test_find_by_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    distro_collection: distros.Distros,
):
    # Arrange
    item1 = create_distro()
    kargs1 = {"uid": item1.uid}
    kargs2 = {"uid": "fake_uid"}
    kargs3 = {"fake_index": item1.uid}
    kargs4 = {"arch": item1.arch.value}
    kargs5 = {"arch": "fake_arch"}

    # Act
    result1 = distro_collection.find_by_indexes(kargs1)
    result2 = distro_collection.find_by_indexes(kargs2)
    result3 = distro_collection.find_by_indexes(kargs3)
    result4 = distro_collection.find_by_indexes(kargs4)
    result5 = distro_collection.find_by_indexes(kargs5)

    # Assert
    assert isinstance(result1, list)
    assert len(result1) == 1
    assert result1[0] == item1
    assert len(kargs1) == 0
    assert result2 is None
    assert len(kargs2) == 0
    assert result3 is None
    assert len(kargs3) == 1
    assert result4 is not None
    assert len(result4) == 1
    assert len(kargs4) == 0
    assert result5 is None
    assert len(kargs5) == 0
