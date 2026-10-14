from cobbler.api import CobblerAPI
from cobbler.modules.authorization import ownership


def test_register():
    # Arrange & Act & Assert
    assert ownership.register() == "authz"


def test_get_authorization_handler(cobbler_api: CobblerAPI):
    # Arrange & Act
    handler = ownership.get_authorization_handler(cobbler_api)
    # Assert
    assert handler.api is cobbler_api
