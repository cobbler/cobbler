class TestImage:

    def test_create_image(self, remote, token):
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

    def test_get_images(self, remote):
        """
        Test: get images
        """
        # Arrange

        # Act
        remote.get_images()

        # Assert

    def test_get_image(self, remote, create_image):
        """
        Test: Get an image object
        """
        # Arrange
        test_image = create_image()

        # Act
        result_image = remote.get_image(test_image.name)

        # Assert
        assert result_image.get("name") == test_image.name

    def test_find_image(self, remote, token, create_image):
        """
        Test: Find an image object
        """
        # Arrange
        test_image = create_image()

        # Act
        result = remote.find_image({"name": test_image.name}, token)

        # Assert - We want to find exactly the one item we added
        assert len(result) == 1
        assert result[0].get("name") == test_image.name

    def test_copy_image(self, remote, token, create_image):
        """
        Test: Copy an image object
        """
        # Arrange
        test_image = create_image()
        new_name = "testimagecopy"
        image = remote.get_item_handle("image", test_image.name, token)

        # Act
        result = remote.copy_image(image, new_name, token)

        # Assert
        assert result

    def test_rename_image(self, remote, token, create_image):
        """
        Test: Rename an image object
        """
        # Arrange
        test_image = create_image()
        new_name = "testimage_renamed"
        image = remote.get_item_handle("image", test_image.name, token)

        # Act
        result = remote.rename_image(image, new_name, token)

        # Assert
        assert result

    def test_remove_image(self, remote, token, create_image):
        """
        Test: remove an image object
        """
        # Arrange
        test_image = create_image()

        # Act
        result = remote.remove_image(test_image.name, token)

        # Assert
        assert result
