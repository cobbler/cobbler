import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import menus
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import menu


@pytest.fixture
def menu_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (Menus) of a generic collection.
    """
    return cobbler_api.menus()


def test_obj_create(collection_mgr: CollectionManager):
    # Arrange & Act
    menu_collection = menus.Menus(collection_mgr)

    # Assert
    assert isinstance(menu_collection, menus.Menus)


def test_factory_produce(cobbler_api: CobblerAPI, menu_collection: menus.Menus):
    # Arrange & Act
    result_menu = menu_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_menu, menu.Menu)


def test_get(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    # Arrange
    name = "test_get"
    item1 = menu.Menu(cobbler_api)
    item1.name = name
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
    # Arrange
    name = "test_find"
    item1 = menu.Menu(cobbler_api)
    item1.name = name
    menu_collection.add(item1)

    # Act
    result = menu_collection.find(name, True, True)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    # Arrange
    name = "test_to_list"
    item1 = menu.Menu(cobbler_api)
    item1.name = name
    menu_collection.add(item1)

    # Act
    result = menu_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(
    menu_collection: menus.Menus,
):
    # Arrange
    item_list = [{"name": "test_from_list", "display_name": "test_display_name"}]

    # Act
    menu_collection.from_list(item_list)

    # Assert
    assert len(menu_collection.listing) == 1
    assert len(menu_collection.indexes["uid"]) == 1
    assert len(menu_collection.indexes["parent"]) == 1


def test_copy(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    # Arrange
    name = "test_copy"
    item1 = menu.Menu(cobbler_api)
    item1.name = name
    menu_collection.add(item1)

    # Act
    new_item_name = "test_copy_new"
    menu_collection.copy(item1, new_item_name)
    item2 = menu_collection.find(new_item_name, False)
    assert isinstance(item2, menu.Menu)
    item2.parent = name

    # Assert
    assert len(menu_collection.listing) == 2
    assert name in menu_collection.listing
    assert new_item_name in menu_collection.listing
    assert len(menu_collection.indexes["uid"]) == 2
    assert (menu_collection.indexes["uid"])[item1.uid] == name
    assert (menu_collection.indexes["uid"])[item2.uid] == new_item_name
    assert len(menu_collection.indexes["parent"]) == 2
    assert menu_collection.indexes["parent"] == {"": {item1.name}, name: {item2.name}}


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
    # Arrange
    old_name = "test_rename"
    item1 = menu.Menu(cobbler_api)
    item1.name = old_name
    menu_collection.add(item1)

    # Act
    menu_collection.rename(item1, input_new_name)

    # Assert
    assert input_new_name in menu_collection.listing
    assert menu_collection.listing[input_new_name].name == input_new_name
    assert len(menu_collection.indexes["parent"]) == 1
    assert (menu_collection.indexes["uid"])[item1.uid] == input_new_name
    assert old_name not in (menu_collection.indexes["parent"])[item1.get_parent]
    assert input_new_name in (menu_collection.indexes["parent"])[item1.get_parent]


def test_collection_add(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    # Arrange
    name = "test_collection_add"
    item1 = menu.Menu(cobbler_api)
    item1.name = name

    # Act
    menu_collection.add(item1)

    # Assert
    assert name in menu_collection.listing
    assert item1.uid in menu_collection.indexes["uid"]
    assert item1.get_parent in menu_collection.indexes["parent"]


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    # Arrange
    name = "duplicate_name"
    item1 = menu.Menu(cobbler_api)
    item1.name = name
    menu_collection.add(item1)
    item2 = menu.Menu(cobbler_api)
    item2.name = name

    # Act & Assert
    with pytest.raises(CX):
        menu_collection.add(item2, check_for_duplicate_names=True)


def test_remove(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    # Arrange
    name = "test_remove"
    item1 = menu.Menu(cobbler_api)
    item1.name = name
    menu_collection.add(item1)
    assert name in menu_collection.listing
    assert len(menu_collection.indexes["uid"]) == 1
    assert (menu_collection.indexes["uid"])[item1.uid] == item1.name
    assert item1.name in (menu_collection.indexes["parent"])[item1.get_parent]

    # Act
    menu_collection.remove(name)

    # Assert
    assert name not in menu_collection.listing
    assert len(menu_collection.indexes["uid"]) == 0
    assert len(menu_collection.indexes["parent"]) == 0


def test_indexes(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    # Arrange

    # Assert
    assert len(menu_collection.indexes) == 2
    assert len(menu_collection.indexes["uid"]) == 0
    assert len(menu_collection.indexes["parent"]) == 0


def test_add_to_indexes(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    # Arrange
    name = "test_add_to_indexes"
    item1 = menu.Menu(cobbler_api)
    item1.name = name
    menu_collection.add(item1)

    # Act
    del (menu_collection.indexes["uid"])[item1.uid]
    del (menu_collection.indexes["parent"])[item1.get_parent]
    menu_collection.add_to_indexes(item1)

    # Assert
    #    assert 0 == 1
    assert item1.uid in menu_collection.indexes["uid"]
    assert item1.get_parent in menu_collection.indexes["parent"]


def test_remove_from_indexes(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    # Arrange
    name = "test_remove_from_indexes"
    item1 = menu.Menu(cobbler_api)
    item1.name = name
    menu_collection.add(item1)

    # Act
    menu_collection.remove_from_indexes(item1)

    # Assert
    assert item1.uid not in menu_collection.indexes["uid"]
    assert item1.get_parent not in menu_collection.indexes["parent"]


def test_update_indexes(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    # Arrange
    name = "test_update_indexes"
    item1 = menu.Menu(cobbler_api)
    item1.name = name
    menu_collection.add(item1)
    uid1_test = "test_uid"

    # Act
    item1.uid = uid1_test

    # Assert
    assert menu_collection.indexes["uid"][uid1_test] == name


def test_find_by_indexes(
    cobbler_api: CobblerAPI,
    menu_collection: menus.Menus,
):
    # Arrange
    name = "test_find_by_indexes"
    item1 = menu.Menu(cobbler_api)
    item1.name = name
    menu_collection.add(item1)
    kargs1 = {"uid": item1.uid}
    kargs2 = {"uid": "fake_uid"}
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
