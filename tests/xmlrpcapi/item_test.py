import unittest
from .cobbler_xmlrpc_base_test import CobblerXmlRpcBaseTest


def tprint(call_name):
    """
    Print a remote call debug message

    @param call_name str remote call name
    """

    print("test remote call: %s()" % call_name)


class TestItem(CobblerXmlRpcBaseTest):
    """
    Test item
    """

    def _get_item(self, type):
        """
        Test: get a generic item

        @param type str item type
        """

        tprint("get_item")
        item = self.remote.get_item(type, "test%s2" % type)

    def _find_item(self, type):
        """
        Test: find a generic item

        @param type str item type
        """

        tprint("find_items")
        result = self.remote.find_items(type, {"name": "test%s2" % type}, None, False)
        self.assertTrue(len(result) > 0)

    def _copy_item(self, type):
        """
        Test: copy a generic item

        @param type str item type
        """

        tprint("copy_item")
        item_id = self.remote.get_item_handle(type, "test%s2" % type, self.token)
        result = self.remote.copy_item(type, item_id, "test%scopy" % type, self.token)
        self.assertTrue(result)

    def _has_item(self, type):
        """
        Test: check if an item is in a item collection

        @param type str item type
        """

        tprint("has_item")
        result = self.remote.has_item(type, "test%s2" % type, self.token)
        self.assertTrue(result)

    def _rename_item(self, type):
        """
        Test: rename a generic item

        @param str type item type
        """

        tprint("rename_item")
        item_id = self.remote.get_item_handle(type, "test%scopy" % type, self.token)
        result = self.remote.rename_item(type, item_id, "test%s3" % type, self.token)
        self.assertTrue(result)

    def _remove_item(self, type):
        """
        Test: remove a generic item

        @param str type item type
        """

        tprint("remove_item")
        self.assertTrue(self.remote.remove_item(type, "test%s2" % type, self.token))
        self.assertTrue(self.remote.remove_item(type, "test%s3" % type, self.token))

    def test_item(self):
        type = "mgmtclass"

        tprint("get_item_names")
        items_names = self.remote.get_item_names(type)

        # create an item of the type defined above
        item_id = self.remote.new_mgmtclass(self.token)

        self.remote.modify_item(type, item_id, "name", "test%s2" % type, self.token)
        result = self.remote.save_item(type, item_id, self.token)
        self.assertTrue(result)

        new_items_names = self.remote.get_item_names(type)
        self.assertTrue(len(new_items_names) == len(items_names) + 1)

        self._get_item(type)
        self._find_item(type)
        self._copy_item(type)
        self._rename_item(type)
        self._remove_item(type)

        new_items_names = self.remote.get_item_names(type)
        self.assertTrue(len(new_items_names) == len(items_names))

if __name__ == '__main__':
    unittest.main()
