"""
Tests that validate the functionality of the module that is responsible for providing XML-RPC calls related to
background tasks.
"""

from cobbler.remote import CobblerXMLRPCInterface


class TestBackground:
    """
    Class to test various background jobs
    """

    def test_background_acletup(self, remote: CobblerXMLRPCInterface, token: str):
        # Arrange

        # Act
        result = remote.background_aclsetup({}, token)

        # Assert
        assert result

    def test_background_buildiso(self, remote: CobblerXMLRPCInterface, token: str):
        # Arrange

        # Act
        result = remote.background_buildiso({}, token)

        # Assert
        assert result

    def test_background_hardlink(self, remote: CobblerXMLRPCInterface, token: str):
        # Arrange

        # Act
        result = remote.background_hardlink({}, token)

        # Assert
        assert result

    def test_background_import(self, remote: CobblerXMLRPCInterface, token: str):
        # Arrange

        # Act
        result = remote.background_import({}, token)

        # Assert
        assert result

    def test_background_replicate(self, remote: CobblerXMLRPCInterface, token: str):
        # Arrange

        # Act
        result = remote.background_replicate({}, token)

        # Assert
        assert result

    def test_background_reposync(self, remote: CobblerXMLRPCInterface, token: str):
        # Arrange

        # Act
        result = remote.background_reposync({}, token)

        # Assert
        assert result

    def test_background_validate_autoinstall_files(
        self, remote: CobblerXMLRPCInterface, token: str
    ):
        # Arrange

        # Act
        result = remote.background_validate_autoinstall_files({}, token)

        # Assert
        assert result

    def test_background_load_items(self, remote: CobblerXMLRPCInterface):
        # Arrange
        remote.api.settings().lazy_start = True

        # Act
        result = remote.background_load_items()

        # Assert
        assert result
