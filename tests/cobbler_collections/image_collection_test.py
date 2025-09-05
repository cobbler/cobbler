"""
Tests that validate the functionality of the module that is responsible for managing the list of images.
"""

import os.path
from typing import Any, Callable

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import images
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import image, menu

from tests.conftest import does_not_raise


@pytest.fixture(name="image_collection")
def fixture_image_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (Images) of a generic collection.
    """
    return cobbler_api.images()


def test_obj_create(collection_mgr: CollectionManager):
    """
    Test the creation of an Images collection.
    """
    # Arrange & Act
    image_collection = images.Images(collection_mgr)

    # Assert
    assert isinstance(image_collection, images.Images)


def test_factory_produce(cobbler_api: CobblerAPI, image_collection: images.Images):
    """
    Test the factory method to produce an Image item.
    """
    # Arrange & Act
    result_image = image_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_image, image.Image)


def test_get(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    """
    Test retrieving an image by name.
    """
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
    """
    Test to verify that an image can be found inside the collection.
    """
    # Arrange
    name = "test_find"
    create_image(name)

    # Act
    result = image_collection.find(True, True, name=name)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    """
    Test converting the collection to a list of dictionaries.
    """
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
    """
    Test populating the collection from a list of dictionaries.
    """
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    test_kernel = os.path.join(folder, fk_kernel)
    item_list = [{"name": "test_from_list", "file": test_kernel}]

    # Act
    image_collection.from_list(item_list)

    # Assert
    assert len(image_collection.listing) == 1
    assert len(image_collection.indexes["name"]) == 1
    assert len(image_collection.indexes["arch"]) == 1
    assert len(image_collection.indexes["menu"]) == 1


def test_copy(
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    """
    Test copying an existing image to a new image with a different name.
    """
    # Arrange
    name = "test_copy"
    item1 = create_image(name)

    # Act
    new_item_name = "test_copy_new"
    image_collection.copy(item1, new_item_name)
    item2 = image_collection.find(False, name=new_item_name)

    # Assert
    assert len(image_collection.listing) == 2
    assert item1.uid in image_collection.listing
    assert item2.uid in image_collection.listing  # type: ignore
    assert len(image_collection.indexes["name"]) == 2
    assert isinstance(item2, image.Image)
    assert (image_collection.indexes["name"])[name] == item1.uid
    assert (image_collection.indexes["name"])[new_item_name] == item2.uid
    assert (image_collection.indexes["arch"])[item1.arch.value] == {
        item1.uid,
        item2.uid,
    }
    assert (image_collection.indexes["arch"])[item2.arch.value] == {
        item1.uid,
        item2.uid,
    }
    assert (image_collection.indexes["menu"])[item1.menu] == {item1.uid, item2.uid}
    assert (image_collection.indexes["menu"])[item2.menu] == {item1.uid, item2.uid}


@pytest.mark.parametrize(
    "input_new_name",
    [
        ("to_be_renamed"),
        ("UpperCase"),
    ],
)
def test_rename(
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
    input_new_name: str,
):
    """
    Test renaming an existing image in the collection.
    """
    # Arrange
    item1 = create_image("test_rename")

    # Act
    image_collection.rename(item1, input_new_name)

    # Assert
    assert item1.uid in image_collection.listing
    assert image_collection.listing[item1.uid].name == input_new_name
    assert (image_collection.indexes["name"])[input_new_name] == item1.uid
    assert (image_collection.indexes["arch"])[item1.arch.value] == {item1.uid}
    assert (image_collection.indexes["menu"])[item1.menu] == {item1.uid}


def test_collection_add(
    cobbler_api: CobblerAPI,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
    image_collection: images.Images,
):
    """
    Test adding a new image to the collection.
    """
    # Arrange
    name = "test_collection_add"
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    item1 = image.Image(cobbler_api)
    item1.name = name  # type: ignore[method-assign]
    item1.file = os.path.join(folder, fk_initrd)  # type: ignore[method-assign]

    # Act
    image_collection.add(item1)

    # Assert
    assert item1.uid in image_collection.listing
    assert item1.name in image_collection.indexes["name"]
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
    """
    Test that adding a duplicate image name raises an exception.
    """
    # Arrange
    name = "test_duplicate_add"
    create_image(name)
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    item2 = image.Image(cobbler_api)
    item2.name = name  # type: ignore[method-assign]
    item2.file = os.path.join(folder, fk_initrd)  # type: ignore[method-assign]

    # Act & Assert
    with pytest.raises(CX):
        image_collection.add(item2, check_for_duplicate_names=True)


def test_remove(
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    """
    Test removing an image from the collection.
    """
    # Arrange
    name = "test_remove"
    item1 = create_image(name)
    assert item1.uid in image_collection.listing
    assert len(image_collection.indexes["name"]) == 1
    assert (image_collection.indexes["name"])[item1.name] == item1.uid
    assert len(image_collection.indexes["arch"]) == 1
    assert (image_collection.indexes["arch"])[item1.arch.value] == {item1.uid}
    assert len(image_collection.indexes["menu"]) == 1
    assert (image_collection.indexes["menu"])[item1.menu] == {item1.uid}

    # Act
    image_collection.remove(item1)

    # Assert
    assert item1.uid not in image_collection.listing
    assert len(image_collection.indexes["name"]) == 0
    assert len(image_collection.indexes["arch"]) == 0
    assert len(image_collection.indexes["menu"]) == 0


@pytest.mark.parametrize(
    "recursive,expected_exception,expected_result",
    [
        (False, pytest.raises(CX), 1),
        (True, does_not_raise(), 0),
    ],
)
def test_remove_by_menu_dependency(
    cobbler_api: CobblerAPI,
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Test removing an image from the collection.
    """
    # Arrange
    name = "test_remove"
    item1 = create_image(name)
    test_menu = cobbler_api.new_menu()
    test_menu.name = "test_menu"  # type: ignore[method-assign]
    cobbler_api.menus().add(test_menu)
    item1.menu = test_menu.uid  # type: ignore[method-assign]

    # Act
    with expected_exception:
        cobbler_api.menus().remove(test_menu, recursive=recursive)

    # Assert
    assert (item1.uid not in image_collection.listing) == recursive
    assert len(image_collection.indexes["name"]) == expected_result
    assert len(image_collection.indexes["arch"]) == expected_result
    assert len(image_collection.indexes["menu"]) == expected_result


