"""
Tests that validate the functionality of the module that is responsible for providing XML-RPC calls related to
repositories.
"""

import pytest

from cobbler.remote import CobblerXMLRPCInterface


@pytest.fixture
def create_repo(remote: CobblerXMLRPCInterface, token: str):
    """
    Creates a Repository "testrepo0" with a mirror "http://www.sample.com/path/to/some/repo" and the attribute
    "mirror_locally=0".

    :param remote: The xmlrpc object to connect to.
    :param token: The token to authenticate against the remote object.
    """
    repo = remote.new_repo(token)
    remote.modify_repo(repo, "name", "testrepo0", token)
    remote.modify_repo(repo, "mirror", "http://www.sample.com/path/to/some/repo", token)
    remote.modify_repo(repo, "mirror_locally", False, token)
    remote.save_repo(repo, token)


@pytest.fixture
def remove_repo(remote: CobblerXMLRPCInterface, token: str):
    """
    Removes the Repository "testrepo0" which can be created with create_repo.

    :param remote: The xmlrpc object to connect to.
    :param token: The token to authenticate against the remote object.
    """
    yield
    remote.remove_repo("testrepo0", token)


class TestRepo:
    """
    TODO
    """

    @pytest.mark.usefixtures("remove_repo")
    def test_create_repo(self, remote: CobblerXMLRPCInterface, token: str):
        """
        Test: create/edit a repo object
        """

        # Arrange --> Nothing to arrange

        # Act & Assert
        repo = remote.new_repo(token)
        assert remote.modify_repo(repo, "name", "testrepo0", token)
        assert remote.modify_repo(
            repo, "mirror", "http://www.sample.com/path/to/some/repo", token
        )
        assert remote.modify_repo(repo, "mirror_locally", False, token)
        assert remote.save_repo(repo, token)

    def test_get_repos(self, remote: CobblerXMLRPCInterface):
        """
        Test: Get repos
        """

        # Arrange --> Nothing to do

        # Act
        result = remote.get_repos()

        # Assert
        assert result == []

    @pytest.mark.usefixtures("create_repo", "remove_repo")
    def test_get_repo(self, remote: CobblerXMLRPCInterface, token: str):
        """
        Test: Get a repo object
        """

        # Arrange --> Done in fixture

        # Act
        repo = remote.get_repo("testrepo0")

        # Assert
        assert repo.get("name") == "testrepo0"  # type: ignore

    @pytest.mark.usefixtures("create_repo", "remove_repo")
    def test_find_repo(self, remote: CobblerXMLRPCInterface, token: str):
        """
        Test: find a repo object
        """

        # Arrange --> Done in fixture

        # Act
        result = remote.find_repo({"name": "testrepo0"}, False, False, token)

        # Assert
        assert result

    @pytest.mark.usefixtures("create_repo", "remove_repo")
    def test_copy_repo(self, remote: CobblerXMLRPCInterface, token: str):
        """
        Test: copy a repo object
        """

        # Arrange --> Done in fixture

        # Act
        repo = remote.get_item_handle("repo", "testrepo0")

        # Assert
        assert remote.copy_repo(repo, "testrepocopy", token)

        # Cleanup
        remote.remove_repo("testrepocopy", token)

    @pytest.mark.usefixtures("create_repo")
    def test_rename_repo(self, remote: CobblerXMLRPCInterface, token: str):
        """
        Test: rename a repo object
        """

        # Arrange

        # Act
        repo = remote.get_item_handle("repo", "testrepo0")
        result = remote.rename_repo(repo, "testrepo1", token)

        # Assert
        assert result

        # Cleanup
        remote.remove_repo("testrepo1", token)

    @pytest.mark.usefixtures("create_repo")
    def test_remove_repo(self, remote: CobblerXMLRPCInterface, token: str):
        """
        Test: remove a repo object
        """

        # Arrange --> Done in fixture

        # Act
        result = remote.remove_repo("testrepo0", token)

        # Assert
        assert result
