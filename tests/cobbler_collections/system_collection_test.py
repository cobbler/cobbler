"""
Tests that validate the functionality of the module that is responsible for managing the list of systems.
"""

from typing import Any, Callable, Dict

import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import systems
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import distro, image, network_interface, profile, system


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
            "interfaces": {
                "default": {
                    "ip_address": "192.168.1.1",
                    "ipv6_address": "::1",
                    "dns_name": "example.org",
                    "mac_address": "52:54:00:7d:81:f4",
                }
            },
        }
    ]

    # Act
    system_collection.from_list(item_list)

    # Assert
    assert len(system_collection.listing) == 1
    for indx in system_collection.indexes.values():
        assert len(indx) == 1


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
    system1.interfaces = {  # type: ignore[method-assign]
        "default": {
            "ip_address": "192.168.1.1",
            "ipv6_address": "::1",
            "dns_name": "example.org",
            "mac_address": "52:54:00:7d:81:f4",
        }
    }

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
    system1.interfaces = {  # type: ignore[method-assign]
        "default": {
            "ip_address": "192.168.1.1",
            "ipv6_address": "::1",
            "dns_name": "example.org",
            "mac_address": "52:54:00:7d:81:f4",
        }
    }

    # Act
    system_collection.rename(system1, input_new_name)

    # Assert
    assert system1.uid in system_collection.listing
    assert system_collection.listing[system1.uid].name == input_new_name
    for interface in system1.interfaces.values():
        assert interface.system_name == input_new_name
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
    system1.interfaces = {  # type: ignore[method-assign]
        "default": {
            "ip_address": "192.168.1.1",
            "ipv6_address": "::1",
            "dns_name": "example.org",
            "mac_address": "52:54:00:7d:81:f4",
        }
    }

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
    system1.interfaces = {  # type: ignore[method-assign]
        "default": {
            "ip_address": "192.168.1.1",
            "ipv6_address": "::1",
            "dns_name": "example.org",
            "mac_address": "52:54:00:7d:81:f4",
        }
    }
    system2 = cobbler_api.new_system(name=name, profile=test_profile.uid)

    # Act & Assert
    assert len(system_collection.indexes["name"]) == 1
    with pytest.raises(CX):
        system_collection.add(system2, check_for_duplicate_names=True)
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == 1


def test_remove(
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
):
    """
    Validate that a system can be removed from the collection.
    """
    # Arrange
    name = "test_remove"
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    system1 = create_system(test_profile.uid)
    system1.interfaces = {  # type: ignore[method-assign]
        "default": {
            "ip_address": "192.168.1.1",
            "ipv6_address": "::1",
            "dns_name": "example.org",
            "mac_address": "52:54:00:7d:81:f4",
        }
    }
    assert system1.uid in system_collection.listing

    # Pre-Assert to validate if the index is in its correct state
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == 1

    # Act
    system_collection.remove(system1)

    # Assert
    assert name not in system_collection.listing
    for key, _ in system_collection.indexes.items():
        assert len(system_collection.indexes[key]) == 0


def test_indexes(
    system_collection: systems.Systems,
):
    """
    Validate that the secondary indices on the system collection work as expected with an empty collection.
    """
    # Arrange

    # Assert
    assert len(system_collection.indexes) == 7
    assert len(system_collection.indexes["name"]) == 0
    assert len(system_collection.indexes["image"]) == 0
    assert len(system_collection.indexes["profile"]) == 0
    assert len(system_collection.indexes["mac_address"]) == 0
    assert len(system_collection.indexes["ip_address"]) == 0
    assert len(system_collection.indexes["ipv6_address"]) == 0
    assert len(system_collection.indexes["dns_name"]) == 0


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
    system1.interfaces = {  # type: ignore[method-assign]
        "default": {
            "ip_address": "192.168.1.1",
            "ipv6_address": "::1",
            "dns_name": "example.org",
            "mac_address": "52:54:00:7d:81:f4",
        }
    }
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


