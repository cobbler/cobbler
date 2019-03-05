import pytest


def tprint(call_name):
    """
    Print a remote call debug message

    @param call_name str remote call name
    """

    print("test remote call: %s()" % call_name)


@pytest.mark.usefixtures("cobbler_xmlrpc_base")
class TestImage:

    def _create_image(self, remote, token):
        """
        Test: create/edit of an image object"""

        images = remote.get_images(token)

        tprint("new_image")
        image = remote.new_image(token)

        tprint("modify_image")
        assert remote.modify_image(image, "name", "testimage0", token)

        tprint("save_image")
        assert remote.save_image(image, token)

        new_images = remote.get_images(token)
        assert len(new_images) == len(images) + 1

    def _get_images(self, remote):
        """
        Test: get images
        """
        tprint("get_images")
        remote.get_images()

    def _get_image(self, remote):
        """
        Test: Get an image object
        """

        tprint("get_image")
        image = remote.get_image("testimage0")

    def _find_image(self, remote, token):
        """
        Test: Find an image object
        """

        tprint("find_image")
        result = remote.find_image({"name": "testimage0"}, token)
        assert result

    def _copy_image(self, remote, token):
        """
        Test: Copy an image object
        """

        tprint("find_image")
        image = remote.get_item_handle("image", "testimage0", token)
        assert remote.copy_image(image, "testimagecopy", token)

    def _rename_image(self, remote, token):
        """
        Test: Rename an image object
        """

        tprint("rename_image")
        image = remote.get_item_handle("image", "testimagecopy", token)
        assert remote.rename_image(image, "testimage1", token)

    def _remove_image(self, remote, token):
        """
        Test: remove an image object
        """

        tprint("remove_image")
        assert remote.remove_image("testimage0", token)
        assert remote.remove_image("testimage1", token)

    def test_image(self, remote, token):
        self._get_images(remote)
        self._create_image(remote, token)
        self._get_image(remote)
        self._find_image(remote, token)
        self._copy_image(remote, token)
        self._rename_image(remote, token)
        self._remove_image(remote, token)
