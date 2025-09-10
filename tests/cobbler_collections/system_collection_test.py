"""
Tests that validate the functionality of the module that is responsible for managing the list of systems.
"""

from typing import Any, Callable, Dict

import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import systems
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import distro, image, profile, system

from tests.conftest import does_not_raise


@pytest.fixture(name="system_collection")
def fixture_system_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (Systems) of a generic collection.
    """
    return cobbler_api.systems()


def test_obj_create(collection_mgr: CollectionManager):
    """
    Validate that a system collection can be instantiated.
    """
    # Arrange & Act
    test_system_collection = systems.Systems(collection_mgr)

    # Assert
    assert isinstance(test_system_collection, systems.Systems)


def test_factory_produce(cobbler_api: CobblerAPI, system_collection: systems.Systems):
    """
    Validate that a system can be correctly produced by the factory method.
    """
    # Arrange & Act
    result_system = system_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_system, system.System)


def test_get(
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
):
    """
    Validate that a system can be successfully retrieved from the collection.
    """
    # Arrange
    name = "test_get"
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    create_system(test_profile.uid)

    # Act
    item = system_collection.get(name)
    fake_item = system_collection.get("fake_name")

    # Assert
    assert item is not None
    assert item.name == name
    assert fake_item is None


def test_find(
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
):
    """
    Validate that a system can be successfully found inside the collection.
    """
    # Arrange
    name = "test_find"
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    create_system(test_profile.uid)

    # Act
    result = system_collection.find(True, True, name=name)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
):
    """
    Validate that the collection can be converted to a list.
    """
    # Arrange
    name = "test_to_list"
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    create_system(test_profile.uid)

    # Act
    result = system_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    system_collection: systems.Systems,
):
    """
    Validate that the collection can be converted from a list.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    item_list = [
        {
            "name": "test_from_list",
            "profile": test_profile.uid,
        }
    ]

    # Act
    system_collection.from_list(item_list)

    # Assert
    assert len(system_collection.listing) == 1
    for key, indx in system_collection.indexes.items():
        print(key)
        if key in ("name", "profile", "image"):
            assert len(indx) == 1
        else:
            # mac_address, ip_address, ipv6_address, dns_name
            assert len(indx) == 0


def test_copy(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
):
    """
    Validate that a system can be copied.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    system1 = create_system(test_profile.uid)
    test_network_interface = cobbler_api.new_network_interface(
        system_uid=system1.uid,
        name="default",
        ip_address="192.168.1.1",
        ipv6_address="::1",
        dns_name="example.org",
        mac_address="52:54:00:7d:81:f4",
    )
    cobbler_api.add_network_interface(test_network_interface)

    # Act
    # pylint: disable-next=unused-variable
    test1 = {  # type: ignore[reportUnusedVariable]
        x for y in system_collection.listing.values() for x in y.interfaces.values()
    }
    new_item_name = "test_copy_successful"
    system_collection.copy(system1, new_item_name)
    system2: system.System = system_collection.find(False, name=new_item_name)  # type: ignore

    # Assert
    assert len(system_collection.listing) == 2
    assert system1.uid in system_collection.listing
    assert system2.uid in system_collection.listing
    for key, value in system_collection.indexes.items():
        indx_prop = cobbler_api.settings().memory_indexes["system"][key]  # type: ignore
        if hasattr(system1, key):
            if indx_prop["nonunique"]:
                assert len(value) == 1
                assert value[getattr(system1, key)] == {system1.uid, system2.uid}
                assert value[getattr(system2, key)] == {system1.uid, system2.uid}
            else:
                assert len(value) == 2
                assert value[getattr(system1, key)] == system1.uid
                assert value[getattr(system2, key)] == system2.uid
        else:
            assert len(value) == 1
            assert value[getattr(system1.interfaces["default"], key)] == system1.uid


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
    system_collection: systems.Systems,
    input_new_name: str,
):
    """
    Validate that a system can be renamed inside the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    system1 = create_system(test_profile.uid)
    test_network_interface = cobbler_api.new_network_interface(system_uid=system1.uid)
    test_network_interface.name = "default"  # type: ignore[method-assign]
    test_network_interface.ip_address = "192.168.1.1"
    test_network_interface.ipv6_address = "::1"
    test_network_interface.dns_name = "example.org"
    test_network_interface.mac_address = "52:54:00:7d:81:f4"
    cobbler_api.add_network_interface(test_network_interface)

    # Act
    system_collection.rename(system1, input_new_name)

    # Assert
    assert system1.uid in system_collection.listing
    assert system_collection.listing[system1.uid].name == input_new_name
    for interface in system1.interfaces.values():
        assert interface.system_uid == system1.uid
    for key, value in system_collection.indexes.items():
        indx_prop = cobbler_api.settings().memory_indexes["system"][key]  # type: ignore
        if hasattr(system1, key):
            if indx_prop["nonunique"]:
                assert value[getattr(system1, key)] == {system1.uid}
            else:
                assert value[getattr(system1, key)] == system1.uid
        else:
            assert value[getattr(system1.interfaces["default"], key)] == system1.uid


