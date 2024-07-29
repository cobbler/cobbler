"""
Tests that validate the functionality of the module that is responsible for authorization.
"""

from cobbler.api import CobblerAPI
from cobbler.modules.authorization import allowall


def test_register():
    # Arrange & Act & Assert
    assert allowall.register() == "authz"


def test_authorize(cobbler_api: CobblerAPI):
    # Arrange & Act & Assert
    assert allowall.authorize(cobbler_api, "", "")
