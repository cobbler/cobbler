from xmlrpc.CobblerXmlRpcBaseTest import CobblerXmlRpcBaseTest


def tprint(call_name):
    """
    Print a remote call debug message

    @param call_name str remote call name
    """

    print("test remote call: %s()" % call_name)


class TestFile(CobblerXmlRpcBaseTest):
    """
    Test remote calls related to files
    """

    def _create_file(self):
        files = self.remote.get_files(self.token)

        tprint("new_file")
        file_id = self.remote.new_file(self.token)

        tprint("modify_file")
        self.remote.modify_file(file_id, "name", "testfile0", self.token)
        self.remote.modify_file(file_id, "is_directory", "False", self.token)
        self.remote.modify_file(file_id, "action", "create", self.token)
        self.remote.modify_file(file_id, "group", "root", self.token)
        self.remote.modify_file(file_id, "mode", "0644", self.token)
        self.remote.modify_file(file_id, "owner", "root", self.token)
        self.remote.modify_file(file_id, "path", "/root/testfile0", self.token)
        self.remote.modify_file(file_id, "template", "testtemplate0", self.token)

        tprint("save_file")
        self.remote.save_file(file_id, self.token)

        new_files = self.remote.get_files(self.token)
        self.assertTrue(len(new_files) == len(files) + 1)

    def _get_files(self):
        """
        Test: get files
        """

        tprint("get_files")
        self.remote.get_files(self.token)

    def _get_file(self):
        """
        Test: Get a file object
        """

        tprint("get_file")
        file = self.remote.get_file("testfile0")

    def _find_file(self):
        """
        Test: find a file object
        """

        tprint("find_file")
        result = self.remote.find_file({"name": "testfile0"}, self.token)
        self.assertTrue(result)

    def _copy_file(self):
        """
        Test: copy a file object
        """

        tprint("copy_file")
        file = self.remote.get_item_handle("file", "testfile0", self.token)
        self.assertTrue(self.remote.copy_file(file, "testfilecopy", self.token))

    def _rename_file(self):
        """
        Test: rename a file object
        """

        tprint("rename_file")
        file = self.remote.get_item_handle("file", "testfilecopy", self.token)
        self.assertTrue(self.remote.rename_file(file, "testfile1", self.token))

    def _remove_file(self):
        """
        Test: remove a file object
        """

        tprint("remove_file")
        self.assertTrue(self.remote.remove_file("testfile0", self.token))
        self.assertTrue(self.remote.remove_file("testfile1", self.token))

    def test_file(self):
        self._get_files()
        self._create_file()
        self._get_file()
        self._find_file()
        self._copy_file()
        self._rename_file()
        self._remove_file()