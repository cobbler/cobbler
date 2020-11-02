from cobbler.api import CobblerAPI
from cobbler.modules.authentication import pam


class TestPam:
    def test_authenticate(self):
        # Arrange
        test_username = "test"
        test_password = "test"
        test_api = CobblerAPI()

        # Act
        result = pam.authenticate(test_api, test_username, test_password)

        # Assert
        assert result
