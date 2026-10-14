from cobbler.api import CobblerAPI
from cobbler.modules.authorization import configfile


def test_register():
    # Arrange & Act & Assert
    assert configfile.register() == "authz"


def test_get_authorization_handler(cobbler_api: CobblerAPI):
    # Arrange & Act
    handler = configfile.get_authorization_handler(cobbler_api)
    # Assert
    assert handler.api is cobbler_api
