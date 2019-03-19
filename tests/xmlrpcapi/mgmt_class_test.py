import pytest


def tprint(call_name):
    """
    Print a remote call debug message

    @param call_name str remote call name
    """

    print("test remote call: %s()" % call_name)


@pytest.mark.usefixtures("cobbler_xmlrpc_base")
class TestMgmtClass:

    def _create_mgmtclass(self, remote, token):
        """
        Test: create/edit a mgmtclass object
        """

        mgmtclasses = remote.get_mgmtclasses(token)

        tprint("new_mgmtclass")
        mgmtclass = remote.new_mgmtclass(token)

        tprint("modify_mgmtclass")
        assert remote.modify_mgmtclass(mgmtclass, "name", "testmgmtclass0", token)

        tprint("save_mgmtclass")
        assert remote.save_mgmtclass(mgmtclass, token)

        new_mgmtclasses = remote.get_mgmtclasses(token)
        assert len(new_mgmtclasses) == len(mgmtclasses) + 1

    def _get_mgmtclasses(self, remote):
        """
        Test: Get mgmtclasses objects
        """

        tprint("get_mgmtclasses")
        remote.get_mgmtclasses()

    def _get_mgmtclass(self, remote):
        """
        Test: get a mgmtclass object
        """

        tprint("get_mgmtclass")
        mgmtclass = remote.get_mgmtclass("testmgmtclass0")

    def _find_mgmtclass(self, remote, token):
        """
        Test: find a mgmtclass object
        """

        tprint("find_mgmtclass")
        result = remote.find_mgmtclass({"name": "testmgmtclass0"}, token)
        assert result

    def _copy_mgmtclass(self, remote, token):
        """
        Test: copy a mgmtclass object
        """

        tprint("copy_mgmtclass")
        mgmtclass = remote.get_item_handle("mgmtclass", "testmgmtclass0", token)
        assert remote.copy_mgmtclass(mgmtclass, "testmgmtclasscopy", token)

    def _rename_mgmtclass(self, remote, token):
        """
        Test: rename a mgmtclass object
        """

        tprint("rename_mgmtclass")
        mgmtclass = remote.get_item_handle("mgmtclass", "testmgmtclasscopy", token)
        assert remote.rename_mgmtclass(mgmtclass, "testmgmtclass1", token)

    def _remove_mgmtclass(self, remote, token):
        """
        Test: remove a mgmtclass object
        """

        tprint("remove_mgmtclass")
        assert remote.remove_mgmtclass("testmgmtclass0", token)
        assert remote.remove_mgmtclass("testmgmtclass1", token)

    def test_mgmtclass(self, remote, token):
        self._get_mgmtclasses(remote)
        self._create_mgmtclass(remote, token)
        self._get_mgmtclass(remote)
        self._find_mgmtclass(remote, token)
        self._copy_mgmtclass(remote, token)
        self._rename_mgmtclass(remote, token)
        self._remove_mgmtclass(remote, token)
