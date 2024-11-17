import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import repos
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import repo


@pytest.fixture
def repo_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (Repos) of a generic collection.
    """
    return cobbler_api.repos()


def test_obj_create(collection_mgr: CollectionManager):
    # Arrange & Act
    repo_collection = repos.Repos(collection_mgr)

    # Assert
    assert isinstance(repo_collection, repos.Repos)


def test_factory_produce(cobbler_api: CobblerAPI, repo_collection: repos.Repos):
    # Arrange & Act
    result_repo = repo_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_repo, repo.Repo)


def test_get(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    # Arrange
    name = "test_get"
    item1 = repo.Repo(cobbler_api)
    item1.name = name
    repo_collection.add(item1)

    # Act
    item = repo_collection.get(name)
    fake_item = repo_collection.get("fake_name")

    # Assert
    assert isinstance(item, repo.Repo)
    assert item.name == name
    assert fake_item is None


def test_find(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    # Arrange
    name = "test_find"
    item1 = repo.Repo(cobbler_api)
    item1.name = name
    repo_collection.add(item1)

    # Act
    result = repo_collection.find(name, True, True)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    # Arrange
    name = "test_to_list"
    item1 = repo.Repo(cobbler_api)
    item1.name = name
    repo_collection.add(item1)

    # Act
    result = repo_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(
    repo_collection: repos.Repos,
):
    # Arrange
    item_list = [{"name": "test_from_list"}]

    # Act
    repo_collection.from_list(item_list)

    # Assert
    assert len(repo_collection.listing) == 1
    assert len(repo_collection.indexes["uid"]) == 1


def test_copy(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    # Arrange
    name = "test_copy"
    item1 = repo.Repo(cobbler_api)
    item1.name = name
    repo_collection.add(item1)

    # Act
    new_item_name = "test_copy_new"
    repo_collection.copy(item1, new_item_name)
    item2 = repo_collection.find(new_item_name, False)
    assert isinstance(item2, repo.Repo)
    item2.parent = name

    # Assert
    assert len(repo_collection.listing) == 2
    assert name in repo_collection.listing
    assert new_item_name in repo_collection.listing
    assert len(repo_collection.indexes["uid"]) == 2
    assert (repo_collection.indexes["uid"])[item1.uid] == name
    assert (repo_collection.indexes["uid"])[item2.uid] == new_item_name


@pytest.mark.parametrize(
    "input_new_name",
    [
        ("to_be_renamed"),
        ("UpperCase"),
    ],
)
def test_rename(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
    input_new_name: str,
):
    # Arrange
    old_name = "test_rename"
    item1 = repo.Repo(cobbler_api)
    item1.name = old_name
    repo_collection.add(item1)

    # Act
    repo_collection.rename(item1, input_new_name)

    # Assert
    assert input_new_name in repo_collection.listing
    assert repo_collection.listing[input_new_name].name == input_new_name
    assert (repo_collection.indexes["uid"])[item1.uid] == input_new_name


def test_collection_add(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    # Arrange
    name = "test_collection_add"
    item1 = repo.Repo(cobbler_api)
    item1.name = name

    # Act
    repo_collection.add(item1)

    # Assert
    assert name in repo_collection.listing
    assert item1.uid in repo_collection.indexes["uid"]


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    # Arrange
    name = "duplicate_name"
    item1 = repo.Repo(cobbler_api)
    item1.name = name
    repo_collection.add(item1)
    item2 = repo.Repo(cobbler_api)
    item2.name = name

    # Act & Assert
    with pytest.raises(CX):
        repo_collection.add(item2, check_for_duplicate_names=True)


def test_remove(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    # Arrange
    name = "test_remove"
    item1 = repo.Repo(cobbler_api)
    item1.name = name
    repo_collection.add(item1)
    assert name in repo_collection.listing
    assert len(repo_collection.indexes["uid"]) == 1
    assert (repo_collection.indexes["uid"])[item1.uid] == item1.name

    # Act
    repo_collection.remove(name)

    # Assert
    assert name not in repo_collection.listing
    assert len(repo_collection.indexes["uid"]) == 0


def test_indexes(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    # Arrange

    # Assert
    assert len(repo_collection.indexes) == 1
    assert len(repo_collection.indexes["uid"]) == 0


def test_add_to_indexes(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    # Arrange
    name = "test_add_to_indexes"
    item1 = repo.Repo(cobbler_api)
    item1.name = name
    repo_collection.add(item1)

    # Act
    del (repo_collection.indexes["uid"])[item1.uid]
    repo_collection.add_to_indexes(item1)

    # Assert
    #    assert 0 == 1
    assert item1.uid in repo_collection.indexes["uid"]


def test_remove_from_indexes(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    # Arrange
    name = "test_remove_from_indexes"
    item1 = repo.Repo(cobbler_api)
    item1.name = name
    repo_collection.add(item1)

    # Act
    repo_collection.remove_from_indexes(item1)

    # Assert
    assert item1.uid not in repo_collection.indexes["uid"]


def test_update_indexes(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    # Arrange
    name = "test_update_indexes"
    item1 = repo.Repo(cobbler_api)
    item1.name = name
    repo_collection.add(item1)
    uid1_test = "test_uid"

    # Act
    item1.uid = uid1_test

    # Assert
    assert repo_collection.indexes["uid"][uid1_test] == name


def test_find_by_indexes(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    # Arrange
    name = "test_find_by_indexes"
    item1 = repo.Repo(cobbler_api)
    item1.name = name
    repo_collection.add(item1)
    kargs1 = {"uid": item1.uid}
    kargs2 = {"uid": "fake_uid"}
    kargs3 = {"fake_index": item1.uid}

    # Act
    result1 = repo_collection.find_by_indexes(kargs1)
    result2 = repo_collection.find_by_indexes(kargs2)
    result3 = repo_collection.find_by_indexes(kargs3)

    # Assert
    assert isinstance(result1, list)
    assert len(result1) == 1
    assert result1[0] == item1
    assert len(kargs1) == 0
    assert result2 is None
    assert len(kargs2) == 0
    assert result3 is None
    assert len(kargs3) == 1
