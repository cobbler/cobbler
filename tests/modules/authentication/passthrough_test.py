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
