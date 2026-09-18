"""
Tests that validate the functionality of the module that is responsible for passthrough authentication.
"""

from pytest import MonkeyPatch

from cobbler import utils
from cobbler.api import CobblerAPI
from cobbler.modules.authentication import passthru


class TestPassthrough:
    def test_authenticate_negative(self, cobbler_api: CobblerAPI):
        # Arrange & Act
        result = passthru.authenticate(cobbler_api, "", "")

        # Assert
        assert not result

    def test_authenticate(self, monkeypatch: MonkeyPatch, cobbler_api: CobblerAPI):
        # Arrange
        def mockreturn():
            return "testpassword"

        monkeypatch.setattr(utils, "get_shared_secret", mockreturn)

        # Act
        result = passthru.authenticate(cobbler_api, "", "testpassword")

        # Assert
        assert result

    def test_authenticate_unconfigured_secret(
        self, monkeypatch: MonkeyPatch, cobbler_api: CobblerAPI
    ):
        # Arrange - secret is -1 when not configured
        def mockreturn():
            return -1

        monkeypatch.setattr(utils, "get_shared_secret", mockreturn)

        # Act
        result = passthru.authenticate(cobbler_api, "", "anything")

        # Assert
        assert not result

    def test_authenticate_empty_secret(
        self, monkeypatch: MonkeyPatch, cobbler_api: CobblerAPI
    ):
        # Arrange - secret is "" if web.ss was truncated mid-regeneration
        def mockreturn():
            return ""

        monkeypatch.setattr(utils, "get_shared_secret", mockreturn)

        # Act
        result = passthru.authenticate(cobbler_api, "", "")

        # Assert: an empty password must never match an empty secret
        assert not result

    def test_authenticate_wrong_secret(
        self, monkeypatch: MonkeyPatch, cobbler_api: CobblerAPI
    ):
        # Arrange
        def mockreturn():
            return "correctpassword"

        monkeypatch.setattr(utils, "get_shared_secret", mockreturn)

        # Act
        result = passthru.authenticate(cobbler_api, "", "wrongpassword")

        # Assert
        assert not result

    def test_authenticate_correct_password_different_username(
        self, monkeypatch: MonkeyPatch, cobbler_api: CobblerAPI
    ):
        # Arrange
        def mockreturn():
            return "correctsecret"

        monkeypatch.setattr(utils, "get_shared_secret", mockreturn)

        # Act: authenticate with correct password but different/arbitrary username
        result = passthru.authenticate(
            cobbler_api, "someotherusername", "correctsecret"
        )

        # Assert: username should be ignored, returns True
        assert result