def test_update_interfaces_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
):
    """
    Validate that the secondary indices on the system collection work as expected while updating a systems network
    interface.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    system1 = create_system(test_profile.uid)
    system1.interfaces = {  # type: ignore[method-assign]
        "test1": {
            "ip_address": "192.168.1.1",
            "ipv6_address": "::1",
            "dns_name": "test1.example.org",
            "mac_address": "52:54:00:7d:81:f4",
        },
        "test2": {
            "ip_address": "192.168.1.2",
            "ipv6_address": "::2",
            "dns_name": "test2.example.org",
            "mac_address": "52:54:00:7d:81:f5",
        },
    }
    interface1 = network_interface.NetworkInterface(cobbler_api, system1.uid)
    interface1.from_dict(
        {
            "ip_address": "192.168.1.3",
            "ipv6_address": "::3",
            "dns_name": "",
            "mac_address": "52:54:00:7d:81:f6",
        }
    )
    interface2 = network_interface.NetworkInterface(cobbler_api, system1.uid)
    interface2.from_dict(
        {
            "ip_address": "192.168.1.4",
            "ipv6_address": "",
            "dns_name": "test4.example.org",
            "mac_address": "52:54:00:7d:81:f7",
        }
    )
    new_interfaces = {
        "test1": interface1,
        "test2": interface2,
        "test3": system1.interfaces["test2"],
    }

    # Act
    system_collection.update_interfaces_indexes(system1, new_interfaces)

    # Assert
    assert set(system_collection.indexes["ip_address"].keys()) == {
        "192.168.1.2",
        "192.168.1.3",
        "192.168.1.4",
    }
    assert set(system_collection.indexes["ipv6_address"].keys()) == {"::2", "::3"}
    assert set(system_collection.indexes["dns_name"].keys()) == {
        "test2.example.org",
        "test4.example.org",
    }
    assert set(system_collection.indexes["mac_address"].keys()) == {
        "52:54:00:7d:81:f5",
        "52:54:00:7d:81:f6",
        "52:54:00:7d:81:f7",
    }

    # Cleanup
    for indx_key, _ in system_collection.indexes.items():
        system_collection.indexes[indx_key] = {}


def test_update_interface_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    create_system: Callable[[str], system.System],
    system_collection: systems.Systems,
):
    """
    Validate that the secondary indices on the system collection work as expected when updating a network interface.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    system1 = create_system(test_profile.uid)
    system1.interfaces = {  # type: ignore[method-assign]
        "test1": {
            "ip_address": "192.168.1.1",
            "ipv6_address": "::1",
            "dns_name": "test1.example.org",
            "mac_address": "52:54:00:7d:81:f4",
        },
        "test2": {
            "ip_address": "192.168.1.2",
            "ipv6_address": "::2",
            "dns_name": "test2.example.org",
            "mac_address": "52:54:00:7d:81:f5",
        },
    }
    interface1 = network_interface.NetworkInterface(cobbler_api, system1.uid)
    interface1.from_dict(
        {
            "ip_address": "192.168.1.3",
            "ipv6_address": "::3",
            "dns_name": "",
            "mac_address": "52:54:00:7d:81:f6",
        }
    )

    # Act
    system_collection.update_interface_indexes(system1, "test2", interface1)

    # Assert
    assert set(system_collection.indexes["ip_address"].keys()) == {
        "192.168.1.1",
        "192.168.1.3",
    }
    assert set(system_collection.indexes["ipv6_address"].keys()) == {"::1", "::3"}
    assert set(system_collection.indexes["dns_name"].keys()) == {"test1.example.org"}
    assert set(system_collection.indexes["mac_address"].keys()) == {
        "52:54:00:7d:81:f4",
        "52:54:00:7d:81:f6",
    }

    # Cleanup
    for indx_key, _ in system_collection.indexes.items():
        system_collection.indexes[indx_key] = {}


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
    system1.interfaces = {  # type: ignore[method-assign]
        "test1": {
            "ip_address": "192.168.1.1",
            "ipv6_address": "::1",
            "dns_name": "test1.example.org",
            "mac_address": "52:54:00:7d:81:f4",
        },
    }
    interface1 = network_interface.NetworkInterface(cobbler_api, system1.uid)
    interface1.from_dict(
        {
            "ip_address": "192.168.1.3",
            "ipv6_address": "::3",
            "dns_name": "",
            "mac_address": "52:54:00:7d:81:f6",
        }
    )

    # Act
    original_uid = system1.uid
    original_image = system1.image
    system1.name = "test_update_system_indexes_renamed"
    system1.profile = ""  # type: ignore[method-assign]
    system1.image = image1.uid  # type: ignore[method-assign]
    system1.interfaces["test1"].ip_address = "192.168.1.2"
    system1.interfaces["test1"].ipv6_address = "::2"
    system1.interfaces["test1"].dns_name = "test2.example.org"
    system1.interfaces["test1"].mac_address = "52:54:00:7d:81:f5"

    interface1.ip_address = "192.168.1.4"
    interface1.ipv6_address = "::4"
    interface1.dns_name = "test4.example.org"
    interface1.mac_address = "52:54:00:7d:81:f7"

    # Assert
    assert original_uid not in system_collection.indexes["name"]
    assert system_collection.indexes["name"][system1.name] == system1.uid
    assert profile1.name not in system_collection.indexes["profile"]
    assert system_collection.indexes["profile"][system1.profile] == {system1.uid}
    assert original_image not in system_collection.indexes["image"]
    assert system_collection.indexes["image"][system1.image] == {system1.uid}
    assert "192.168.1.1" not in system_collection.indexes["ip_address"]
    assert system_collection.indexes["ip_address"]["192.168.1.2"] == system1.uid
    assert "::1" not in system_collection.indexes["ipv6_address"]
    assert system_collection.indexes["ipv6_address"]["::2"] == system1.uid
    assert "test1.example.org" not in system_collection.indexes["dns_name"]
    assert system_collection.indexes["dns_name"]["test2.example.org"] == system1.uid
    assert "52:54:00:7d:81:f4" not in system_collection.indexes["mac_address"]
    assert system_collection.indexes["mac_address"]["52:54:00:7d:81:f5"] == system1.uid

    assert interface1.ip_address not in system_collection.indexes["ip_address"]
    assert interface1.ipv6_address not in system_collection.indexes["ipv6_address"]
    assert interface1.dns_name not in system_collection.indexes["dns_name"]
    assert interface1.mac_address not in system_collection.indexes["mac_address"]


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
    system1.interfaces = {  # type: ignore[method-assign]
        "default": {
            "ip_address": "192.168.1.1",
            "ipv6_address": "::1",
            "dns_name": "example.org",
            "mac_address": "52:54:00:7d:81:f4",
        }
    }
    original_uid = system1.uid

    # Act
    system_collection.remove_from_indexes(system1)

    # Assert
    assert system1.uid not in system_collection.indexes["name"]
    assert (
        system1.interfaces["default"].ip_address
        not in system_collection.indexes["ip_address"]
    )
    assert (
        system1.interfaces["default"].ipv6_address
        not in system_collection.indexes["ipv6_address"]
    )
    assert (
        system1.interfaces["default"].dns_name
        not in system_collection.indexes["dns_name"]
    )
    assert (
        system1.interfaces["default"].mac_address
        not in system_collection.indexes["mac_address"]
    )

    # Cleanup
    system1.uid = original_uid


