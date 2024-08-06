"""
Tests that validate the functionality of the module that is responsible for PAM authentication.
"""

from cobbler.api import CobblerAPI
from cobbler.modules.authentication import pam


class TestPam:
    def test_authenticate(self, cobbler_api: CobblerAPI):
        # Arrange
        test_username = "test"
        test_password = "test"

        # Act
        result = pam.authenticate(cobbler_api, test_username, test_password)

        # Assert
        assert result
