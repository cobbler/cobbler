"""
Tests that validate the functionality of the module that is responsible for managing the list of menus.
"""

import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import menus
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import menu


@pytest.fixture(name="menu_collection")
def fixture_menu_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (Menus) of a generic collection.
    """
    return cobbler_api.menus()


def test_obj_create(collection_mgr: CollectionManager):
    """
    Test the creation of a Menus collection object.
    """
    # Arrange & Act
    menu_collection = menus.Menus(collection_mgr)

    # Assert
    assert isinstance(menu_collection, menus.Menus)


def test_factory_produce(cobbler_api: CobblerAPI, menu_collection: menus.Menus):
    """
    Test the factory method for producing Menu items.
    """
    # Arrange & Act
    result_menu = menu_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_menu, menu.Menu)


def test_get(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    """
    Test retrieving a Menu item by name.
    """
    # Arrange
    name = "test_get"
    item1 = cobbler_api.new_menu()
    item1.name = name  # type: ignore[method-assign]
    menu_collection.add(item1)

    # Act
    item = menu_collection.get(name)
    fake_item = menu_collection.get("fake_name")

    # Assert
    assert isinstance(item, menu.Menu)
    assert item.name == name
    assert fake_item is None


def test_find(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    """
    Test to verify that a menu can be found inside the collection.
    """
    # Arrange
    name = "test_find"
    item1 = cobbler_api.new_menu()
    item1.name = name  # type: ignore[method-assign]
    menu_collection.add(item1)

    # Act
    result = menu_collection.find(True, True, name=name)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    """
    Test converting the collection to a list of dictionaries.
    """
    # Arrange
    name = "test_to_list"
    item1 = cobbler_api.new_menu()
    item1.name = name  # type: ignore[method-assign]
    menu_collection.add(item1)

    # Act
    result = menu_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(
    menu_collection: menus.Menus,
):
    """
    Test populating the collection from a list of dictionaries.
    """
    # Arrange
    item_list = [{"name": "test_from_list", "display_name": "test_display_name"}]

    # Act
    menu_collection.from_list(item_list)

    # Assert
    assert len(menu_collection.listing) == 1
    assert len(menu_collection.indexes["name"]) == 1
    assert len(menu_collection.indexes["parent"]) == 1


def test_copy(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    """
    Test copying a Menu item within the collection.
    """
    # Arrange
    name = "test_copy"
    item1 = cobbler_api.new_menu(name=name)
    menu_collection.add(item1)

    # Act
    new_item_name = "test_copy_new"
    menu_collection.copy(item1, new_item_name)
    item2 = menu_collection.find(False, name=new_item_name)
    assert isinstance(item2, menu.Menu)
    item2.parent = item1.uid  # type: ignore[method-assign]

    # Assert
    assert len(menu_collection.listing) == 2
    assert item1.uid in menu_collection.listing
    assert item2.uid in menu_collection.listing
    assert len(menu_collection.indexes["name"]) == 2
    assert (menu_collection.indexes["name"])[name] == item1.uid
    assert (menu_collection.indexes["name"])[new_item_name] == item2.uid
    assert len(menu_collection.indexes["parent"]) == 2
    assert menu_collection.indexes["parent"] == {
        "": {item1.uid},
        item1.uid: {item2.uid},
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
    menu_collection: menus.Menus,
    input_new_name: str,
):
    """
    Test renaming a Menu item within the collection.
    """
    # Arrange
    old_name = "test_rename"
    item1 = cobbler_api.new_menu()
    item1.name = old_name  # type: ignore[method-assign]
    menu_collection.add(item1)

    # Act
    menu_collection.rename(item1, input_new_name)

    # Assert
    assert item1.uid in menu_collection.listing
    assert menu_collection.listing[item1.uid].name == input_new_name
    assert len(menu_collection.indexes["parent"]) == 1
    assert (menu_collection.indexes["name"])[input_new_name] == item1.uid
    assert item1.uid in (menu_collection.indexes["parent"])[item1.get_parent]


def test_collection_add(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    """
    Test adding a Menu item to the collection.
    """
    # Arrange
    name = "test_collection_add"
    item1 = cobbler_api.new_menu()
    item1.name = name  # type: ignore[method-assign]

    # Act
    menu_collection.add(item1)

    # Assert
    assert item1.uid in menu_collection.listing
    assert item1.name in menu_collection.indexes["name"]
    assert item1.get_parent in menu_collection.indexes["parent"]


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    """
    Test that adding a Menu item with a duplicate name raises an exception.
    """
    # Arrange
    name = "duplicate_name"
    item1 = cobbler_api.new_menu()
    item1.name = name  # type: ignore[method-assign]
    menu_collection.add(item1)
    item2 = cobbler_api.new_menu()
    item2.name = name  # type: ignore[method-assign]

    # Act & Assert
    with pytest.raises(CX):
        menu_collection.add(item2, check_for_duplicate_names=True)


def test_remove(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    """
    Test removing a Menu item from the collection.
    """
    # Arrange
    name = "test_remove"
    item1 = cobbler_api.new_menu()
    item1.name = name  # type: ignore[method-assign]
    menu_collection.add(item1)
    assert item1.uid in menu_collection.listing
    assert len(menu_collection.indexes["name"]) == 1
    assert (menu_collection.indexes["name"])[item1.name] == item1.uid
    assert item1.uid in (menu_collection.indexes["parent"])[item1.get_parent]

    # Act
    menu_collection.remove(item1)

    # Assert
    assert item1.uid not in menu_collection.listing
    assert len(menu_collection.indexes["name"]) == 0
    assert len(menu_collection.indexes["parent"]) == 0


def test_indexes(
    menu_collection: menus.Menus,
):
    """
    Test to verify the indexes of the Menu collection.
    """
    # Arrange

    # Assert
    assert len(menu_collection.indexes) == 2
    assert len(menu_collection.indexes["name"]) == 0
    assert len(menu_collection.indexes["parent"]) == 0


def test_add_to_indexes(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    """
    Test adding a Menu item to the collection's indexes.
    """
    # Arrange
    name = "test_add_to_indexes"
    item1 = cobbler_api.new_menu()
    item1.name = name  # type: ignore[method-assign]
    menu_collection.add(item1)

    # Act
    del (menu_collection.indexes["name"])[item1.name]
    del (menu_collection.indexes["parent"])[item1.get_parent]
    menu_collection.add_to_indexes(item1)

    # Assert
    #    assert 0 == 1
    assert item1.name in menu_collection.indexes["name"]
    assert item1.get_parent in menu_collection.indexes["parent"]


def test_remove_from_indexes(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    """
    Test removing a Menu item from the collection's indexes.
    """
    # Arrange
    name = "test_remove_from_indexes"
    item1 = cobbler_api.new_menu()
    item1.name = name  # type: ignore[method-assign]
    menu_collection.add(item1)

    # Act
    menu_collection.remove_from_indexes(item1)

    # Assert
    assert item1.name not in menu_collection.indexes["name"]
    assert item1.get_parent not in menu_collection.indexes["parent"]


def test_update_indexes(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    """
    Test updating the indexes of a Menu item in the collection.
    """
    # Arrange
    name = "test_update_indexes"
    item1 = cobbler_api.new_menu()
    item1.name = name  # type: ignore[method-assign]
    menu_collection.add(item1)
    new_name = "test_update_indicies_new"

    # Act
    item1.name = new_name  # type: ignore[method-assign]

    # Assert
    assert menu_collection.indexes["name"][new_name] == item1.uid


def test_find_by_indexes(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    """
    Test finding Menu items by their indexes in the collection.
    """
    # Arrange
    name = "test_find_by_indexes"
    item1 = cobbler_api.new_menu()
    item1.name = name  # type: ignore[method-assign]
    menu_collection.add(item1)
    kargs1 = {"name": item1.name}
    kargs2 = {"name": "fake_uid"}
    kargs3 = {"fake_index": item1.uid}
    kargs4 = {"parent": ""}
    kargs5 = {"parent": "fake_parent"}

    # Act
    result1 = menu_collection.find_by_indexes(kargs1)
    result2 = menu_collection.find_by_indexes(kargs2)
    result3 = menu_collection.find_by_indexes(kargs3)
    result4 = menu_collection.find_by_indexes(kargs4)
    result5 = menu_collection.find_by_indexes(kargs5)

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
