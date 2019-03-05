import pytest


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


@pytest.mark.usefixtures("cobbler_xmlrpc_base")
class TestFile:
    """
    Test remote calls related to files
    """

    def test_create_file(self, remote, token):
        files = remote.get_files(token)

        file_id = remote.new_file(token)

        remote.modify_file(file_id, "name", "testfile0", token)
        remote.modify_file(file_id, "is_directory", "False", token)
        remote.modify_file(file_id, "action", "create", token)
        remote.modify_file(file_id, "group", "root", token)
        remote.modify_file(file_id, "mode", "0644", token)
        remote.modify_file(file_id, "owner", "root", token)
        remote.modify_file(file_id, "path", "/root/testfile0", token)
        remote.modify_file(file_id, "template", "testtemplate0", token)

        remote.save_file(file_id, token)

        new_files = remote.get_files(token)
        assert len(new_files) == len(files) + 1

    def test_get_files(self, remote, token):
        """
        Test: get files
        """

        remote.get_files(token)

    def test_get_file(self, remote):
        """
        Test: Get a file object
        """

        file = remote.get_file("testfile0")

    def test_find_file(self, remote, token):
        """
        Test: find a file object
        """

        result = remote.find_file({"name": "testfile0"}, token)
        assert result

    def test_copy_file(self, remote, token):
        """
        Test: copy a file object
        """

        file = remote.get_item_handle("file", "testfile0", token)
        assert remote.copy_file(file, "testfilecopy", token)

    def test_rename_file(self, remote, token):
        """
        Test: rename a file object
        """

        file = remote.get_item_handle("file", "testfilecopy", token)
        assert remote.rename_file(file, "testfile1", token)

    def test_remove_file(self, remote, token):
        """
        Test: remove a file object
        """

        assert remote.remove_file("testfile0", token)
        assert remote.remove_file("testfile1", token)
