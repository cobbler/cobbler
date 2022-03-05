from cobbler.modules.authentication import pam


class TestPam:
    def test_authenticate(self, cobbler_api):
        # Arrange
        test_username = "test"
        test_password = "test"

        # Act
        result = pam.authenticate(cobbler_api, test_username, test_password)

        # Assert
        assert result
