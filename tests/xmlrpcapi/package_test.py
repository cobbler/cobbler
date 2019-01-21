import unittest
from .cobbler_xmlrpc_base_test import CobblerXmlRpcBaseTest


"""
Order is important currently:
self._get_packages()
self._create_package()
self._get_package()
self._find_package()
self._copy_package()
self._rename_package()
self._remove_package()
"""


class TestPackage(CobblerXmlRpcBaseTest):

    def test_create_package(self):
        """
        Test: create/edit a package object
        """

        packages = self.remote.get_packages(self.token)
        package = self.remote.new_package(self.token)

        self.assertTrue(self.remote.modify_package(package, "name", "testpackage0", self.token))
        self.assertTrue(self.remote.save_package(package, self.token))

        new_packages = self.remote.get_packages(self.token)
        self.assertTrue(len(new_packages) == len(packages) + 1)

    def test_get_packages(self):
        """
        Test: Get packages
        """

        package = self.remote.get_packages()

    def test_get_package(self):
        """
        Test: Get a package object
        """

        package = self.remote.get_package("testpackage0")

    def test_find_package(self):
        """
        Test: find a package object
        """

        result = self.remote.find_package({"name": "testpackage0"}, self.token)
        self.assertTrue(result)

    def test_copy_package(self):
        """
        Test: copy a package object
        """

        package = self.remote.get_item_handle("package", "testpackage0", self.token)
        self.assertTrue(self.remote.copy_package(package, "testpackagecopy", self.token))

    def test_rename_package(self):
        """
        Test: rename a package object
        """

        package = self.remote.get_item_handle("package", "testpackagecopy", self.token)
        self.assertTrue(self.remote.rename_package(package, "testpackage1", self.token))

    def test_remove_package(self):
        """
        Test: remove a package object
        """

        self.assertTrue(self.remote.remove_package("testpackage0", self.token))
        self.assertTrue(self.remote.remove_package("testpackage1", self.token))


if __name__ == '__main__':
    unittest.main()
