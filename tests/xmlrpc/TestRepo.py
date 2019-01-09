from xmlrpc.CobblerXmlRpcBaseTest import CobblerXmlRpcBaseTest


def tprint(call_name):
    """
    Print a remote call debug message

    @param call_name str remote call name
    """

    print("test remote call: %s()" % call_name)


class TestRepo(CobblerXmlRpcBaseTest):

    def _create_repo(self):
        """
        Test: create/edit a repo object
        """

        repos = self.remote.get_repos(self.token)

        tprint("new_repo")
        repo = self.remote.new_repo(self.token)

        tprint("modify_repo")
        self.assertTrue(self.remote.modify_repo(repo, "name", "testrepo0", self.token))
        self.assertTrue(self.remote.modify_repo(repo, "mirror", "http://www.sample.com/path/to/some/repo", self.token))
        self.assertTrue(self.remote.modify_repo(repo, "mirror_locally", "0", self.token))

        tprint("save_repo")
        self.assertTrue(self.remote.save_repo(repo, self.token))

        new_repos = self.remote.get_repos(self.token)
        self.assertTrue(len(new_repos) == len(repos) + 1)

    def _get_repos(self):
        """
        Test: Get repos
        """

        tprint("get_repos")
        self.remote.get_repos()

    def _get_repo(self):
        """
        Test: Get a repo object
        """

        tprint("get_repo")
        repo = self.remote.get_repo("testrepo0")

    def _find_repo(self):
        """
        Test: find a repo object
        """

        tprint("find_repo")
        result = self.remote.find_repo({"name": "testrepo0"}, self.token)
        self.assertTrue(result)

    def _copy_repo(self):
        """
        Test: copy a repo object
        """

        tprint("copy_repo")
        repo = self.remote.get_item_handle("repo", "testrepo0", self.token)
        self.assertTrue(self.remote.copy_repo(repo, "testrepocopy", self.token))

    def _rename_repo(self):
        """
        Test: rename a repo object
        """

        tprint("rename_repo")
        repo = self.remote.get_item_handle("repo", "testrepocopy", self.token)
        self.assertTrue(self.remote.rename_repo(repo, "testrepo1", self.token))

    def _remove_repo(self):
        """
        Test: remove a repo object
        """

        tprint("remove_repo")
        self.assertTrue(self.remote.remove_repo("testrepo0", self.token))
        self.assertTrue(self.remote.remove_repo("testrepo1", self.token))

    def test_repo(self):
        self._get_repos()
        self._create_repo()
        self._get_repo()
        self._find_repo()
        self._copy_repo()
        self._rename_repo()
        self._remove_repo()