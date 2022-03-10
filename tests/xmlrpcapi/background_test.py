import pytest


class TestBackground:
    """
    Class to test various background jobs
    """

    def test_background_acletup(self, remote, token):
        # Arrange

        # Act
        result = remote.background_aclsetup({}, token)

        # Assert
        assert result

    def test_background_buildiso(self, remote, token):
        # Arrange

        # Act
        result = remote.background_buildiso({}, token)

        # Assert
        assert result

    def test_background_hardlink(self, remote, token):
        # Arrange

        # Act
        result = remote.background_hardlink({}, token)

        # Assert
        assert result

    def test_background_import(self, remote, token):
        # Arrange

        # Act
        result = remote.background_import({}, token)

        # Assert
        assert result

    def test_background_replicate(self, remote, token):
        # Arrange

        # Act
        result = remote.background_replicate({}, token)

        # Assert
        assert result

    def test_background_reposync(self, remote, token):
        # Arrange

        # Act
        result = remote.background_reposync({}, token)

        # Assert
        assert result

    def test_background_validate_autoinstall_files(self, remote, token):
        # Arrange

        # Act
        result = remote.background_validate_autoinstall_files({}, token)

        # Assert
        assert result
