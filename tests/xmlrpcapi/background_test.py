import pytest


@pytest.mark.usefixtures("cobbler_xmlrpc_base")
class TestBackground:
    """
    Class to test various background jobs
    """

    @pytest.mark.skip(reason="Not Implemented!")
    def test_background_acletup(self):
        # TODO: test remote.background_aclsetup()
        raise NotImplementedError()

    @pytest.mark.skip(reason="Not Implemented!")
    def test_background_buildiso(self):
        # TODO: test remote.background_buildiso()
        raise NotImplementedError()

    @pytest.mark.skip(reason="Not Implemented!")
    def test_background_dlccontent(self):
        # TODO: test remote.background_dlcontent()
        raise NotImplementedError()

    @pytest.mark.skip(reason="Not Implemented!")
    def test_background_hardlink(self):
        # TODO: test remote.background_hardlink()
        raise NotImplementedError()

    @pytest.mark.skip(reason="Not Implemented!")
    def test_background_import(self):
        # TODO: test remote.background_import()
        raise NotImplementedError()

    @pytest.mark.skip(reason="Not Implemented!")
    def test_background_replicate(self):
        # TODO: test remote.background_replicate()
        raise NotImplementedError()

    @pytest.mark.skip(reason="Not Implemented!")
    def test_background_reposync(self):
        # TODO: test remote.background_reposync()
        raise NotImplementedError()

    @pytest.mark.skip(reason="Not Implemented!")
    def test_background_validate_autoinstall_files(self):
        # TODO: test remote.background_validate_autoinstall_files()
        raise NotImplementedError()
