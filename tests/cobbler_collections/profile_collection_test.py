"""
TODO
"""

from typing import Any, Callable

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import profiles
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import distro, menu, profile, repo


@pytest.fixture(name="profile_collection")
def fixture_profile_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (Profiles) of a generic collection.
    """
    return cobbler_api.profiles()


def test_obj_create(collection_mgr: CollectionManager):
    """
    TODO
    """
    # Arrange & Act
    test_profile_collection = profiles.Profiles(collection_mgr)

    # Assert
    assert isinstance(test_profile_collection, profiles.Profiles)


def test_factory_produce(
    cobbler_api: CobblerAPI, profile_collection: profiles.Profiles
):
    """
    TODO
    """
    # Arrange & Act
    result_profile = profile_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_profile, profile.Profile)


def test_get(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    TODO
    """
    # Arrange
    name = "test_get"
    create_distro()
    create_profile(name)

    # Act
    item = profile_collection.get(name)
    fake_item = profile_collection.get("fake_name")

    # Assert
    assert item is not None
    assert item.name == name
    assert fake_item is None


def test_find(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    TODO
    """
    # Arrange
    name = "test_find"
    create_distro()
    create_profile(name)

    # Act
    result = profile_collection.find(name, True, True)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    TODO
    """
    # Arrange
    name = "test_to_list"
    create_distro()
    create_profile(name)

    # Act
    result = profile_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    profile_collection: profiles.Profiles,
):
    """
    TODO
    """
    # Arrange
    name = "test_from_list"
    distro1 = create_distro()
    item_list = [
        {
            "name": name,
            "distro": distro1.name,
        },
    ]

    # Act
    profile_collection.from_list(item_list)

    # Assert
    assert len(profile_collection.listing) == 1
    for indx in profile_collection.indexes.values():
        assert len(indx) == 1