def test_find_by_indexes(
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
    system1.interfaces = {  # type: ignore[method-assign]
        "default": {
            "ip_address": "192.168.1.1",
            "ipv6_address": "::1",
            "dns_name": "example.org",
            "mac_address": "52:54:00:7d:81:f4",
        }
    }

    kwargs = {
        "name": [
            {"name": system1.name},
            {"name": "fake_name"},
            {"fake_index": system1.name},
        ],
        "ip_address": [
            {"ip_address": system1.interfaces["default"].ip_address},
            {"ip_address": "fake_ip_addres"},
            {"fake_index": system1.interfaces["default"].ip_address},
        ],
        "ipv6_address": [
            {"ipv6_address": system1.interfaces["default"].ipv6_address},
            {"ipv6_address": "fake_ipv6_addres"},
            {"fake_index": system1.interfaces["default"].ipv6_address},
        ],
        "dns_name": [
            {"dns_name": system1.interfaces["default"].dns_name},
            {"dns_name": "fake_dns_name"},
            {"fake_index": system1.interfaces["default"].dns_name},
        ],
        "mac_address": [
            {"mac_address": system1.interfaces["default"].mac_address},
            {"mac_address": "fake_mac_address"},
            {"fake_index": system1.interfaces["default"].mac_address},
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
