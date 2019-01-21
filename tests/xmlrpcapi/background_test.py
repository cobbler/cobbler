import unittest
from .cobbler_xmlrpc_base_test import CobblerXmlRpcBaseTest


class TestBackground(CobblerXmlRpcBaseTest):
    """
    Class to test various background jobs
    """

    def test_background_acletup(self):
        # TODO: test remote.background_aclsetup()
        raise NotImplementedError()

    def test_background_buildiso(self):
        # TODO: test remote.background_buildiso()
        raise NotImplementedError()

    def test_background_dlccontent(self):
        # TODO: test remote.background_dlcontent()
        raise NotImplementedError()

    def test_background_hardlink(self):
        # TODO: test remote.background_hardlink()
        raise NotImplementedError()

    def test_background_import(self):
        # TODO: test remote.background_import()
        raise NotImplementedError()

    def test_background_replicate(self):
        # TODO: test remote.background_replicate()
        raise NotImplementedError()

    def test_background_reposync(self):
        # TODO: test remote.background_reposync()
        raise NotImplementedError()

    def test_background_validate_autoinstall_files(self):
        # TODO: test remote.background_validate_autoinstall_files()
        raise NotImplementedError()


if __name__ == '__main__':
    unittest.main()
