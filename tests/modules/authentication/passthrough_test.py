from cobbler import utils
from cobbler.modules.authentication import passthru


class TestPassthrough:
    def test_authenticate_negative(self):
        # Arrange & Act
        result = passthru.authenticate("", "", "")

        # Assert
        assert not result

    def test_authenticate(self, monkeypatch):
        # Arrange
        def mockreturn():
            return "testpassword"
        monkeypatch.setattr(utils, "get_shared_secret", mockreturn)

        # Act
        result = passthru.authenticate("", "", "testpassword")

        # Assert
        assert result
