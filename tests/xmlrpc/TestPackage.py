from xmlrpc.CobblerXmlRpcBaseTest import CobblerXmlRpcBaseTest


def tprint(call_name):
    """
    Print a remote call debug message

    @param call_name str remote call name
    """

    print("test remote call: %s()" % call_name)


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

        tprint("get_packages")
        packages = self.remote.get_packages(self.token)

        tprint("new_package")
        package = self.remote.new_package(self.token)

        tprint("modify_package")
        self.assertTrue(self.remote.modify_package(package, "name", "testpackage0", self.token))

        tprint("save_package")
        self.assertTrue(self.remote.save_package(package, self.token))

        new_packages = self.remote.get_packages(self.token)
        self.assertTrue(len(new_packages) == len(packages) + 1)

    def test_get_packages(self):
        """
        Test: Get packages
        """
        tprint("get_package")
        package = self.remote.get_packages()

    def test_get_package(self):
        """
        Test: Get a package object
        """

        tprint("get_package")
        package = self.remote.get_package("testpackage0")

    def test_find_package(self):
        """
        Test: find a package object
        """

        tprint("find_package")
        result = self.remote.find_package({"name": "testpackage0"}, self.token)
        self.assertTrue(result)

    def test_copy_package(self):
        """
        Test: copy a package object
        """

        tprint("copy_package")
        package = self.remote.get_item_handle("package", "testpackage0", self.token)
        self.assertTrue(self.remote.copy_package(package, "testpackagecopy", self.token))

    def test_rename_package(self):
        """
        Test: rename a package object
        """

        tprint("rename_package")
        package = self.remote.get_item_handle("package", "testpackagecopy", self.token)
        self.assertTrue(self.remote.rename_package(package, "testpackage1", self.token))

    def test_remove_package(self):
        """
        Test: remove a package object
        """

        tprint("remove_package")
        self.assertTrue(self.remote.remove_package("testpackage0", self.token))
        self.assertTrue(self.remote.remove_package("testpackage1", self.token))
