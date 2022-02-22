from cobbler.modules.authorization import ownership


def test_register():
    # Arrange & Act & Assert
    assert ownership.register() == "authz"
