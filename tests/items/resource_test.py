from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.resource import Resource


def test_object_creation():
    # Arrange
    test_api = CobblerAPI()

    # Act
    distro = Resource(test_api)

    # Arrange
    assert isinstance(distro, Resource)


def test_make_clone():
    # Arrange
    test_api = CobblerAPI()
    resource = Resource(test_api)

    # Act
    result = resource.make_clone()

    # Assert
    assert result != resource

# Properties Tests


def test_action():
    # Arrange
    test_api = CobblerAPI()
    resource = Resource(test_api)

    # Act
    resource.action = "create"

    # Assert
    assert resource.action == enums.ResourceAction.CREATE


def test_group():
    # Arrange
    test_api = CobblerAPI()
    resource = Resource(test_api)

    # Act
    resource.group = "test"

    # Assert
    assert resource.group == "test"


def test_mode():
    # Arrange
    test_api = CobblerAPI()
    resource = Resource(test_api)

    # Act
    resource.mode = "test"

    # Assert
    assert resource.mode == "test"


def test_owner():
    # Arrange
    test_api = CobblerAPI()
    resource = Resource(test_api)

    # Act
    resource.owner = "test"

    # Assert
    assert resource.owner == "test"


def test_path():
    # Arrange
    test_api = CobblerAPI()
    resource = Resource(test_api)

    # Act
    resource.path = "test"

    # Assert
    assert resource.path == "test"


def test_template():
    # Arrange
    test_api = CobblerAPI()
    resource = Resource(test_api)

    # Act
    resource.template = "test"

    # Assert
    assert resource.template == "test"
