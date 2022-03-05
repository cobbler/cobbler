from cobbler import enums
from cobbler.items.resource import Resource


def test_object_creation(cobbler_api):
    # Arrange

    # Act
    distro = Resource(cobbler_api)

    # Arrange
    assert isinstance(distro, Resource)


def test_make_clone(cobbler_api):
    # Arrange
    resource = Resource(cobbler_api)

    # Act
    result = resource.make_clone()

    # Assert
    assert result != resource

# Properties Tests


def test_action(cobbler_api):
    # Arrange
    resource = Resource(cobbler_api)

    # Act
    resource.action = "create"

    # Assert
    assert resource.action == enums.ResourceAction.CREATE


def test_group(cobbler_api):
    # Arrange
    resource = Resource(cobbler_api)

    # Act
    resource.group = "test"

    # Assert
    assert resource.group == "test"


def test_mode(cobbler_api):
    # Arrange
    resource = Resource(cobbler_api)

    # Act
    resource.mode = "test"

    # Assert
    assert resource.mode == "test"


def test_owner(cobbler_api):
    # Arrange
    resource = Resource(cobbler_api)

    # Act
    resource.owner = "test"

    # Assert
    assert resource.owner == "test"


def test_path(cobbler_api):
    # Arrange
    resource = Resource(cobbler_api)

    # Act
    resource.path = "test"

    # Assert
    assert resource.path == "test"


def test_template(cobbler_api):
    # Arrange
    resource = Resource(cobbler_api)

    # Act
    resource.template = "test"

    # Assert
    assert resource.template == "test"
