"""
Tests that validate the functionality of the module that is responsible for providing XML-RPC calls related to images.
"""

from typing import Callable

from cobbler.items.image import Image
from cobbler.remote import CobblerXMLRPCInterface


class TestImage:
    """
    TODO
    """

    def test_create_image(self, remote: CobblerXMLRPCInterface, token: str):
        """
        Test: create/edit of an image object
        """
        # Act
        image = remote.new_image(token)

        # Assert
        assert remote.modify_image(image, "name", "testimage0", token)
        assert remote.save_image(image, token)
        image_list = remote.get_images(token)
        assert len(image_list) == 1

    def test_get_images(self, remote: CobblerXMLRPCInterface):
        """
        Test: get images
        """
        # Arrange

        # Act
        remote.get_images()

        # Assert

    def test_get_image(
        self, remote: CobblerXMLRPCInterface, create_image: Callable[[], Image]
    ):
        """
        Test: Get an image object
        """
        # Arrange
        test_image = create_image()

        # Act
        result_image = remote.get_image(test_image.name)

        # Assert
        assert result_image.get("name") == test_image.name  # type: ignore[reportUnknownMemberType]

    def test_find_image(
        self,
        remote: CobblerXMLRPCInterface,
        token: str,
        create_image: Callable[[], Image],
    ):
        """
        Test: Find an image object
        """
        # Arrange
        test_image = create_image()

        # Act
        result = remote.find_image({"name": test_image.name}, True, False, token)
        print(result)

        # Assert - We want to find exactly the one item we added
        assert len(result) == 1
        assert result[0].get("name") == test_image.name

    def test_copy_image(
        self,
        remote: CobblerXMLRPCInterface,
        token: str,
        create_image: Callable[[], Image],
    ):
        """
        Test: Copy an image object
        """
        # Arrange
        test_image = create_image()
        new_name = "testimagecopy"

        # Act
        result = remote.copy_image(test_image.uid, new_name, token)

        # Assert
        assert result

    def test_rename_image(
        self,
        remote: CobblerXMLRPCInterface,
        token: str,
        create_image: Callable[[], Image],
    ):
        """
        Test: Rename an image object
        """
        # Arrange
        test_image = create_image()
        new_name = "testimage_renamed"

        # Act
        result = remote.rename_image(test_image.uid, new_name, token)

        # Assert
        assert result

    def test_remove_image(
        self,
        remote: CobblerXMLRPCInterface,
        token: str,
        create_image: Callable[[], Image],
    ):
        """
        Test: remove an image object
        """
        # Arrange
        test_image = create_image()

        # Act
        result = remote.remove_image(test_image.name, token)

        # Assert
        assert result
