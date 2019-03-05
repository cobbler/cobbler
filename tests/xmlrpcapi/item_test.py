import pytest


def tprint(call_name):
    """
    Print a remote call debug message

    @param call_name str remote call name
    """

    print("test remote call: %s()" % call_name)


@pytest.mark.usefixtures("cobbler_xmlrpc_base")
class TestItem:
    """
    Test item
    """

    def _get_item(self, type, remote):
        """
        Test: get a generic item

        @param type str item type
        """

        tprint("get_item")
        item = remote.get_item(type, "test%s2" % type)

    def _find_item(self, type, remote):
        """
        Test: find a generic item

        @param type str item type
        """

        tprint("find_items")
        result = remote.find_items(type, {"name": "test%s2" % type}, None, False)
        assert len(result) > 0

    def _copy_item(self, type, remote, token):
        """
        Test: copy a generic item

        @param type str item type
        """

        tprint("copy_item")
        item_id = remote.get_item_handle(type, "test%s2" % type, token)
        result = remote.copy_item(type, item_id, "test%scopy" % type, token)
        assert result

    def _has_item(self, type, remote, token):
        """
        Test: check if an item is in a item collection

        @param type str item type
        """

        tprint("has_item")
        result = remote.has_item(type, "test%s2" % type, token)
        assert result

    def _rename_item(self, type, remote, token):
        """
        Test: rename a generic item

        @param str type item type
        """

        tprint("rename_item")
        item_id = remote.get_item_handle(type, "test%scopy" % type, token)
        result = remote.rename_item(type, item_id, "test%s3" % type, token)
        assert result

    def _remove_item(self, type, remote, token):
        """
        Test: remove a generic item

        @param str type item type
        """

        tprint("remove_item")
        assert remote.remove_item(type, "test%s2" % type, token)
        assert remote.remove_item(type, "test%s3" % type, token)

    def test_item(self, remote, token):
        type = "mgmtclass"

        tprint("get_item_names")
        items_names = remote.get_item_names(type)

        # create an item of the type defined above
        item_id = remote.new_mgmtclass(token)

        remote.modify_item(type, item_id, "name", "test%s2" % type, token)
        result = remote.save_item(type, item_id, token)
        assert result

        new_items_names = remote.get_item_names(type)
        assert len(new_items_names) == len(items_names) + 1

        self._get_item(type, remote)
        self._find_item(type, remote)
        self._copy_item(type, remote, token)
        self._rename_item(type, remote, token)
        self._remove_item(type, remote, token)

        new_items_names = remote.get_item_names(type)
        assert len(new_items_names) == len(items_names)
