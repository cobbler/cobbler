import pytest

from cobbler.api import CobblerAPI
from cobbler.items.file import File
from tests.conftest import does_not_raise


def test_object_creation():
    # Arrange
    test_api = CobblerAPI()

    # Act
    distro = File(test_api)

    # Arrange
    assert isinstance(distro, File)


def test_make_clone():
    # Arrange
    test_api = CobblerAPI()
    file = File(test_api)

    # Act
    clone = file.make_clone()

    # Assert
    assert clone != file


# Properties Tests


@pytest.mark.parametrize("value,expected_exception", [
    (False, does_not_raise())
])
def test_is_dir(value, expected_exception):
    # Arrange
    test_api = CobblerAPI()
    file = File(test_api)

    # Act
    with expected_exception:
        file.is_dir = value

        # Assert
        assert file.is_dir is value
