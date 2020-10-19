from cobbler.api import CobblerAPI
from cobbler.items.package import Package


def test_object_creation():
    # Arrange
    test_api = CobblerAPI()

    # & Act
    package = Package(test_api)

    # Arrange
    assert isinstance(package, Package)


def test_make_clone():
    # Arrange
    test_api = CobblerAPI()
    package = Package(test_api)

    # Act
    result = package.make_clone()

    # Assert
    assert package != result


def test_installer():
    # Arrange
    test_api = CobblerAPI()
    package = Package(test_api)

    # Act
    package.installer = ""

    # Assert
    assert package.installer == ""


def test_version():
    # Arrange
    test_api = CobblerAPI()
    package = Package(test_api)

    # Act
    package.version = ""

    # Assert
    assert package.version == ""
