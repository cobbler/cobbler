from cobbler.modules.authorization import allowall


def test_register():
    # Arrange & Act & Assert
    assert allowall.register() == "authz"


def test_authorize():
    # Arrange & Act & Assert
    assert allowall.authorize(None, None, None)
