import unittest
from .cobbler_xmlrpc_base_test import CobblerXmlRpcBaseTest


def tprint(call_name):
    """
    Print a remote call debug message

    @param call_name str remote call name
    """

    print("test remote call: %s()" % call_name)


class TestMgmtClass(CobblerXmlRpcBaseTest):

    def _create_mgmtclass(self):
        """
        Test: create/edit a mgmtclass object
        """

        mgmtclasses = self.remote.get_mgmtclasses(self.token)

        tprint("new_mgmtclass")
        mgmtclass = self.remote.new_mgmtclass(self.token)

        tprint("modify_mgmtclass")
        self.assertTrue(self.remote.modify_mgmtclass(mgmtclass, "name", "testmgmtclass0", self.token))

        tprint("save_mgmtclass")
        self.assertTrue(self.remote.save_mgmtclass(mgmtclass, self.token))

        new_mgmtclasses = self.remote.get_mgmtclasses(self.token)
        self.assertTrue(len(new_mgmtclasses) == len(mgmtclasses) + 1)

    def _get_mgmtclasses(self):
        """
        Test: Get mgmtclasses objects
        """

        tprint("get_mgmtclasses")
        self.remote.get_mgmtclasses()

    def _get_mgmtclass(self):
        """
        Test: get a mgmtclass object
        """

        tprint("get_mgmtclass")
        mgmtclass = self.remote.get_mgmtclass("testmgmtclass0")

    def _find_mgmtclass(self):
        """
        Test: find a mgmtclass object
        """

        tprint("find_mgmtclass")
        result = self.remote.find_mgmtclass({"name": "testmgmtclass0"}, self.token)
        self.assertTrue(result)

    def _copy_mgmtclass(self):
        """
        Test: copy a mgmtclass object
        """

        tprint("copy_mgmtclass")
        mgmtclass = self.remote.get_item_handle("mgmtclass", "testmgmtclass0", self.token)
        self.assertTrue(self.remote.copy_mgmtclass(mgmtclass, "testmgmtclasscopy", self.token))

    def _rename_mgmtclass(self):
        """
        Test: rename a mgmtclass object
        """

        tprint("rename_mgmtclass")
        mgmtclass = self.remote.get_item_handle("mgmtclass", "testmgmtclasscopy", self.token)
        self.assertTrue(self.remote.rename_mgmtclass(mgmtclass, "testmgmtclass1", self.token))

    def _remove_mgmtclass(self):
        """
        Test: remove a mgmtclass object
        """

        tprint("remove_mgmtclass")
        self.assertTrue(self.remote.remove_mgmtclass("testmgmtclass0", self.token))
        self.assertTrue(self.remote.remove_mgmtclass("testmgmtclass1", self.token))

    def test_mgmtclass(self):
        self._get_mgmtclasses()
        self._create_mgmtclass()
        self._get_mgmtclass()
        self._find_mgmtclass()
        self._copy_mgmtclass()
        self._rename_mgmtclass()
        self._remove_mgmtclass()

if __name__ == '__main__':
    unittest.main()
