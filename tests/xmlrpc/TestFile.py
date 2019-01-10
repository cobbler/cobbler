from xmlrpc.CobblerXmlRpcBaseTest import CobblerXmlRpcBaseTest


def tprint(call_name):
    """
    Print a remote call debug message

    @param call_name str remote call name
    """

    print("test remote call: %s()" % call_name)


"""
Order is currently important:
test_get_files()
test_create_file()
test_get_file()
test_find_file()
test_copy_file()
test_rename_file()
test_remove_file()
"""


class TestFile(CobblerXmlRpcBaseTest):
    """
    Test remote calls related to files
    """

    def test_create_file(self):
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

    def test_get_files(self):
        """
        Test: get files
        """

        tprint("get_files")
        self.remote.get_files(self.token)

    def test_get_file(self):
        """
        Test: Get a file object
        """

        tprint("get_file")
        file = self.remote.get_file("testfile0")

    def test_find_file(self):
        """
        Test: find a file object
        """

        tprint("find_file")
        result = self.remote.find_file({"name": "testfile0"}, self.token)
        self.assertTrue(result)

    def test_copy_file(self):
        """
        Test: copy a file object
        """

        tprint("copy_file")
        file = self.remote.get_item_handle("file", "testfile0", self.token)
        self.assertTrue(self.remote.copy_file(file, "testfilecopy", self.token))

    def test_rename_file(self):
        """
        Test: rename a file object
        """

        tprint("rename_file")
        file = self.remote.get_item_handle("file", "testfilecopy", self.token)
        self.assertTrue(self.remote.rename_file(file, "testfile1", self.token))

    def test_remove_file(self):
        """
        Test: remove a file object
        """

        tprint("remove_file")
        self.assertTrue(self.remote.remove_file("testfile0", self.token))
        self.assertTrue(self.remote.remove_file("testfile1", self.token))