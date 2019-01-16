import unittest
from .cobbler_xmlrpc_base_test import CobblerXmlRpcBaseTest


def tprint(call_name):
    """
    Print a remote call debug message

    @param call_name str remote call name
    """

    print("test remote call: %s()" % call_name)


class TestImage(CobblerXmlRpcBaseTest):

    def _create_image(self):
        """
        Test: create/edit of an image object"""

        images = self.remote.get_images(self.token)

        tprint("new_image")
        image = self.remote.new_image(self.token)

        tprint("modify_image")
        self.assertTrue(self.remote.modify_image(image, "name", "testimage0", self.token))

        tprint("save_image")
        self.assertTrue(self.remote.save_image(image, self.token))

        new_images = self.remote.get_images(self.token)
        self.assertTrue(len(new_images) == len(images) + 1)

    def _get_images(self):
        """
        Test: get images
        """
        tprint("get_images")
        self.remote.get_images()

    def _get_image(self):
        """
        Test: Get an image object
        """

        tprint("get_image")
        image = self.remote.get_image("testimage0")

    def _find_image(self):
        """
        Test: Find an image object
        """

        tprint("find_image")
        result = self.remote.find_image({"name": "testimage0"}, self.token)
        self.assertTrue(result)

    def _copy_image(self):
        """
        Test: Copy an image object
        """

        tprint("find_image")
        image = self.remote.get_item_handle("image", "testimage0", self.token)
        self.assertTrue(self.remote.copy_image(image, "testimagecopy", self.token))

    def _rename_image(self):
        """
        Test: Rename an image object
        """

        tprint("rename_image")
        image = self.remote.get_item_handle("image", "testimagecopy", self.token)
        self.assertTrue(self.remote.rename_image(image, "testimage1", self.token))

    def _remove_image(self):
        """
        Test: remove an image object
        """

        tprint("remove_image")
        self.assertTrue(self.remote.remove_image("testimage0", self.token))
        self.assertTrue(self.remote.remove_image("testimage1", self.token))

    def test_image(self):
        self._get_images()
        self._create_image()
        self._get_image()
        self._find_image()
        self._copy_image()
        self._rename_image()
        self._remove_image()

if __name__ == '__main__':
    unittest.main()
