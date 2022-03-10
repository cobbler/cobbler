import pytest


class TestFile:
    """
    Test remote calls related to files
    """

    def test_create_file(self, remote, token, remove_file):
        # Arrange

        # Act
        file_id = remote.new_file(token)
        filename = "testfile_create"

        remote.modify_file(file_id, "name", filename, token)
        remote.modify_file(file_id, "is_directory", False, token)
        remote.modify_file(file_id, "action", "create", token)
        remote.modify_file(file_id, "group", "root", token)
        remote.modify_file(file_id, "mode", "0644", token)
        remote.modify_file(file_id, "owner", "root", token)
        remote.modify_file(file_id, "path", "/root/testfile0", token)
        remote.modify_file(file_id, "template", "testtemplate0", token)

        result = remote.save_file(file_id, token)
        new_files = remote.get_files(token)

        # Cleanup
        remove_file(filename)

        # Assert
        assert result
        assert len(new_files) == 1

    def test_get_files(self, remote, token, create_file, remove_file):
        """
        Test: get files
        """
        # Arrange
        filename = "testfile_get_files"
        create_file(filename, False, "create", "root", "0644", "root", "/root/testfile0", "testtemplate0")

        # Act
        result = remote.get_files(token)

        # Cleanup
        remove_file(filename)

        # Assert
        assert type(result) == list
        assert len(result) == 1
        assert result[0].get("name") == filename

    def test_get_file(self, remote, token, create_file, remove_file):
        """
        Test: Get a file object
        """
        # Arrange
        filename = "testfile_get_file"
        create_file(filename, False, "create", "root", "0644", "root", "/root/testfile0", "testtemplate0")

        # Act
        file = remote.get_file("testfile0")

        # Cleanup
        remove_file(filename)

        # Assert
        assert file

    def test_find_file(self, remote, token, create_file, remove_file):
        """
        Test: find a file object
        """
        # Arrange
        filename = "testfile_find"
        create_file(filename, False, "create", "root", "0644", "root", "/root/testfile0", "testtemplate0")

        # Act
        result = remote.find_file({"name": filename}, token)

        # Cleanup
        remove_file(filename)

        # Assert
        assert result

    def test_copy_file(self, remote, token, create_file, remove_file):
        """
        Test: copy a file object
        """
        # Arrange
        filename_base = "testfile_copy_base"
        filename_copy = "testfile_copy_copied"
        create_file(filename_base, False, "create", "root", "0644", "root", "/root/testfile0", "testtemplate0")

        # Act
        file = remote.get_item_handle("file", filename_base, token)
        result = remote.copy_file(file, filename_copy, token)

        # Cleanup
        remove_file(filename_base)
        remove_file(filename_copy)

        # Assert
        assert result

    def test_rename_file(self, remote, token, create_file, remove_file):
        """
        Test: rename a file object
        """
        # Arrange
        filename = "testfile_renamed"
        filename_renamed = "testfile_renamed_successful"
        create_file(filename, False, "create", "root", "0644", "root", "/root/testfile0", "testtemplate0")
        file = remote.get_item_handle("file", filename, token)

        # Act
        result = remote.rename_file(file, filename_renamed, token)

        # Cleanup
        remove_file(filename_renamed)

        # Assert
        assert result

    def test_remove_file(self, remote, token, create_file):
        """
        Test: remove a file object
        """
        # Arrange
        filename = "testfile_remove"
        create_file(filename, False, "create", "root", "0644", "root", "/root/testfile0", "testtemplate0")

        # Act
        result = remote.remove_file(filename, token)

        # Assert
        assert result
