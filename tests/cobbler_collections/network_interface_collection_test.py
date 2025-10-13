"""
Tests that validate the functionality of the module that is responsible for managing the list of network interfaces.
"""

from typing import Any, Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import network_interfaces
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import distro, network_interface, profile, system

from tests.conftest import does_not_raise


@pytest.fixture(name="network_interface_collection")
def fixture_network_interface_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (Network Interfaces) of a generic collection.
    """
    return cobbler_api.network_interfaces()


def test_obj_create(collection_mgr: CollectionManager):
    """
    Test the creation of a Menus collection object.
    """
    # Arrange & Act
    menu_collection = network_interfaces.NetworkInterfaces(collection_mgr)

    # Assert
    assert isinstance(menu_collection, network_interfaces.NetworkInterfaces)


def test_factory_produce(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test the factory method for producing Network Interface items.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)

    # Act
    result_menu = network_interface_collection.factory_produce(
        cobbler_api, {"system_uid": test_system.uid}
    )

    # Assert
    assert isinstance(result_menu, network_interface.NetworkInterface)


def test_get(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test retrieving a Network Interface item by name.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    name = "test_get"
    item1 = cobbler_api.new_network_interface(system_uid=test_system.uid)
    item1.name = name  # type: ignore[method-assign]
    network_interface_collection.add(item1)

    # Act
    item = network_interface_collection.get(name)
    fake_item = network_interface_collection.get("fake_name")

    # Assert
    assert isinstance(item, network_interface.NetworkInterface)
    assert item.name == name
    assert fake_item is None


def test_find(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test to verify that a menu can be found inside the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    name = "test_find"
    item1 = cobbler_api.new_network_interface(system_uid=test_system.uid)
    item1.name = name  # type: ignore[method-assign]
    network_interface_collection.add(item1)

    # Act
    result = network_interface_collection.find(True, True, name=name)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test converting the collection to a list of dictionaries.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    name = "test_to_list"
    item1 = cobbler_api.new_network_interface(system_uid=test_system.uid)
    item1.name = name  # type: ignore[method-assign]
    network_interface_collection.add(item1)

    # Act
    result = network_interface_collection.to_list()

    # Assert - System Default interface and "test_to_list" interface
    assert len(result) == 2
    assert name in [item.get("name", "<empty>") for item in result]


def test_from_list(
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test populating the collection from a list of dictionaries.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    item_list = [{"name": "test_from_list", "system_uid": test_system.uid}]

    # Act
    network_interface_collection.from_list(item_list)

    # Assert
    assert len(network_interface_collection.listing) == 2
    assert len(network_interface_collection.indexes["name"]) == 2


def test_copy(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test copying a Network Interface item within the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    name = "test_copy"
    item1 = cobbler_api.new_network_interface(system_uid=test_system.uid, name=name)
    network_interface_collection.add(item1)

    # Act
    new_item_name = "test_copy_new"
    network_interface_collection.copy(item1, new_item_name)
    item2 = network_interface_collection.find(False, name=new_item_name)
    assert isinstance(item2, network_interface.NetworkInterface)

    # Assert
    # 3 interfaces: "default", "test_copy", "test_copy_new"
    assert len(network_interface_collection.listing) == 3
    assert item1.uid in network_interface_collection.listing
    assert item2.uid in network_interface_collection.listing
    assert len(network_interface_collection.indexes["name"]) == 3
    assert (network_interface_collection.indexes["name"])[name] == {item1.uid}
    assert (network_interface_collection.indexes["name"])[new_item_name] == {item2.uid}


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
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
    input_new_name: str,
):
    """
    Test renaming a Network Interface item within the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    old_name = "test_rename"
    item1 = cobbler_api.new_network_interface(system_uid=test_system.uid)
    item1.name = old_name  # type: ignore[method-assign]
    network_interface_collection.add(item1)

    # Act
    network_interface_collection.rename(item1, input_new_name)

    # Assert
    assert item1.uid in network_interface_collection.listing
    assert network_interface_collection.listing[item1.uid].name == input_new_name
    assert (network_interface_collection.indexes["name"])[input_new_name] == {item1.uid}


