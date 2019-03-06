import pytest


@pytest.fixture
def create_repo(remote, token):
    """
    Creates a Repository "testrepo0" with a mirror "http://www.sample.com/path/to/some/repo" and the attribute
    "mirror_locally=0".
    """
    repo = remote.new_repo(token)
    remote.modify_repo(repo, "name", "testrepo0", token)
    remote.modify_repo(repo, "mirror", "http://www.sample.com/path/to/some/repo", token)
    remote.modify_repo(repo, "mirror_locally", "0", token)
    remote.save_repo(repo, token)


@pytest.mark.usefixtures("cobbler_xmlrpc_base")
class TestRepo:
    def test_create_repo(self, remote, token):
        """
        Test: create/edit a repo object
        """

        # TODO: Arrange

        # Act
        repo = remote.new_repo(token)
        assert remote.modify_repo(repo, "name", "testrepo0", token)
        assert remote.modify_repo(repo, "mirror", "http://www.sample.com/path/to/some/repo", token)
        assert remote.modify_repo(repo, "mirror_locally", "0", token)
        assert remote.save_repo(repo, token)

        # TODO: Assert

    def test_get_repos(self, remote):
        """
        Test: Get repos
        """

        # TODO: Arrange

        # Act
        remote.get_repos()

        # TODO: Assert

    def test_get_repo(self, remote):
        """
        Test: Get a repo object
        """

        # TODO: Arrange --> Place file under "/var/lib/coobler/collections/repos/?"

        # Act
        repo = remote.get_repo("testrepo0")

        # TODO: Assert
        # TODO: Cleanup

    @pytest.mark.usefixtures("create_repo")
    def test_find_repo(self, remote, token):
        """
        Test: find a repo object
        """

        # TODO: Arrange

        # Act
        result = remote.find_repo({"name": "testrepo0"}, token)

        # Assert
        assert result
        # TODO: Cleanup

    @pytest.mark.usefixtures("create_repo")
    def test_copy_repo(self, remote, token):
        """
        Test: copy a repo object
        """

        # TODO: Arrange

        # Act
        repo = remote.get_item_handle("repo", "testrepo0", token)

        # Assert
        assert remote.copy_repo(repo, "testrepocopy", token)
        # TODO: Cleanup

    @pytest.mark.usefixtures("create_repo")
    def test_rename_repo(self, remote, token):
        """
        Test: rename a repo object
        """

        # TODO: Arrange

        # Act
        repo = remote.get_item_handle("repo", "testrepo0", token)

        # Assert
        assert remote.rename_repo(repo, "testrepo1", token)
        # TODO: Cleanup

    @pytest.mark.usefixtures("create_repo")
    def test_remove_repo(self, remote, token):
        """
        Test: remove a repo object
        """

        # TODO: Arrange

        # Act
        result = remote.remove_repo("testrepo0", token)

        # TODO: Assert
        assert result