def test_collection_add(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    system_collection: systems.Systems,
):
    """
    Validate that a system can be added to the collection.
    """
    # Arrange
    name = "test_collection_add"
    test_distro = create_distro()
    profile1 = create_profile(test_distro.uid)
    system1 = cobbler_api.new_system(name=name, profile=profile1.uid)
    test_network_interface = cobbler_api.new_network_interface(
        system_uid=system1.uid,
        name="default",
        ip_address="192.168.1.1",
        ipv6_address="::1",
        dns_name="example.org",
        mac_address="52:54:00:7d:81:f4",
    )
    cobbler_api.add_network_interface(test_network_interface)

    # Act
    system_collection.add(system1)

    # Assert
    assert system1.uid in system_collection.listing
    assert system_collection.listing[system1.uid].name == name
    for interface in system1.interfaces.values():
        assert interface.system_uid == system1.uid
    for key, value in system_collection.indexes.items():
        indx_prop = cobbler_api.settings().memory_indexes["system"][key]  # type: ignore
        if hasattr(system1, key):
            if indx_prop["nonunique"]:
                assert value[getattr(system1, key)] == {system1.uid}
            else:
                assert value[getattr(system1, key)] == system1.uid
        else:
            assert value[getattr(system1.interfaces["default"], key)] == system1.uid


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    create_distro: Any,
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
):
    """
    Validate that a system with an identical name cannot be added to the collection.
    """
    # Arrange
    name = "test_duplicate_add"
    test_distro = create_distro(name)
    test_profile = create_profile(test_distro.uid)
    system1 = create_system(test_profile.uid)
    test_network_interface = cobbler_api.new_network_interface(
        system_uid=system1.uid,
        name="default",
        ip_address="192.168.1.1",
        ipv6_address="::1",
        dns_name="example.org",
        mac_address="52:54:00:7d:81:f4",
    )
    cobbler_api.add_network_interface(test_network_interface)
    system2 = cobbler_api.new_system(name=name, profile=test_profile.uid)

    # Act & Assert
    assert len(system_collection.indexes["name"]) == 1
    with pytest.raises(CX):
        system_collection.add(system2, check_for_duplicate_names=True)
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == 1


def test_remove(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
):
    """
    Validate that a system can be removed from the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    system1 = create_system(test_profile.uid)
    cobbler_api.remove_network_interface(system1.interfaces["default"])
    assert system1.uid in system_collection.listing

    # Pre-Assert to validate if the index is in its correct state
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == 1

    # Act
    system_collection.remove(system1)

    # Assert
    assert system1.uid not in system_collection.listing
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == 0


@pytest.mark.parametrize(
    "recursive,expected_exception,expected_result",
    [
        (False, pytest.raises(CX), 1),
        (True, does_not_raise(), 0),
    ],
)
def test_remove_by_image_dependency(
    cobbler_api: CobblerAPI,
    create_image: Callable[[], image.Image],
    create_system: Callable[..., system.System],
    system_collection: systems.Systems,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Validate that a system can be removed from the collection.
    """
    # Arrange
    test_image = create_image()
    system1 = create_system(image_uid=test_image.uid)
    system1.interfaces["default"].ip_address = "192.168.1.1"
    system1.interfaces["default"].ipv6_address = "::1"
    system1.interfaces["default"].dns_name = "example.org"
    system1.interfaces["default"].mac_address = "52:54:00:7d:81:f4"

    # Act
    with expected_exception:
        cobbler_api.images().remove(test_image, recursive=recursive)

    # Assert
    assert (system1.uid not in system_collection.listing) == recursive
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == expected_result


