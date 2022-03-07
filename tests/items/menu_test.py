from cobbler.items.menu import Menu


def test_object_creation(cobbler_api):
    # Arrange

    # Act
    distro = Menu(cobbler_api)

    # Arrange
    assert isinstance(distro, Menu)


def test_make_clone(cobbler_api):
    # Arrange
    menu = Menu(cobbler_api)

    # Act
    result = menu.make_clone()

    # Assert
    assert menu != result


def test_display_name(cobbler_api):
    # Arrange
    menu = Menu(cobbler_api)

    # Act
    menu.display_name = ""

    # Assert
    assert menu.display_name == ""
