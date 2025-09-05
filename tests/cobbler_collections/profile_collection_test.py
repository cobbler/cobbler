"""
Test module to validate the functionality of the module that is responsible for managing the collection of profiles.
"""

from typing import Any, Callable

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import profiles
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import distro, profile

from tests.conftest import does_not_raise


@pytest.fixture(name="profile_collection")
def fixture_profile_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (Profiles) of a generic collection.
    """
    return cobbler_api.profiles()


def test_obj_create(collection_mgr: CollectionManager):
    """
    Test the creation of a Profiles collection object.
    """
    # Arrange & Act
    test_profile_collection = profiles.Profiles(collection_mgr)

    # Assert
    assert isinstance(test_profile_collection, profiles.Profiles)


def test_factory_produce(
    cobbler_api: CobblerAPI, profile_collection: profiles.Profiles
):
    """
    Test the factory method to produce a Profile item.
    """
    # Arrange & Act
    result_profile = profile_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_profile, profile.Profile)


def test_get(
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    Test retrieving a Profile by name from the collection.
    """
    # Arrange
    name = "test_get"
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)

    # Act
    item = profile_collection.get(test_profile.name)
    fake_item = profile_collection.get("fake_name")

    # Assert
    assert item is not None
    assert item.name == name
    assert fake_item is None


