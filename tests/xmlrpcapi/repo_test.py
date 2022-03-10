import pytest


@pytest.fixture
def create_repo(remote, token):
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
def remove_repo(remote, token):
    """
    Removes the Repository "testrepo0" which can be created with create_repo.

    :param remote: The xmlrpc object to connect to.
    :param token: The token to authenticate against the remote object.
    """
    yield
    remote.remove_repo("testrepo0", token)


class TestRepo:
    @pytest.mark.usefixtures("remove_repo")
    def test_create_repo(self, remote, token):
        """
        Test: create/edit a repo object
        """

        # Arrange --> Nothing to arrange

        # Act & Assert
        repo = remote.new_repo(token)
        assert remote.modify_repo(repo, "name", "testrepo0", token)
        assert remote.modify_repo(repo, "mirror", "http://www.sample.com/path/to/some/repo", token)
        assert remote.modify_repo(repo, "mirror_locally", False, token)
        assert remote.save_repo(repo, token)

    def test_get_repos(self, remote):
        """
        Test: Get repos
        """

        # Arrange --> Nothing to do

        # Act
        result = remote.get_repos()

        # Assert
        assert result == []

    @pytest.mark.usefixtures("create_repo", "remove_repo")
    def test_get_repo(self, remote, token):
        """
        Test: Get a repo object
        """

        # Arrange --> Done in fixture

        # Act
        repo = remote.get_repo("testrepo0")

        # Assert
        assert repo.get("name") == "testrepo0"

    @pytest.mark.usefixtures("create_repo", "remove_repo")
    def test_find_repo(self, remote, token):
        """
        Test: find a repo object
        """

        # Arrange --> Done in fixture

        # Act
        result = remote.find_repo({"name": "testrepo0"}, token)

        # Assert
        assert result

    @pytest.mark.usefixtures("create_repo", "remove_repo")
    def test_copy_repo(self, remote, token):
        """
        Test: copy a repo object
        """

        # Arrange --> Done in fixture

        # Act
        repo = remote.get_item_handle("repo", "testrepo0", token)

        # Assert
        assert remote.copy_repo(repo, "testrepocopy", token)

        # Cleanup
        remote.remove_repo("testrepocopy", token)

    @pytest.mark.usefixtures("create_repo")
    def test_rename_repo(self, remote, token):
        """
        Test: rename a repo object
        """

        # Arrange

        # Act
        repo = remote.get_item_handle("repo", "testrepo0", token)
        result = remote.rename_repo(repo, "testrepo1", token)

        # Assert
        assert result

        # Cleanup
        remote.remove_repo("testrepo1", token)

    @pytest.mark.usefixtures("create_repo")
    def test_remove_repo(self, remote, token):
        """
        Test: remove a repo object
        """

        # Arrange --> Done in fixture

        # Act
        result = remote.remove_repo("testrepo0", token)

        # Assert
        assert result
