from cobbler.api import CobblerAPI
from cobbler.items.menu import Menu


def test_object_creation():
    # Arrange
    test_api = CobblerAPI()

    # Act
    distro = Menu(test_api)

    # Arrange
    assert isinstance(distro, Menu)


def test_make_clone():
    # Arrange
    test_api = CobblerAPI()
    menu = Menu(test_api)

    # Act
    result = menu.make_clone()

    # Assert
    assert menu != result


def test_display_name():
    # Arrange
    test_api = CobblerAPI()
    menu = Menu(test_api)

    # Act
    menu.display_name = ""

    # Assert
    assert menu.display_name == ""
