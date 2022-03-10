import pytest


class TestMgmtClass:

    def test_create_mgmtclass(self, remote, token, remove_mgmt_class):
        """
        Test: create/edit a mgmtclass object
        """
        # Arrange
        name = "test_mgmt_class_create"

        # Act
        mgmtclass = remote.new_mgmtclass(token)
        result_modify = remote.modify_mgmtclass(mgmtclass, "name", name, token)
        result_save = remote.save_mgmtclass(mgmtclass, token)
        mgmtclass_count = remote.get_mgmtclasses(token)

        # Cleanup
        remove_mgmt_class(name)

        # Assert
        assert result_modify
        assert result_save
        assert len(mgmtclass_count) == 1

    def test_get_mgmtclasses(self, remote):
        """
        Test: Get mgmtclasses objects
        """
        # Arrange

        # Act
        result = remote.get_mgmtclasses()

        # Assert
        assert result == []

    def test_get_mgmtclass(self, remote, token, create_mgmt_class, remove_mgmt_class):
        """
        Test: get a mgmtclass object
        """
        # Arrange
        name = "test_mgmt_class_get"
        create_mgmt_class(name)

        # Act
        mgmtclass = remote.get_mgmtclass(name)

        # Cleanup
        remove_mgmt_class(name)

        # Assert
        assert mgmtclass

    def test_find_mgmtclass(self, remote, token, create_mgmt_class, remove_mgmt_class):
        """
        Test: find a mgmtclass object
        """
        # Arrange
        name = "test_mgmt_class_find"
        create_mgmt_class(name)

        # Act
        result = remote.find_mgmtclass({"name": name}, token)

        # Cleanup
        remove_mgmt_class(name)

        # Assert
        assert result

    def test_copy_mgmtclass(self, remote, token, create_mgmt_class, remove_mgmt_class):
        """
        Test: copy a mgmtclass object
        """
        # Arrange
        name = "testmgmtclass0"
        name_copy = "testmgmtclasscopy"
        mgmtclass = create_mgmt_class(name)

        # Act
        result = remote.copy_mgmtclass(mgmtclass, name_copy, token)

        # Cleanup
        remove_mgmt_class(name)
        remove_mgmt_class(name_copy)

        # Assert
        assert result

    def test_rename_mgmtclass(self, remote, token, create_mgmt_class, remove_mgmt_class):
        """
        Test: rename a mgmtclass object
        """
        # Arrange
        name = "test_mgmt_class_prerename"
        name_new = "test_mgmt_class_postrename"
        mgmtclass = create_mgmt_class(name)

        # Act
        result = remote.rename_mgmtclass(mgmtclass, name_new, token)

        # Cleanup
        remove_mgmt_class(name_new)

        # Assert
        assert result

    def test_remove_mgmtclass(self, remote, token, create_mgmt_class):
        """
        Test: remove a mgmtclass object
        """
        # Arrange
        name = "test_mgmt_class_remove"
        create_mgmt_class(name)

        # Act
        result = remote.remove_mgmtclass(name, token)

        # Assert
        assert result