def test_copy(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    TODO
    """
    # pylint: disable=protected-access
    # Arrange
    name = "test_copy"
    create_distro()
    profile1 = create_profile(name)

    # Act
    new_item_name = "test_copy_successful"
    profile_collection.copy(profile1, new_item_name)
    profile2 = profile_collection.find(new_item_name, False)

    # Assert
    assert isinstance(profile2, profile.Profile)
    assert len(profile_collection.listing) == 2
    assert name in profile_collection.listing
    assert new_item_name in profile_collection.listing
    for key, value in profile_collection.indexes.items():
        indx_prop = cobbler_api.settings().memory_indexes["profile"][key]
        attr_val1 = profile_collection._get_index_property(profile1, key)  # type: ignore[reportPrivateUsage]
        attr_val2 = profile_collection._get_index_property(profile2, key)  # type: ignore[reportPrivateUsage]
        if isinstance(attr_val1, list):
            attr_val1 = ""
        elif isinstance(attr_val1, enums.ConvertableEnum):
            attr_val1 = attr_val1.value
        if isinstance(attr_val2, list):
            attr_val2 = ""
        elif isinstance(attr_val2, enums.ConvertableEnum):
            attr_val2 = attr_val2.value
        if indx_prop["nonunique"]:
            assert len(value) == 1
            assert value[attr_val1] == {name, new_item_name}
            assert value[attr_val2] == {name, new_item_name}
        else:
            assert len(value) == 2
            assert value[attr_val1] == name
            assert value[attr_val2] == new_item_name


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
    profile_collection: profiles.Profiles,
    input_new_name: str,
):
    """
    TODO
    """
    # pylint: disable=protected-access
    # Arrange
    name = "test_rename"
    create_distro()
    profile1 = create_profile(name)

    # Act
    profile_collection.rename(profile1, input_new_name)

    # Assert
    assert input_new_name in profile_collection.listing
    assert profile_collection.listing[input_new_name].name == input_new_name
    for key, value in profile_collection.indexes.items():
        indx_prop = cobbler_api.settings().memory_indexes["profile"][key]
        attr_val = profile_collection._get_index_property(profile1, key)  # type: ignore[reportPrivateUsage]
        if isinstance(attr_val, list):
            attr_val = ""
        elif isinstance(attr_val, enums.ConvertableEnum):
            attr_val = attr_val.value
        if indx_prop["nonunique"]:
            assert value[attr_val] == {input_new_name}
        else:
            assert value[attr_val] == input_new_name


def test_collection_add(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    TODO
    """
    # pylint: disable=protected-access
    # Arrange
    name = "test_collection_add"
    distro1 = create_distro()
    profile1 = profile.Profile(cobbler_api)
    profile1.name = name
    profile1.distro = distro1.name

    # Act
    profile_collection.add(profile1)

    # Assert
    assert name in profile_collection.listing
    assert profile_collection.listing[name].name == name
    for key, value in profile_collection.indexes.items():
        indx_prop = cobbler_api.settings().memory_indexes["profile"][key]
        attr_val = profile_collection._get_index_property(profile1, key)  # type: ignore[reportPrivateUsage]
        if isinstance(attr_val, list):
            attr_val = ""
        elif isinstance(attr_val, enums.ConvertableEnum):
            attr_val = attr_val.value
        if indx_prop["nonunique"]:
            assert value[attr_val] == {name}
        else:
            assert value[attr_val] == name


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    TODO
    """
    # Arrange
    name = "test_duplicate_add"
    distro1 = create_distro()
    create_profile(name)
    profile2 = profile.Profile(cobbler_api)
    profile2.name = name
    profile2.distro = distro1.name

    # Act & Assert
    assert len(profile_collection.indexes["uid"]) == 1
    with pytest.raises(CX):
        profile_collection.add(profile2, check_for_duplicate_names=True)
    for key, _ in profile_collection.indexes.items():
        assert len(profile_collection.indexes[key]) == 1


def test_remove(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    TODO
    """
    # Arrange
    name = "test_remove"
    create_distro()
    create_profile(name)
    assert name in profile_collection.listing

    # Pre-Assert to validate if the index is in its correct state
    for key, _ in profile_collection.indexes.items():
        assert len(profile_collection.indexes[key]) == 1

    # Act
    profile_collection.remove(name)

    # Assert
    assert name not in profile_collection.listing
    for key, _ in profile_collection.indexes.items():
        assert len(profile_collection.indexes[key]) == 0


def test_indexes(
    cobbler_api: CobblerAPI,
    profile_collection: profiles.Profiles,
):
    """
    TODO
    """
    # Arrange

    # Assert
    assert len(profile_collection.indexes) == 6
    assert len(profile_collection.indexes["uid"]) == 0
    assert len(profile_collection.indexes["parent"]) == 0
    assert len(profile_collection.indexes["distro"]) == 0
    assert len(profile_collection.indexes["arch"]) == 0
    assert len(profile_collection.indexes["menu"]) == 0
    assert len(profile_collection.indexes["repos"]) == 0


def test_add_to_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    TODO
    """
    # pylint: disable=protected-access
    # Arrange
    name = "test_add_to_indexes"
    create_distro()
    profile1 = create_profile(name)
    for key, value in profile_collection.indexes.items():
        attr_val = profile_collection._get_index_property(profile1, key)  # type: ignore[reportPrivateUsage]
        if isinstance(attr_val, list):
            attr_val = ""
        elif isinstance(attr_val, enums.ConvertableEnum):
            attr_val = attr_val.value
        del value[attr_val]

    # Act
    profile_collection.add_to_indexes(profile1)

    # Assert
    for key, value in profile_collection.indexes.items():
        indx_prop = cobbler_api.settings().memory_indexes["profile"][key]
        attr_val = profile_collection._get_index_property(profile1, key)  # type: ignore[reportPrivateUsage]
        if isinstance(attr_val, list):
            attr_val = ""
        elif isinstance(attr_val, enums.ConvertableEnum):
            attr_val = attr_val.value
        if indx_prop["nonunique"]:
            assert {attr_val: {profile1.name}} == value
        else:
            assert {attr_val: profile1.name} == value


def test_update_profile_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Any,
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    TODO
    """
    # Arrange
    name = "test_update_profile_indexes"
    distro1: distro.Distro = create_distro()
    distro2: distro.Distro = create_distro("test_update_profile_indexes_new")
    profile1 = create_profile(name)
    profile2 = profile.Profile(cobbler_api)
    profile2.name = "test_update_profile2"
    profile2.distro = distro2.name
    profile_collection.add(profile2)
    menu1 = menu.Menu(cobbler_api)
    menu1.name = name
    cobbler_api.menus().add(menu1)
    repo1 = repo.Repo(cobbler_api)
    repo1.name = name
    cobbler_api.repos().add(repo1)

    # Act
    original_uid = profile1.uid
    original_distro = distro1.name
    original_menu = profile1.menu
    profile1.uid = "test_uid"
    profile1.parent = profile2.name
    profile1.distro = distro2.name
    profile1.menu = menu1.name
    profile1.repos = repo1.name
    profile2.repos = [repo1.name]

    # Assert
    assert original_uid not in profile_collection.indexes["uid"]
    assert profile_collection.indexes["uid"]["test_uid"] == profile1.name
    assert profile1.name not in profile_collection.indexes["parent"]
    assert profile_collection.indexes["parent"][profile1.get_parent] == {profile1.name}
    assert original_distro not in profile_collection.indexes["distro"]
    assert profile_collection.indexes["distro"][profile1.distro.name] == {  # type: ignore[reportOptionalMemberAccess]
        profile1.name,
        profile2.name,
    }
    assert profile1.name not in profile_collection.indexes["menu"][original_menu]
    assert profile_collection.indexes["menu"][profile1.menu] == {profile1.name}
    assert profile_collection.indexes["repos"][repo1.name] == {
        profile1.name,
        profile2.name,
    }


def test_remove_from_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    TODO
    """
    # Arrange
    name = "test_remove_from_indexes"
    distro1 = create_distro()
    profile1 = create_profile(name)
    profile2 = profile.Profile(cobbler_api)
    profile2.name = "test_remove_from_indexe2"
    profile2.distro = distro1.name
    profile_collection.add(profile2)
    profile1.parent = profile2.name
    menu1 = menu.Menu(cobbler_api)
    menu1.name = name
    cobbler_api.menus().add(menu1)
    profile1.menu = menu1.name
    repo1 = repo.Repo(cobbler_api)
    repo1.name = name
    cobbler_api.repos().add(repo1)
    profile1.repos = repo1.name

    # Act
    profile_collection.remove_from_indexes(profile1)

    # Assert
    assert profile1.uid not in profile_collection.indexes["uid"]
    assert profile1.get_parent not in profile_collection.indexes["parent"]
    assert profile_collection.indexes["distro"][profile1.distro.name] == {profile2.name}  # type: ignore[reportOptionalMemberAccess]
    assert profile_collection.indexes["arch"][profile1.arch.value] == {profile2.name}  # type: ignore[reportOptionalMemberAccess]
    assert profile1.menu not in profile_collection.indexes["menu"]
    assert profile1.repos[0] not in profile_collection.indexes["repos"]

    # Cleanup
    profile_collection.add_to_indexes(profile1)


def test_find_by_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    TODO
    """
    # Arrange
    name = "test_find_by_indexes"
    distro1 = create_distro()
    profile1 = create_profile(name)
    kargs1 = {"uid": profile1.uid}
    kargs2 = {"uid": "fake_uid"}
    kargs3 = {"fake_index": profile1.uid}
    kargs4 = {"parent": ""}
    kargs5 = {"parent": "fake_parent"}
    kargs6 = {"menu": ""}
    kargs7 = {"parent": "fake_menu"}
    kargs8 = {"repos": ""}
    kargs9 = {"repos": "fake_repos"}
    kargs10 = {"distro": distro1.name}
    kargs11 = {"repos": "fake_distro"}
    kargs12 = {"arch": profile1.arch.value}  # type: ignore[reportOptionalMemberAccess]
    kargs13 = {"repos": "fake_arch"}

    # Act
    result1 = profile_collection.find_by_indexes(kargs1)
    result2 = profile_collection.find_by_indexes(kargs2)
    result3 = profile_collection.find_by_indexes(kargs3)
    result4 = profile_collection.find_by_indexes(kargs4)
    result5 = profile_collection.find_by_indexes(kargs5)
    result6 = profile_collection.find_by_indexes(kargs6)
    result7 = profile_collection.find_by_indexes(kargs7)
    result8 = profile_collection.find_by_indexes(kargs8)
    result9 = profile_collection.find_by_indexes(kargs9)
    result10 = profile_collection.find_by_indexes(kargs10)
    result11 = profile_collection.find_by_indexes(kargs11)
    result12 = profile_collection.find_by_indexes(kargs12)
    result13 = profile_collection.find_by_indexes(kargs13)

    # Assert
    assert isinstance(result1, list)
    assert len(result1) == 1
    assert result1[0] == profile1
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
    assert result8 is not None
    assert len(result8) == 1
    assert len(kargs8) == 0
    assert result9 is None
    assert len(kargs9) == 0
    assert result10 is not None
    assert len(result10) == 1
    assert len(kargs10) == 0
    assert result11 is None
    assert len(kargs11) == 0
    assert result12 is not None
    assert len(result12) == 1
    assert len(kargs12) == 0
    assert result13 is None
    assert len(kargs13) == 0
