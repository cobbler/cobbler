import os.path

import pytest

from cobbler.cexceptions import CX
from cobbler.cobbler_collections import distros
from cobbler.items import distro


@pytest.fixture
def distro_collection(collection_mgr):
    return distros.Distros(collection_mgr)


def test_obj_create(collection_mgr):
    # Arrange & Act
    distro_collection = distros.Distros(collection_mgr)

    # Assert
    assert isinstance(distro_collection, distros.Distros)


def test_factory_produce(cobbler_api, distro_collection):
    # Arrange & Act
    result_distro = distro_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_distro, distro.Distro)


def test_get(cobbler_api, distro_collection):
    # Arrange
    name = "test_get"
    item1 = distro.Distro(cobbler_api)
    item1.name = name
    distro_collection.add(item1)

    # Act
    item = distro_collection.get(name)

    # Assert
    assert isinstance(item, distro.Distro)
    assert item.name == name


def test_find(cobbler_api, distro_collection):
    # Arrange
    name = "test_find"
    item1 = distro.Distro(cobbler_api)
    item1.name = name
    distro_collection.add(item1)

    # Act
    result = distro_collection.find(name, True, True)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(cobbler_api, distro_collection):
    # Arrange
    name = "test_to_list"
    item1 = distro.Distro(cobbler_api)
    item1.name = name
    distro_collection.add(item1)

    # Act
    result = distro_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(distro_collection):
    # Arrange
    item_list = [{"name": "test_from_list"}]

    # Act
    distro_collection.from_list(item_list)

    # Assert
    assert len(distro_collection.listing) == 1


def test_copy(cobbler_api, distro_collection, create_kernel_initrd, fk_initrd, fk_kernel):
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    name = "test_copy"
    item1 = distro.Distro(cobbler_api)
    item1.name = name
    item1.initrd = os.path.join(folder, fk_initrd)
    item1.kernel = os.path.join(folder, fk_kernel)
    distro_collection.add(item1)

    # Act
    new_item_name = "test_copy_successful"
    distro_collection.copy(item1, new_item_name)

    # Assert
    assert len(distro_collection.listing) == 2
    assert name in distro_collection.listing
    assert new_item_name in distro_collection.listing


def test_rename(cobbler_api, distro_collection):
    # Arrange
    name = "to_be_renamed"
    item1 = distro.Distro(cobbler_api)
    item1.name = name
    distro_collection.add(item1)

    # Act
    new_name = "new_name"
    distro_collection.rename(item1, new_name)

    # Assert
    assert new_name in distro_collection.listing
    assert distro_collection.listing.get(new_name).name == new_name


def test_collection_add(cobbler_api, distro_collection):
    # Arrange
    name = "collection_add"
    item1 = distro.Distro(cobbler_api)
    item1.name = name

    # Act
    distro_collection.add(item1)

    # Assert
    assert name in distro_collection.listing


def test_duplicate_add(cobbler_api, distro_collection):
    # Arrange
    name = "duplicate_name"
    item1 = distro.Distro(cobbler_api)
    item1.name = name
    distro_collection.add(item1)
    item2 = distro.Distro(cobbler_api)
    item2.name = name

    # Act & Assert
    with pytest.raises(CX):
        distro_collection.add(item2, check_for_duplicate_names=True)


def test_remove(cobbler_api, distro_collection):
    # Arrange
    name = "to_be_removed"
    item1 = distro.Distro(cobbler_api)
    item1.name = name
    distro_collection.add(item1)
    assert name in distro_collection.listing

    # Act
    distro_collection.remove(name)

    # Assert
    assert name not in distro_collection.listing


@pytest.mark.skip("Method which is under test is broken!")
def test_to_string(cobbler_api, distro_collection):
    # Arrange
    name = "to_string"
    item1 = distro.Distro(cobbler_api)
    item1.name = name
    distro_collection.add(item1)

    # Act
    result = distro_collection.to_string()

    # Assert
    print(result)
    assert False
