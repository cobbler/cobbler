from cobbler.modules.managers import bind


def test_register():
    # Arrange & Act
    result = bind.register()

    # Assert
    assert result == "manage"


def test_manager_what():
    # Arrange & Act & Assert
    assert bind._BindManager.what() == "bind"


def test_get_manager(cobbler_api):
    # Arrange & Act
    result = bind.get_manager(cobbler_api)

    # Assert
    isinstance(result, bind._BindManager)
