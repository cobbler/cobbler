from cobbler.modules.authorization import configfile


def test_register():
    # Arrange & Act & Assert
    assert configfile.register() == "authz"
