import pytest

# TODO: Create fixture where image is create


@pytest.fixture(scope="function")
def remove_item(remote, token):
    """
    Remove an item with the given name.

    :param token: The fixture to have the token for authenticated strings available.
    :param remote: The fixture to have the base xmlrpc connection.
    """
    def _remove_item(itemtype, name):
        yield
        remote.remove_item(itemtype, name, token)
    return _remove_item


class TestImage:

    def test_create_image(self, remote, token):
        """
        Test: create/edit of an image object"""

        # Arrange

        # Act
        images = remote.get_images(token)
        image = remote.new_image(token)

        # Assert
        assert remote.modify_image(image, "name", "testimage0", token)
        assert remote.save_image(image, token)
        new_images = remote.get_images(token)
        assert len(new_images) == len(images) + 1

    def test_get_images(self, remote):
        """
        Test: get images
        """

        # Arrange

        # Act
        remote.get_images()

        # Assert

    def test_get_image(self, remote):
        """
        Test: Get an image object
        """

        # Arrange

        # Act

        # Assert
        image = remote.get_image("testimage0")

    def test_find_image(self, remote, token):
        """
        Test: Find an image object
        """

        # Arrange

        # Act
        result = remote.find_image({"name": "testimage0"}, token)

        # Assert
        assert result

    def test_copy_image(self, remote, token):
        """
        Test: Copy an image object
        """

        # Arrange

        # Act
        image = remote.get_item_handle("image", "testimage0", token)

        # Assert
        assert remote.copy_image(image, "testimagecopy", token)

    def test_rename_image(self, remote, token, remove_item):
        """
        Test: Rename an image object
        """
        # Arrange
        name = "testimage1"
        image = remote.get_item_handle("image", "testimagecopy", token)

        # Act
        result = remote.rename_image(image, name, token)

        # Cleanup
        remote.remove_item("image", name, token)

        # Assert
        assert result

    def test_remove_image(self, remote, token):
        """
        Test: remove an image object
        """
        # Arrange

        # Act

        # Assert
        assert remote.remove_image("testimage0", token)
