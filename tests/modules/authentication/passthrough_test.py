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

    def test_authenticate_secret_not_configured(self, monkeypatch):
        # Arrange: get_shared_secret returns -1 (not configured)
        def mockreturn():
            return -1
        monkeypatch.setattr(utils, "get_shared_secret", mockreturn)

        # Act: try with a non-trivial password
        result = passthru.authenticate("", "", "somepassword123")

        # Assert: must return False regardless of password
        assert not result

    def test_authenticate_empty_secret(self, monkeypatch):
        # Arrange: get_shared_secret returns "" (e.g. web.ss truncated during cobblerd
        # startup/rotation, before being rewritten)
        def mockreturn():
            return ""
        monkeypatch.setattr(utils, "get_shared_secret", mockreturn)

        # Act: try with an empty password, which would otherwise match via
        # hmac.compare_digest("" == "")
        result = passthru.authenticate("", "", "")

        # Assert: must return False even though password == secret == ""
        assert not result

    def test_authenticate_wrong_password(self, monkeypatch):
        # Arrange
        def mockreturn():
            return "correctsecret"
        monkeypatch.setattr(utils, "get_shared_secret", mockreturn)

        # Act: authenticate with wrong password
        result = passthru.authenticate("", "", "wrongpassword")

        # Assert
        assert not result

    def test_authenticate_correct_password_different_username(self, monkeypatch):
        # Arrange
        def mockreturn():
            return "correctsecret"
        monkeypatch.setattr(utils, "get_shared_secret", mockreturn)

        # Act: authenticate with correct password but different/arbitrary username
        result = passthru.authenticate("", "someotherusername", "correctsecret")

        # Assert: username should be ignored, returns True
        assert result
