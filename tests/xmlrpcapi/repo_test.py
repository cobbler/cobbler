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

        repos = self.remote.get_repos(self.token)

        repo = self.remote.new_repo(self.token)

        self.assertTrue(self.remote.modify_repo(repo, "name", "testrepo0", self.token))
        self.assertTrue(self.remote.modify_repo(repo, "mirror", "http://www.sample.com/path/to/some/repo", self.token))
        self.assertTrue(self.remote.modify_repo(repo, "mirror_locally", "0", self.token))

        self.assertTrue(self.remote.save_repo(repo, self.token))

        new_repos = self.remote.get_repos(self.token)
        self.assertTrue(len(new_repos) == len(repos) + 1)

    def test_get_repos(self):
        """
        Test: Get repos
        """

        self.remote.get_repos()

    def test_get_repo(self):
        """
        Test: Get a repo object
        """

        repo = self.remote.get_repo("testrepo0")

    def test_find_repo(self):
        """
        Test: find a repo object
        """

        result = self.remote.find_repo({"name": "testrepo0"}, self.token)
        self.assertTrue(result)

    def test_copy_repo(self):
        """
        Test: copy a repo object
        """

        repo = self.remote.get_item_handle("repo", "testrepo0", self.token)
        self.assertTrue(self.remote.copy_repo(repo, "testrepocopy", self.token))

    def test_rename_repo(self):
        """
        Test: rename a repo object
        """

        repo = self.remote.get_item_handle("repo", "testrepocopy", self.token)
        self.assertTrue(self.remote.rename_repo(repo, "testrepo1", self.token))

    def test_remove_repo(self):
        """
        Test: remove a repo object
        """

        self.assertTrue(self.remote.remove_repo("testrepo0", self.token))
        self.assertTrue(self.remote.remove_repo("testrepo1", self.token))


if __name__ == '__main__':
    unittest.main()