def test_collection_add(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test adding a Network Interface item to the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    name = "test_collection_add"
    item1 = cobbler_api.new_network_interface(system_uid=test_system.uid)
    item1.name = name  # type: ignore[method-assign]

    # Act
    network_interface_collection.add(item1)

    # Assert
    assert item1.uid in network_interface_collection.listing
    assert item1.name in network_interface_collection.indexes["name"]


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test that adding a Network Interface item with a duplicate name raises an exception.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    name = "duplicate_name"
    item1 = cobbler_api.new_network_interface(system_uid=test_system.uid, name=name)
    network_interface_collection.add(item1)
    item2 = cobbler_api.new_network_interface(system_uid=test_system.uid, name=name)

    # Act & Assert
    with pytest.raises(CX):
        network_interface_collection.add(item2, check_for_duplicate_names=True)


def test_remove(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test removing a Network Interface item from the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    name = "test_remove"
    item1 = cobbler_api.new_network_interface(system_uid=test_system.uid)
    item1.name = name  # type: ignore[method-assign]
    network_interface_collection.add(item1)
    assert item1.uid in network_interface_collection.listing
    assert len(network_interface_collection.indexes["name"]) == 2
    assert (network_interface_collection.indexes["name"])[item1.name] == {item1.uid}

    # Act
    network_interface_collection.remove(item1)

    # Assert
    assert item1.uid not in network_interface_collection.listing
    assert len(network_interface_collection.indexes["name"]) == 1


@pytest.mark.parametrize(
    "recursive,expected_exception,expected_result",
    [
        (False, pytest.raises(CX), 2),
        (True, does_not_raise(), 0),
    ],
)
def test_remove_by_system_dependency(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Test removing a Network Interface item from the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    name = "test_remove"
    item1 = cobbler_api.new_network_interface(system_uid=test_system.uid)
    item1.name = name  # type: ignore[method-assign]
    network_interface_collection.add(item1)

    # Act
    with expected_exception:
        cobbler_api.systems().remove(test_system, recursive=recursive)

    # Assert
    assert (item1.uid not in network_interface_collection.listing) == recursive
    assert len(network_interface_collection.indexes["name"]) == expected_result


def test_indexes(
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test to verify the indexes of the Network Interface collection.
    """
    # Arrange

    # Assert
    assert len(network_interface_collection.indexes) == 5
    assert len(network_interface_collection.indexes["name"]) == 0
    assert len(network_interface_collection.indexes["dns.name"]) == 0
    assert len(network_interface_collection.indexes["ipv4.address"]) == 0
    assert len(network_interface_collection.indexes["ipv6.address"]) == 0
    assert len(network_interface_collection.indexes["mac_address"]) == 0


def test_add_to_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test adding a Network Interface item to the collection's indexes.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    name = "test_add_to_indexes"
    item1 = cobbler_api.new_network_interface(system_uid=test_system.uid)
    item1.name = name  # type: ignore[method-assign]
    network_interface_collection.add(item1)

    # Act
    del (network_interface_collection.indexes["name"])[item1.name]
    network_interface_collection.add_to_indexes(item1)

    # Assert
    #    assert 0 == 1
    assert item1.name in network_interface_collection.indexes["name"]


def test_remove_from_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test removing a Network Interface item from the collection's indexes.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    name = "test_remove_from_indexes"
    item1 = cobbler_api.new_network_interface(system_uid=test_system.uid)
    item1.name = name  # type: ignore[method-assign]
    network_interface_collection.add(item1)

    # Act
    network_interface_collection.remove_from_indexes(item1)

    # Assert
    assert item1.name not in network_interface_collection.indexes["name"]


def test_update_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test updating the indexes of a Network Interface item in the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    name = "test_update_indexes"
    item1 = cobbler_api.new_network_interface(system_uid=test_system.uid, name=name)
    network_interface_collection.add(item1)
    new_name = "test_update_indicies_new"

    # Act
    item1.name = new_name  # type: ignore[method-assign]

    # Assert
    assert network_interface_collection.indexes["name"][new_name] == {item1.uid}


def test_find_by_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    network_interface_collection: network_interfaces.NetworkInterfaces,
):
    """
    Test finding Network Interface items by their indexes in the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)
    name = "test_find_by_indexes"
    item1 = cobbler_api.new_network_interface(system_uid=test_system.uid)
    item1.name = name  # type: ignore[method-assign]
    network_interface_collection.add(item1)
    kwargs1 = {"name": item1.name}
    kwargs2 = {"name": "fake_uid"}
    kwargs3 = {"fake_index": item1.uid}

    # Act
    result1 = network_interface_collection.find_by_indexes(kwargs1)
    result2 = network_interface_collection.find_by_indexes(kwargs2)
    result3 = network_interface_collection.find_by_indexes(kwargs3)

    # Assert
    assert isinstance(result1, list)
    assert len(result1) == 1
    assert result1[0] == item1
    assert len(kwargs1) == 0
    assert result2 is None
    assert len(kwargs2) == 0
    assert result3 is None
    assert len(kwargs3) == 1
