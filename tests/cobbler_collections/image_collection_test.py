import os.path
from typing import Callable

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import images
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import image, menu


@pytest.fixture
def image_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (Images) of a generic collection.
    """
    return cobbler_api.images()


def test_obj_create(collection_mgr: CollectionManager):
    # Arrange & Act
    image_collection = images.Images(collection_mgr)

    # Assert
    assert isinstance(image_collection, images.Images)


def test_factory_produce(cobbler_api: CobblerAPI, image_collection: images.Images):
    # Arrange & Act
    result_image = image_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_image, image.Image)


def test_get(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    # Arrange
    name = "test_get"
    create_image(name)

    # Act
    item = image_collection.get(name)
    fake_item = image_collection.get("fake_name")

    # Assert
    assert isinstance(item, image.Image)
    assert item.name == name
    assert fake_item is None


def test_find(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    # Arrange
    name = "test_find"
    create_image(name)

    # Act
    result = image_collection.find(name, True, True)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    # Arrange
    name = "test_to_list"
    create_image(name)

    # Act
    result = image_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(
    image_collection: images.Images,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
):
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    test_kernel = os.path.join(folder, fk_kernel)
    item_list = [{"name": "test_from_list", "file": test_kernel}]

    # Act
    image_collection.from_list(item_list)

    # Assert
    assert len(image_collection.listing) == 1
    assert len(image_collection.indexes["uid"]) == 1
    assert len(image_collection.indexes["arch"]) == 1
    assert len(image_collection.indexes["menu"]) == 1


def test_copy(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    # Arrange
    name = "test_copy"
    item1 = create_image(name)

    # Act
    new_item_name = "test_copy_new"
    image_collection.copy(item1, new_item_name)
    item2 = image_collection.find(new_item_name, False)

    # Assert
    assert len(image_collection.listing) == 2
    assert name in image_collection.listing
    assert new_item_name in image_collection.listing
    assert len(image_collection.indexes["uid"]) == 2
    assert isinstance(item2, image.Image)
    assert (image_collection.indexes["uid"])[item1.uid] == name
    assert (image_collection.indexes["uid"])[item2.uid] == new_item_name
    assert (image_collection.indexes["arch"])[item1.arch.value] == {name, new_item_name}
    assert (image_collection.indexes["arch"])[item2.arch.value] == {name, new_item_name}
    assert (image_collection.indexes["menu"])[item1.menu] == {name, new_item_name}
    assert (image_collection.indexes["menu"])[item2.menu] == {name, new_item_name}


@pytest.mark.parametrize(
    "input_new_name",
    [
        ("to_be_renamed"),
        ("UpperCase"),
    ],
)
def test_rename(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
    input_new_name: str,
):
    # Arrange
    item1 = create_image("test_rename")

    # Act
    image_collection.rename(item1, input_new_name)

    # Assert
    assert input_new_name in image_collection.listing
    assert image_collection.listing[input_new_name].name == input_new_name
    assert (image_collection.indexes["uid"])[item1.uid] == input_new_name
    assert (image_collection.indexes["arch"])[item1.arch.value] == {input_new_name}
    assert (image_collection.indexes["menu"])[item1.menu] == {input_new_name}


def test_collection_add(
    cobbler_api: CobblerAPI,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
    image_collection: images.Images,
):
    # Arrange
    name = "test_collection_add"
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    item1 = image.Image(cobbler_api)
    item1.name = name
    item1.file = os.path.join(folder, fk_initrd)

    # Act
    image_collection.add(item1)

    # Assert
    assert name in image_collection.listing
    assert item1.uid in image_collection.indexes["uid"]
    assert item1.arch.value in image_collection.indexes["arch"]
    assert item1.menu in image_collection.indexes["menu"]


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
    image_collection: images.Images,
):
    # Arrange
    name = "test_duplicate_add"
    create_image(name)
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    item2 = image.Image(cobbler_api)
    item2.name = name
    item2.file = os.path.join(folder, fk_initrd)

    # Act & Assert
    with pytest.raises(CX):
        image_collection.add(item2, check_for_duplicate_names=True)


def test_remove(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    # Arrange
    name = "test_remove"
    item1 = create_image(name)
    assert name in image_collection.listing
    assert len(image_collection.indexes["uid"]) == 1
    assert (image_collection.indexes["uid"])[item1.uid] == item1.name
    assert len(image_collection.indexes["arch"]) == 1
    assert (image_collection.indexes["arch"])[item1.arch.value] == {item1.name}
    assert len(image_collection.indexes["menu"]) == 1
    assert (image_collection.indexes["menu"])[item1.menu] == {item1.name}

    # Act
    image_collection.remove(name)

    # Assert
    assert name not in image_collection.listing
    assert len(image_collection.indexes["uid"]) == 0
    assert len(image_collection.indexes["arch"]) == 0
    assert len(image_collection.indexes["menu"]) == 0


def test_indexes(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    # Arrange

    # Assert
    assert len(image_collection.indexes) == 3
    assert len(image_collection.indexes["uid"]) == 0
    assert len(image_collection.indexes["arch"]) == 0
    assert len(image_collection.indexes["menu"]) == 0


def test_add_to_indexes(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    # Arrange
    name = "test_add_to_indexes"
    item1 = create_image(name)

    # Act
    del (image_collection.indexes["uid"])[item1.uid]
    del (image_collection.indexes["arch"])[item1.arch.value]
    del (image_collection.indexes["menu"])[item1.menu]
    image_collection.add_to_indexes(item1)

    # Assert
    assert item1.uid in image_collection.indexes["uid"]
    assert item1.arch.value in image_collection.indexes["arch"]
    assert item1.menu in image_collection.indexes["menu"]


def test_remove_from_indexes(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    # Arrange
    name = "test_remove_from_indexes"
    item1 = create_image(name)

    # Act
    image_collection.remove_from_indexes(item1)

    # Assert
    assert item1.uid not in image_collection.indexes["uid"]
    assert item1.arch.value not in image_collection.indexes["arch"]
    assert item1.menu not in image_collection.indexes["menu"]


def test_update_indexes(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    # Arrange
    name = "test_update_indexes"
    item1 = create_image(name)
    uid1_test = "test_uid"
    menu1 = menu.Menu(cobbler_api)
    menu1.name = "test_update_indexes"
    cobbler_api.menus().add(menu1)

    # Act
    item1.uid = uid1_test
    item1.arch = enums.Archs.I386
    item1.menu = menu1.name

    # Assert
    assert image_collection.indexes["uid"][uid1_test] == name
    assert image_collection.indexes["arch"][enums.Archs.I386.value] == {name}
    assert image_collection.indexes["menu"][menu1.name] == {name}


def test_find_by_indexes(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    # Arrange
    name = "to_be_removed"
    item1 = create_image(name)
    kargs1 = {"uid": item1.uid}
    kargs2 = {"uid": "fake_uid"}
    kargs3 = {"fake_index": item1.uid}
    kargs4 = {"menu": ""}
    kargs5 = {"menu": "fake_menu"}
    kargs6 = {"arch": item1.arch.value}
    kargs7 = {"arch": "fake_arch"}

    # Act
    result1 = image_collection.find_by_indexes(kargs1)
    result2 = image_collection.find_by_indexes(kargs2)
    result3 = image_collection.find_by_indexes(kargs3)
    result4 = image_collection.find_by_indexes(kargs4)
    result5 = image_collection.find_by_indexes(kargs5)
    result6 = image_collection.find_by_indexes(kargs6)
    result7 = image_collection.find_by_indexes(kargs7)

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
    assert result6 is not None
    assert len(result6) == 1
    assert len(kargs6) == 0
    assert result7 is None
    assert len(kargs7) == 0