def test_find(
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    Test to verify that a profile can be found inside the collection.
    """
    # Arrange
    name = "test_find"
    test_distro = create_distro()
    create_profile(test_distro.uid)

    # Act
    result = profile_collection.find(True, True, name=name)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    Test converting the profile collection to a list of dictionaries.
    """
    # Arrange
    name = "test_to_list"
    test_distro = create_distro()
    create_profile(test_distro.uid)

    # Act
    result = profile_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(
    create_distro: Callable[[], distro.Distro],
    profile_collection: profiles.Profiles,
):
    """
    Test populating the profile collection from a list of dictionaries.
    """
    # Arrange
    name = "test_from_list"
    distro1 = create_distro()
    item_list = [
        {
            "uid": "c6292be68ce0416490414420a7467b21",
            "name": name,
            "distro": distro1.uid,
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
    Test copying a profile within the collection.
    """
    # pylint: disable=protected-access
    # Arrange
    test_distro = create_distro()
    profile1 = create_profile(test_distro.uid)

    # Act
    new_item_name = "test_copy_successful"
    profile_collection.copy(profile1, new_item_name)
    profile2 = profile_collection.find(False, name=new_item_name)

    # Assert
    assert isinstance(profile2, profile.Profile)
    assert len(profile_collection.listing) == 2
    assert profile1.uid in profile_collection.listing
    assert profile2.uid in profile_collection.listing
    for key, value in profile_collection.indexes.items():
        indx_prop = cobbler_api.settings().memory_indexes["profile"][key]  # type: ignore
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
            assert value[attr_val1] == {profile1.uid, profile2.uid}
            assert value[attr_val2] == {profile1.uid, profile2.uid}
        else:
            assert len(value) == 2
            assert value[attr_val1] == profile1.uid
            assert value[attr_val2] == profile2.uid


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
    Test renaming a profile within the collection.
    """
    # pylint: disable=protected-access
    # Arrange
    test_distro = create_distro()
    profile1 = create_profile(test_distro.uid)

    # Act
    profile_collection.rename(profile1, input_new_name)

    # Assert
    assert profile1.uid in profile_collection.listing
    assert profile_collection.listing[profile1.uid].name == input_new_name
    for key, value in profile_collection.indexes.items():
        indx_prop = cobbler_api.settings().memory_indexes["profile"][key]  # type: ignore
        attr_val = profile_collection._get_index_property(profile1, key)  # type: ignore[reportPrivateUsage]
        if isinstance(attr_val, list):
            attr_val = ""
        elif isinstance(attr_val, enums.ConvertableEnum):
            attr_val = attr_val.value
        if indx_prop["nonunique"]:
            assert value[attr_val] == {profile1.uid}
        else:
            assert value[attr_val] == profile1.uid


def test_collection_add(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    profile_collection: profiles.Profiles,
):
    """
    Test adding a new profile to the collection.
    """
    # pylint: disable=protected-access
    # Arrange
    name = "test_collection_add"
    distro1 = create_distro()
    profile1 = cobbler_api.new_profile()
    profile1.name = name  # type: ignore[method-assign]
    profile1.distro = distro1.uid  # type: ignore[method-assign]

    # Act
    profile_collection.add(profile1)

    # Assert
    assert profile1.uid in profile_collection.listing
    assert profile_collection.listing[profile1.uid].name == name
    for key, value in profile_collection.indexes.items():
        indx_prop = cobbler_api.settings().memory_indexes["profile"][key]  # type: ignore
        attr_val = profile_collection._get_index_property(profile1, key)  # type: ignore[reportPrivateUsage]
        if isinstance(attr_val, list):
            attr_val = ""
        elif isinstance(attr_val, enums.ConvertableEnum):
            attr_val = attr_val.value
        if indx_prop["nonunique"]:
            assert value[attr_val] == {profile1.uid}
        else:
            assert value[attr_val] == profile1.uid


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    Test that adding a duplicate profile name raises an exception and does not modify the collection.
    """
    # Arrange
    name = "test_duplicate_add"
    distro1 = create_distro()
    create_profile(distro1.uid)
    profile2 = cobbler_api.new_profile()
    profile2.name = name  # type: ignore[method-assign]
    profile2.distro = distro1.uid  # type: ignore[method-assign]

    # Act & Assert
    assert len(profile_collection.indexes["name"]) == 1
    with pytest.raises(CX):
        profile_collection.add(profile2, check_for_duplicate_names=True)
    for key, _ in profile_collection.indexes.items():
        assert len(profile_collection.indexes[key]) == 1


def test_remove(
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    Test removing a profile from the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    assert test_profile.uid in profile_collection.listing

    # Pre-Assert to validate if the index is in its correct state
    for key, _ in profile_collection.indexes.items():
        assert len(profile_collection.indexes[key]) == 1

    # Act
    profile_collection.remove(test_profile)

    # Assert
    assert test_profile.uid not in profile_collection.listing
    for key, _ in profile_collection.indexes.items():
        assert len(profile_collection.indexes[key]) == 0


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
    profile_collection: profiles.Profiles,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Test removing a profile from the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)

    # Act
    with expected_exception:
        cobbler_api.distros().remove(test_distro, recursive=recursive)

    # Assert
    assert (test_profile.uid not in profile_collection.listing) == recursive
    for key, _ in profile_collection.indexes.items():
        assert len(profile_collection.indexes[key]) == expected_result


@pytest.mark.parametrize(
    "recursive,expected_exception,expected_result",
    [
        (False, pytest.raises(CX), 1),
        (True, does_not_raise(), 0),
    ],
)
def test_remove_by_repo_dependency(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Test removing a profile from the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_repo = cobbler_api.new_repo()
    test_repo.name = "test_repo"  # type: ignore[method-assign]
    cobbler_api.repos().add(test_repo)
    test_profile.repos = [test_repo.uid]  # type: ignore[method-assign]

    # Act
    with expected_exception:
        cobbler_api.repos().remove(test_repo, recursive=recursive)

    # Assert
    assert (test_profile.uid not in profile_collection.listing) == recursive
    for key, _ in profile_collection.indexes.items():
        assert len(profile_collection.indexes[key]) == expected_result


@pytest.mark.parametrize(
    "recursive,expected_exception,expected_result",
    [
        (False, pytest.raises(CX), 1),
        (True, does_not_raise(), 0),
    ],
)
def test_remove_by_menu_dependency(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Test removing a profile from the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_menu = cobbler_api.new_menu()
    test_menu.name = "test_menu"  # type: ignore[method-assign]
    cobbler_api.menus().add(test_menu)
    test_profile.menu = test_menu.uid  # type: ignore[method-assign]

    # Act
    with expected_exception:
        cobbler_api.menus().remove(test_menu, recursive=recursive)

    # Assert
    assert (test_profile.uid not in profile_collection.listing) == recursive
    for key, _ in profile_collection.indexes.items():
        assert len(profile_collection.indexes[key]) == expected_result


@pytest.mark.parametrize(
    "recursive,expected_exception,expected_result",
    [
        (False, pytest.raises(CX), 1),
        (True, does_not_raise(), 0),
    ],
)
def test_remove_by_parent_dependency(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[..., profile.Profile],
    profile_collection: profiles.Profiles,
    recursive: bool,
    expected_exception: Any,
    expected_result: int,
):
    """
    Test removing a profile from the collection.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_parent_profile = create_profile(test_distro.uid, name="test_parent_profile")
    test_profile.parent = test_parent_profile.uid  # type: ignore[method-assign]

    # Act
    with expected_exception:
        profile_collection.remove(test_parent_profile, recursive=recursive)

    # Assert
    assert (test_profile.uid not in profile_collection.listing) == recursive
    for key, _ in profile_collection.indexes.items():
        assert len(profile_collection.indexes[key]) >= expected_result


def test_indexes(
    profile_collection: profiles.Profiles,
):
    """
    Test to validate that the profile collection has the expected indexes initialized.
    """
    # Arrange

    # Assert
    assert len(profile_collection.indexes) == 6
    assert len(profile_collection.indexes["name"]) == 0
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
    Test adding a profile to the collection's indexes.
    """
    # pylint: disable=protected-access
    # Arrange
    test_distro = create_distro()
    profile1 = create_profile(test_distro.uid)
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
        indx_prop = cobbler_api.settings().memory_indexes["profile"][key]  # type: ignore
        attr_val = profile_collection._get_index_property(profile1, key)  # type: ignore[reportPrivateUsage]
        if isinstance(attr_val, list):
            attr_val = ""
        elif isinstance(attr_val, enums.ConvertableEnum):
            attr_val = attr_val.value
        if indx_prop["nonunique"]:
            assert {attr_val: {profile1.uid}} == value
        else:
            assert {attr_val: profile1.uid} == value


def test_update_profile_name_index(
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    Test renaming a profile within the collection.
    """
    # Arrange
    test_distro = create_distro()
    profile1 = create_profile(test_distro.uid)
    new_name = "test_name_renamed"
    original_name = profile1.name

    # Act
    profile1.name = new_name  # type: ignore[method-assign]

    # Assert
    assert original_name not in profile_collection.indexes["name"]
    assert profile_collection.indexes["name"][new_name] == profile1.uid


def test_update_profile_parent_index(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    Test updating the parent index of a profile within the collection.
    """
    # Arrange
    distro1 = create_distro()
    profile1 = create_profile(distro1.uid)
    profile2 = cobbler_api.new_profile()
    profile2.name = "test_update_profile_parent_index2"  # type: ignore[method-assign]
    profile2.distro = distro1.uid  # type: ignore[method-assign]
    profile_collection.add(profile2)

    # Act
    profile1.parent = profile2.uid  # type: ignore[method-assign]

    # Assert
    assert profile1.name not in profile_collection.indexes["parent"]
    assert profile_collection.indexes["parent"][profile2.uid] == {profile1.uid}


def test_update_profile_distro_index(
    create_distro: Callable[[str], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    Test updating the distro index of a profile within the collection.
    """
    # Arrange
    name = "test_update_profile_distro_index"
    distro1 = create_distro(name)
    distro2 = create_distro("test_update_profile_distro_index_new")
    profile1 = create_profile(distro1.uid)

    # Act
    original_distro = distro1.uid
    profile1.distro = distro2.uid  # type: ignore[method-assign]

    # Assert
    assert original_distro not in profile_collection.indexes["distro"]
    result = profile_collection.indexes["distro"][profile1.distro.uid]  # type: ignore
    assert result == {profile1.uid}


def test_update_profile_arch_index(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    Test updating the arch index of profiles within the collection.
    """
    # Arrange - All distros and profiles have x86_64 as arch
    name = "test_update_profile_arch_index"
    distro1 = create_distro(name)
    distro2: distro.Distro = create_distro("test_update_profile_arch_index_new")
    profile1 = create_profile(distro1.uid)
    profile2 = cobbler_api.new_profile(
        name="test_update_profile_arch_index2", distro=distro2.uid
    )
    profile_collection.add(profile2)
    profile3 = cobbler_api.new_profile(
        name="test_update_profile_arch_index3", distro=distro1.uid
    )
    profile_collection.add(profile3)

    # Act & Assert
    assert profile_collection.indexes["arch"][enums.Archs.X86_64.value] == {
        profile1.uid,
        profile2.uid,
        profile3.uid,
    }

    # Now distro2 and profile2 have i386 as arch
    distro2.arch = enums.Archs.I386  # type: ignore[method-assign]
    assert profile_collection.indexes["arch"][enums.Archs.X86_64.value] == {
        profile1.uid,
        profile3.uid,
    }
    assert profile_collection.indexes["arch"][enums.Archs.I386.value] == {profile2.uid}

    # Now distro2, profile1 and profile2 have i386 as arch
    profile1.distro = distro2.uid  # type: ignore[method-assign]
    assert profile_collection.indexes["arch"][enums.Archs.X86_64.value] == {
        profile3.uid
    }
    assert profile_collection.indexes["arch"][enums.Archs.I386.value] == {
        profile1.uid,
        profile2.uid,
    }

    # Now set profile3 as parent to profile2, thus giving profile2 the arch x86_64 again
    profile2.parent = profile3.uid  # type: ignore[method-assign]
    assert profile_collection.indexes["arch"][enums.Archs.X86_64.value] == {
        profile2.uid,
        profile3.uid,
    }
    assert profile_collection.indexes["arch"][enums.Archs.I386.value] == {profile1.uid}

    # Now set the parent of profile3 to profile1, thus giving profile3 the arch i386
    profile3.parent = profile1.uid  # type: ignore[method-assign]
    assert enums.Archs.X86_64.value not in profile_collection.indexes["arch"]
    assert profile_collection.indexes["arch"][enums.Archs.I386.value] == {
        profile1.uid,
        profile2.uid,
        profile3.uid,
    }

    # Now set distro2 as x86_64 and have all items as x86_64
    distro2.arch = enums.Archs.X86_64  # type: ignore[method-assign]
    assert profile_collection.indexes["arch"][enums.Archs.X86_64.value] == {
        profile1.uid,
        profile2.uid,
        profile3.uid,
    }
    assert enums.Archs.I386.value not in profile_collection.indexes["arch"]


def test_update_profile_menu_index(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    Test updating the menu index of a profile within the collection.
    """
    # Arrange
    name = "test_update_profile_menu_index"
    test_distro = create_distro()
    profile1 = create_profile(test_distro.uid)
    menu1 = cobbler_api.new_menu()
    menu1.name = name  # type: ignore[method-assign]
    cobbler_api.menus().add(menu1)

    # Act
    original_menu = profile1.menu
    profile1.menu = menu1.uid  # type: ignore[method-assign]

    # Assert
    assert original_menu not in profile_collection.indexes["menu"]
    assert profile_collection.indexes["menu"][profile1.menu] == {profile1.uid}


def test_update_profile_repos_index(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    Test updating the repos index of profiles within the collection.
    """
    # Arrange
    name = "test_update_profile_repos_index"
    distro1 = create_distro()
    profile1 = create_profile(distro1.uid)
    profile2 = cobbler_api.new_profile()
    profile2.name = "test_update_profile2"  # type: ignore[method-assign]
    profile2.distro = distro1.uid  # type: ignore[method-assign]
    profile_collection.add(profile2)
    repo1 = cobbler_api.new_repo()
    repo1.name = name  # type: ignore[method-assign]
    cobbler_api.repos().add(repo1)

    # Act
    profile1.repos = repo1.uid  # type: ignore[method-assign]
    profile2.repos = [repo1.uid]  # type: ignore[method-assign]

    # Assert
    assert profile_collection.indexes["repos"][repo1.uid] == {
        profile1.uid,
        profile2.uid,
    }


def test_remove_from_indexes(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    Test removing a profile from the collection's indexes.
    """
    # Arrange
    name = "test_remove_from_indexes"
    distro1 = create_distro()
    profile1 = create_profile(distro1.uid)
    profile2 = cobbler_api.new_profile()
    profile2.name = "test_remove_from_indexe2"  # type: ignore[method-assign]
    profile2.distro = distro1.uid  # type: ignore[method-assign]
    profile_collection.add(profile2)
    profile1.parent = profile2.uid  # type: ignore[method-assign]
    menu1 = cobbler_api.new_menu()
    menu1.name = name  # type: ignore[method-assign]
    cobbler_api.menus().add(menu1)
    profile1.menu = menu1.uid  # type: ignore[method-assign]
    repo1 = cobbler_api.new_repo()
    repo1.name = name  # type: ignore[method-assign]
    cobbler_api.repos().add(repo1)
    profile1.repos = repo1.uid  # type: ignore[method-assign]

    # Act
    profile_collection.remove_from_indexes(profile1)

    # Assert
    assert profile1.name not in profile_collection.indexes["name"]
    assert profile1.get_parent not in profile_collection.indexes["parent"]
    assert profile_collection.indexes["distro"][profile2.distro.uid] == {profile2.uid}  # type: ignore
    assert profile_collection.indexes["arch"][profile2.arch.value] == {profile2.uid}  # type: ignore
    assert profile1.menu not in profile_collection.indexes["menu"]
    assert profile1.repos[0] not in profile_collection.indexes["repos"]

    # Cleanup
    profile_collection.add_to_indexes(profile1)


def test_find_by_indexes(
    create_distro: Callable[[], distro.Distro],
    create_profile: Callable[[str], profile.Profile],
    profile_collection: profiles.Profiles,
):
    """
    Test finding profiles by various indexes within the collection.
    """
    # Arrange
    distro1 = create_distro()
    profile1 = create_profile(distro1.uid)
    kargs1 = {"name": profile1.name}
    kargs2 = {"name": "fake_uid"}
    kargs3 = {"fake_index": profile1.uid}
    kargs4 = {"parent": ""}
    kargs5 = {"parent": "fake_parent"}
    kargs6 = {"menu": ""}
    kargs7 = {"parent": "fake_menu"}
    kargs8 = {"repos": ""}
    kargs9 = {"repos": "fake_repos"}
    kargs10 = {"distro": distro1.uid}
    kargs11 = {"repos": "fake_distro"}
    kargs12 = {"arch": profile1.arch.value}  # type: ignore[reportOptionalMemberAccess,union-attr]
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