@pytest.mark.parametrize(
    "recursive,expected_exception,expected_result",
    [
        (False, pytest.raises(CX), 1),
        (True, does_not_raise(), 0),
    ],
)
def test_remove_by_menu_image_dependency(
    cobbler_api: CobblerAPI,
    create_image: Callable[[], image.Image],
    create_system: Callable[..., system.System],
    system_collection: systems.Systems,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Validate that a system can be removed from the collection.
    """
    # Arrange
    test_image = create_image()
    test_menu = cobbler_api.new_menu()
    test_menu.name = "test_menu"  # type: ignore[method-assign]
    cobbler_api.menus().add(test_menu)
    test_image.menu = test_menu.uid  # type: ignore[method-assign]
    system1 = create_system(image_uid=test_image.uid)
    system1.interfaces["default"].ip_address = "192.168.1.1"
    system1.interfaces["default"].ipv6_address = "::1"
    system1.interfaces["default"].dns_name = "example.org"
    system1.interfaces["default"].mac_address = "52:54:00:7d:81:f4"

    # Act
    with expected_exception:
        cobbler_api.menus().remove(test_menu, recursive=recursive)

    # Assert
    assert (system1.uid not in system_collection.listing) == recursive
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == expected_result


@pytest.mark.parametrize(
    "recursive,expected_exception,expected_result",
    [
        (False, pytest.raises(CX), 1),
        (True, does_not_raise(), 0),
    ],
)
def test_remove_by_parent_menu_dependency(
    cobbler_api: CobblerAPI,
    create_image: Callable[[], image.Image],
    create_system: Callable[..., system.System],
    system_collection: systems.Systems,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Validate that a system can be removed from the collection.
    """
    # Arrange
    test_image = create_image()
    test_menu = cobbler_api.new_menu()
    test_menu.name = "test_menu"  # type: ignore[method-assign]
    cobbler_api.menus().add(test_menu)
    test_parent_menu = cobbler_api.new_menu()
    test_parent_menu.name = "test_parent_menu"  # type: ignore[method-assign]
    cobbler_api.menus().add(test_parent_menu)
    test_menu.parent = test_parent_menu.uid  # type: ignore[method-assign]
    test_image.menu = test_menu.uid  # type: ignore[method-assign]
    system1 = create_system(image_uid=test_image.uid)
    system1.interfaces["default"].ip_address = "192.168.1.1"
    system1.interfaces["default"].ipv6_address = "::1"
    system1.interfaces["default"].dns_name = "example.org"
    system1.interfaces["default"].mac_address = "52:54:00:7d:81:f4"

    # Act
    with expected_exception:
        cobbler_api.menus().remove(test_parent_menu, recursive=recursive)

    # Assert
    assert (system1.uid not in system_collection.listing) == recursive
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == expected_result


@pytest.mark.parametrize(
    "recursive,expected_exception,expected_result",
    [
        (False, pytest.raises(CX), 1),
        (True, does_not_raise(), 0),
    ],
)
def test_remove_by_distro_dependency(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Validate that a system can be removed from the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    system1 = create_system(test_profile.uid)
    system1.interfaces["default"].ip_address = "192.168.1.1"
    system1.interfaces["default"].ipv6_address = "::1"
    system1.interfaces["default"].dns_name = "example.org"
    system1.interfaces["default"].mac_address = "52:54:00:7d:81:f4"

    # Act
    with expected_exception:
        cobbler_api.distros().remove(test_distro, recursive=recursive)

    # Assert
    assert (system1.uid not in system_collection.listing) == recursive
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == expected_result


@pytest.mark.parametrize(
    "recursive,expected_exception,expected_result",
    [
        (False, pytest.raises(CX), 1),
        (True, does_not_raise(), 0),
    ],
)
def test_remove_by_profile_dependency(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Validate that a system can be removed from the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    system1 = create_system(test_profile.uid)
    system1.interfaces["default"].ip_address = "192.168.1.1"
    system1.interfaces["default"].ipv6_address = "::1"
    system1.interfaces["default"].dns_name = "example.org"
    system1.interfaces["default"].mac_address = "52:54:00:7d:81:f4"

    # Act
    with expected_exception:
        cobbler_api.profiles().remove(test_profile, recursive=recursive)

    # Assert
    assert (system1.uid not in system_collection.listing) == recursive
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == expected_result


@pytest.mark.parametrize(
    "recursive,expected_exception,expected_result",
    [
        (False, pytest.raises(CX), 1),
        (True, does_not_raise(), 0),
    ],
)
def test_remove_by_menu_profile_dependency(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Validate that a system can be removed from the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_menu = cobbler_api.new_menu()
    test_menu.name = "test_menu"  # type: ignore[method-assign]
    cobbler_api.menus().add(test_menu)
    test_profile.menu = test_menu.uid  # type: ignore[method-assign]
    system1 = create_system(test_profile.uid)
    system1.interfaces["default"].ip_address = "192.168.1.1"
    system1.interfaces["default"].ipv6_address = "::1"
    system1.interfaces["default"].dns_name = "example.org"
    system1.interfaces["default"].mac_address = "52:54:00:7d:81:f4"

    # Act
    with expected_exception:
        cobbler_api.menus().remove(test_menu, recursive=recursive)

    # Assert
    assert (system1.uid not in system_collection.listing) == recursive
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == expected_result


@pytest.mark.parametrize(
    "recursive,expected_exception,expected_result",
    [
        (False, pytest.raises(CX), 1),
        (True, does_not_raise(), 0),
    ],
)
def test_remove_by_repos_profile_dependency(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Validate that a system can be removed from the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_repo = cobbler_api.new_repo()
    test_repo.name = "test_repo"  # type: ignore[method-assign]
    cobbler_api.repos().add(test_repo)
    test_profile.repos = [test_repo.uid]  # type: ignore[method-assign]
    system1 = create_system(test_profile.uid)
    system1.interfaces["default"].ip_address = "192.168.1.1"
    system1.interfaces["default"].ipv6_address = "::1"
    system1.interfaces["default"].dns_name = "example.org"
    system1.interfaces["default"].mac_address = "52:54:00:7d:81:f4"

    # Act
    with expected_exception:
        cobbler_api.repos().remove(test_repo, recursive=recursive)

    # Assert
    assert (system1.uid not in system_collection.listing) == recursive
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == expected_result


@pytest.mark.parametrize(
    "recursive,expected_exception,expected_result",
    [
        (False, pytest.raises(CX), 1),
        (True, does_not_raise(), 0),
    ],
)
def test_remove_by_parent_profile_dependency(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[..., profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Validate that a system can be removed from the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_parent_profile = create_profile(test_distro.uid, name="test_parent_profile")
    test_profile.parent = test_parent_profile.uid  # type: ignore[method-assign]
    system1 = create_system(test_profile.uid)
    system1.interfaces["default"].ip_address = "192.168.1.1"
    system1.interfaces["default"].ipv6_address = "::1"
    system1.interfaces["default"].dns_name = "example.org"
    system1.interfaces["default"].mac_address = "52:54:00:7d:81:f4"

    # Act
    with expected_exception:
        cobbler_api.profiles().remove(test_parent_profile, recursive=recursive)

    # Assert
    assert (system1.uid not in system_collection.listing) == recursive
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == expected_result


def test_indexes(
    system_collection: systems.Systems,
):
    """
    Validate that the secondary indices on the system collection work as expected with an empty collection.
    """
    # Arrange

    # Assert
    assert len(system_collection.indexes) == 3
    assert len(system_collection.indexes["name"]) == 0
    assert len(system_collection.indexes["image"]) == 0
    assert len(system_collection.indexes["profile"]) == 0


def test_add_to_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
):
    """
    Validate that the secondary indices on the system collection work as expected while adding a system.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    system1 = create_system(test_profile.uid)
    system1.interfaces["default"].ip_address = "192.168.1.1"
    system1.interfaces["default"].ipv6_address = "::1"
    system1.interfaces["default"].dns_name = "example.org"
    system1.interfaces["default"].mac_address = "52:54:00:7d:81:f4"
    for key, value in system_collection.indexes.items():
        if hasattr(system1, key):
            del value[getattr(system1, key)]
        else:
            del value[getattr(system1.interfaces["default"], key)]

    # Act
    system_collection.add_to_indexes(system1)

    # Assert
    for key, value in system_collection.indexes.items():
        indx_prop = cobbler_api.settings().memory_indexes["system"][key]  # type: ignore
        if hasattr(system1, key):
            if indx_prop["nonunique"]:
                assert {getattr(system1, key): {system1.uid}} == value
            else:
                assert {getattr(system1, key): system1.uid} == value
        else:
            assert {getattr(system1.interfaces["default"], key): system1.uid} == value


def test_update_system_indexes(
    cobbler_api: CobblerAPI,
    create_image: Callable[[], image.Image],
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
):
    """
    Validate that the secondary indices on the system collection work as expected when updating a network interface.
    """
    # Arrange
    image1 = create_image()
    test_distro = create_distro()
    profile1 = create_profile(test_distro.uid)
    system1 = create_system(profile1.uid)

    # Act
    original_uid = system1.uid
    original_image = system1.image
    system1.name = "test_update_system_indexes_renamed"  # type: ignore[method-assign]
    system1.profile = ""  # type: ignore[method-assign]
    system1.image = image1.uid  # type: ignore[method-assign]

    # Assert
    assert original_uid not in system_collection.indexes["name"]
    assert system_collection.indexes["name"][system1.name] == system1.uid
    assert profile1.name not in system_collection.indexes["profile"]
    assert system_collection.indexes["profile"][system1.profile] == {system1.uid}
    assert original_image not in system_collection.indexes["image"]
    assert system_collection.indexes["image"][system1.image] == {system1.uid}


def test_remove_from_indexes(
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
):
    """
    Validate that the secondary indices on the system collection work as expected when removing a system.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    system1 = create_system(test_profile.uid)
    system1.interfaces["default"].ip_address = "192.168.1.1"
    system1.interfaces["default"].ipv6_address = "::1"
    system1.interfaces["default"].dns_name = "example.org"
    system1.interfaces["default"].mac_address = "52:54:00:7d:81:f4"

    # Act
    system_collection.remove_from_indexes(system1)

    # Assert
    assert system1.uid not in system_collection.indexes["name"]


def test_find_by_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
):
    """
    Validate that the secondary indices on the system collection work as expected for finding items in a collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    system1 = create_system(test_profile.uid)

    kwargs = {
        "name": [
            {"name": system1.name},
            {"name": "fake_name"},
            {"fake_index": system1.name},
        ],
    }
    results: Dict[str, Any] = {}

    # Act
    for indx, args in kwargs.items():
        results[indx] = []
        for arg in args:
            results[indx].append(system_collection.find_by_indexes(arg))

    # Assert
    print(results)
    for indx, result in results.items():
        assert isinstance(result[0], list)
        assert len(result[0]) == 1
        assert (result[0])[0] == system1
        assert len((kwargs[indx])[0]) == 0
        assert result[1] is None
        assert len((kwargs[indx])[1]) == 0
        assert result[2] is None
        assert len((kwargs[indx])[2]) == 1