def test_indexes(
    image_collection: images.Images,
):
    """
    Test the initial state of the indexes in the collection.
    """
    # Arrange

    # Assert
    assert len(image_collection.indexes) == 3
    assert len(image_collection.indexes["name"]) == 0
    assert len(image_collection.indexes["arch"]) == 0
    assert len(image_collection.indexes["menu"]) == 0


def test_add_to_indexes(
    create_image: Callable[[str], image.Image],
    image_collection: images.Images,
):
    """
    Test adding an image to the collection's indexes.
    """
    # Arrange
    name = "test_add_to_indexes"
    item1 = create_image(name)

    # Act
    del (image_collection.indexes["name"])[item1.name]
    del (image_collection.indexes["arch"])[item1.arch.value]
    del (image_collection.indexes["menu"])[item1.menu]
    image_collection.add_to_indexes(item1)

    # Assert
    assert item1.name in image_collection.indexes["name"]
    assert item1.arch.value in image_collection.indexes["arch"]
    assert item1.menu in image_collection.indexes["menu"]


def test_remove_from_indexes(
    create_image: Callable[[], image.Image],
    image_collection: images.Images,
):
    """
    Test removing an image from the collection's indexes.
    """
    # Arrange
    item1 = create_image()

    # Act
    image_collection.remove_from_indexes(item1)

    # Assert
    assert item1.name not in image_collection.indexes["name"]
    assert item1.arch.value not in image_collection.indexes["arch"]
    assert item1.menu not in image_collection.indexes["menu"]


def test_update_indexes(
    cobbler_api: CobblerAPI,
    create_image: Callable[[], image.Image],
    image_collection: images.Images,
):
    """
    Test updating the indexes after modifying an image's attributes.
    """
    # Arrange
    item1 = create_image()
    new_name = "test_update_indicies_post"
    menu1 = menu.Menu(cobbler_api)
    menu1.name = "test_update_indexes"  # type: ignore[method-assign]
    cobbler_api.menus().add(menu1)

    # Act
    item1.name = new_name  # type: ignore[method-assign]
    item1.arch = enums.Archs.I386  # type: ignore[method-assign]
    item1.menu = menu1.uid  # type: ignore[method-assign]

    # Assert
    assert image_collection.indexes["name"][new_name] == item1.uid
    assert image_collection.indexes["arch"][enums.Archs.I386.value] == {item1.uid}
    assert image_collection.indexes["menu"][menu1.uid] == {item1.uid}


def test_find_by_indexes(
    create_image: Callable[[], image.Image],
    image_collection: images.Images,
):
    """
    Test finding images by various indexes.
    """
    # Arrange
    item1 = create_image()
    kargs1 = {"name": item1.name}
    kargs2 = {"name": "fake_uid"}
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
