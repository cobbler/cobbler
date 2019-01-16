import unittest
import pytest

from .cobbler_xmlrpc_base_test import CobblerXmlRpcBaseTest


"""
Order is currently important:
self._get_repos()
self._create_repo()
self._get_repo()
self._find_repo()
self._copy_repo()
self._rename_repo()
self._remove_repo()
"""


class TestRepo(CobblerXmlRpcBaseTest):

    @pytest.fixture
    def createRepo(self):
        repo = self.remote.new_repo(self.token)
        self.remote.modify_repo(repo, "name", "testrepo0", self.token)
        self.remote.modify_repo(repo, "mirror", "http://www.sample.com/path/to/some/repo", self.token)
        self.remote.modify_repo(repo, "mirror_locally", "0", self.token)
        self.remote.save_repo(repo, self.token)

    def test_create_repo(self):
        """
        Test: create/edit a repo object
        """

        # TODO: Arrange

        # Act
        repo = self.remote.new_repo(self.token)
        self.assertTrue(self.remote.modify_repo(repo, "name", "testrepo0", self.token))
        self.assertTrue(self.remote.modify_repo(repo, "mirror", "http://www.sample.com/path/to/some/repo", self.token))
        self.assertTrue(self.remote.modify_repo(repo, "mirror_locally", "0", self.token))
        self.assertTrue(self.remote.save_repo(repo, self.token))

        # TODO: Assert

    def test_get_repos(self):
        """
        Test: Get repos
        """

        # TODO: Arrange

        # Act
        self.remote.get_repos()

        # TODO: Assert

    def test_get_repo(self):
        """
        Test: Get a repo object
        """

        # TODO: Arrange --> Place file under "/var/lib/coobler/collections/repos/?"

        # Act
        repo = self.remote.get_repo("testrepo0")

        # TODO: Assert
        # TODO: Cleanup

    def test_find_repo(self, createRepo):
        """
        Test: find a repo object
        """

        # TODO: Arrange

        # Act
        result = self.remote.find_repo({"name": "testrepo0"}, self.token)

        # Assert
        self.assertTrue(result)
        # TODO: Cleanup

    def test_copy_repo(self, createRepo):
        """
        Test: copy a repo object
        """

        # TODO: Arrange

        # Act
        repo = self.remote.get_item_handle("repo", "testrepo0", self.token)

        # Assert
        self.assertTrue(self.remote.copy_repo(repo, "testrepocopy", self.token))
        # TODO: Cleanup

    def test_rename_repo(self, createRepo):
        """
        Test: rename a repo object
        """

        # TODO: Arrange

        # Act
        repo = self.remote.get_item_handle("repo", "testrepo0", self.token)

        # Assert
        self.assertTrue(self.remote.rename_repo(repo, "testrepo1", self.token))
        # TODO: Cleanup

    def test_remove_repo(self, createRepo):
        """
        Test: remove a repo object
        """

        # TODO: Arrange

        # Act
        result = self.remote.remove_repo("testrepo0", self.token)

        # TODO: Assert
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
