from cobbler import enums
from cobbler.items.package import Package


def test_object_creation(cobbler_api):
    # Arrange

    # & Act
    package = Package(cobbler_api)

    # Arrange
    assert isinstance(package, Package)


def test_make_clone(cobbler_api):
    # Arrange
    package = Package(cobbler_api)

    # Act
    result = package.make_clone()

    # Assert
    assert package != result


def test_installer(cobbler_api):
    # Arrange
    package = Package(cobbler_api)

    # Act
    package.installer = ""

    # Assert
    assert package.installer == ""


def test_version(cobbler_api):
    # Arrange
    package = Package(cobbler_api)

    # Act
    package.version = ""

    # Assert
    assert package.version == ""


def test_to_dict(cobbler_api):
    # Arrange
    titem = Package(cobbler_api)

    # Act
    result = titem.to_dict()

    # Assert
    assert isinstance(result, dict)


def test_to_dict_resolved(cobbler_api):
    # Arrange
    titem = Package(cobbler_api)

    # Act
    result = titem.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert enums.VALUE_INHERITED not in str(result)
