"""
Test module to validate the functionality of the module that is responsible for managing the collection of repos.
"""

import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import repos
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import repo


@pytest.fixture(name="repo_collection")
def fixture_repo_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (Repos) of a generic collection.
    """
    return cobbler_api.repos()


def test_obj_create(collection_mgr: CollectionManager):
    """
    Test the instantiation of the Repos collection.
    """
    # Arrange & Act
    repo_collection = repos.Repos(collection_mgr)

    # Assert
    assert isinstance(repo_collection, repos.Repos)


def test_factory_produce(cobbler_api: CobblerAPI, repo_collection: repos.Repos):
    """
    Test the factory method to produce a Repo item.
    """
    # Arrange & Act
    result_repo = repo_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_repo, repo.Repo)


def test_get(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    """
    Test retrieving a Repo item by name.
    """
    # Arrange
    name = "test_get"
    item1 = cobbler_api.new_repo()
    item1.name = name  # type: ignore[method-assign]
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
    """
    Test to verify that a repo can be found inside the collection.
    """
    # Arrange
    name = "test_find"
    item1 = cobbler_api.new_repo()
    item1.name = name  # type: ignore[method-assign]
    repo_collection.add(item1)

    # Act
    result = repo_collection.find(True, True, name=name)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    """
    Test to verify that the collection can be converted to a list of dictionaries.
    """
    # Arrange
    name = "test_to_list"
    item1 = cobbler_api.new_repo()
    item1.name = name  # type: ignore[method-assign]
    repo_collection.add(item1)

    # Act
    result = repo_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(
    repo_collection: repos.Repos,
):
    """
    Test to verify that the collection can be populated from a list of dictionaries.
    """
    # Arrange
    item_list = [{"name": "test_from_list"}]

    # Act
    repo_collection.from_list(item_list)

    # Assert
    assert len(repo_collection.listing) == 1
    assert len(repo_collection.indexes["name"]) == 1


def test_copy(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    """
    Test to verify that a repo can be copied inside the collection.
    """
    # Arrange
    name = "test_copy"
    item1 = cobbler_api.new_repo(name=name)
    repo_collection.add(item1)
    new_item_name = "test_copy_new"

    # Act
    repo_collection.copy(item1, new_item_name)
    item2 = repo_collection.find(False, name=new_item_name)
    assert isinstance(item2, repo.Repo)
    item2.parent = item1.uid  # type: ignore[method-assign]

    # Assert
    assert len(repo_collection.listing) == 2
    assert item1.uid in repo_collection.listing
    assert item2.uid in repo_collection.listing
    assert len(repo_collection.indexes["name"]) == 2
    assert (repo_collection.indexes["name"])[item1.name] == item1.uid
    assert (repo_collection.indexes["name"])[new_item_name] == item2.uid


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
    """
    Test to verify that a repo can be renamed inside the collection.
    """
    # Arrange
    old_name = "test_rename"
    item1 = cobbler_api.new_repo()
    item1.name = old_name  # type: ignore[method-assign]
    repo_collection.add(item1)

    # Act
    repo_collection.rename(item1, input_new_name)

    # Assert
    assert item1.uid in repo_collection.listing
    assert repo_collection.listing[item1.uid].name == input_new_name
    assert (repo_collection.indexes["name"])[input_new_name] == item1.uid


def test_collection_add(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    """
    Test to verify that a repo can be added to the collection.
    """
    # Arrange
    name = "test_collection_add"
    item1 = cobbler_api.new_repo(name=name)

    # Act
    repo_collection.add(item1)

    # Assert
    assert item1.uid in repo_collection.listing
    assert name in repo_collection.indexes["name"]


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    """
    Test to verify that adding a repo with a duplicate name raises an exception.
    """
    # Arrange
    name = "duplicate_name"
    item1 = cobbler_api.new_repo()
    item1.name = name  # type: ignore[method-assign]
    repo_collection.add(item1)
    item2 = cobbler_api.new_repo()
    item2.name = name  # type: ignore[method-assign]

    # Act & Assert
    with pytest.raises(CX):
        repo_collection.add(item2, check_for_duplicate_names=True)


def test_remove(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    """
    Test to verify that a repo can be removed from the collection.
    """
    # Arrange
    name = "test_remove"
    item1 = cobbler_api.new_repo(name=name)
    repo_collection.add(item1)
    assert item1.uid in repo_collection.listing
    assert len(repo_collection.indexes["name"]) == 1
    assert (repo_collection.indexes["name"])[item1.name] == item1.uid

    # Act
    repo_collection.remove(item1)

    # Assert
    assert item1.uid not in repo_collection.listing
    assert len(repo_collection.indexes["name"]) == 0


def test_indexes(
    repo_collection: repos.Repos,
):
    """
    Test to verify that the collection's indexes are correctly initialized.
    """
    # Arrange

    # Assert
    assert len(repo_collection.indexes) == 1
    assert len(repo_collection.indexes["name"]) == 0


def test_add_to_indexes(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    """
    Test to verify that a repo can be added to the collection's indexes.
    """
    # Arrange
    name = "test_add_to_indexes"
    item1 = cobbler_api.new_repo(name=name)
    repo_collection.add(item1)

    # Act
    del (repo_collection.indexes["name"])[item1.name]
    repo_collection.add_to_indexes(item1)

    # Assert
    assert item1.name in repo_collection.indexes["name"]


def test_remove_from_indexes(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    """
    Test to verify that a repo can be removed from the collection's indexes.
    """
    # Arrange
    name = "test_remove_from_indexes"
    item1 = cobbler_api.new_repo(name=name)
    repo_collection.add(item1)

    # Act
    repo_collection.remove_from_indexes(item1)

    # Assert
    assert item1.uid not in repo_collection.indexes["name"]


def test_update_indexes(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    """
    Test to verify that a repo's indexes can be updated in the collection.
    """
    # Arrange
    name = "test_update_indexes"
    item1 = cobbler_api.new_repo(name=name)
    repo_collection.add(item1)
    name_test = "test_update_indexes_new"

    # Act
    item1.name = name_test  # type: ignore[method-assign]

    # Assert
    assert repo_collection.indexes["name"][name_test] == item1.uid


def test_find_by_indexes(
    cobbler_api: CobblerAPI,
    repo_collection: repos.Repos,
):
    """
    Test to verify that a repo can be found by its indexes in the collection.
    """
    # Arrange
    name = "test_find_by_indexes"
    item1 = cobbler_api.new_repo(name=name)
    repo_collection.add(item1)
    kwargs1 = {"name": item1.name}
    kwargs2 = {"name": "fake_uid"}
    kwargs3 = {"fake_index": item1.uid}

    # Act
    result1 = repo_collection.find_by_indexes(kwargs1)
    result2 = repo_collection.find_by_indexes(kwargs2)
    result3 = repo_collection.find_by_indexes(kwargs3)

    # Assert
    assert isinstance(result1, list)
    assert len(result1) == 1
    assert result1[0] == item1
    assert len(kwargs1) == 0
    assert result2 is None
    assert len(kwargs2) == 0
    assert result3 is None
    assert len(kwargs3) == 1
