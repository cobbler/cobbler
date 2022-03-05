import pytest

from cobbler.items.file import File
from tests.conftest import does_not_raise


def test_object_creation(cobbler_api):
    # Arrange

    # Act
    distro = File(cobbler_api)

    # Arrange
    assert isinstance(distro, File)


def test_make_clone(cobbler_api):
    # Arrange
    file = File(cobbler_api)

    # Act
    clone = file.make_clone()

    # Assert
    assert clone != file


# Properties Tests


@pytest.mark.parametrize("value,expected_exception", [
    (False, does_not_raise())
])
def test_is_dir(cobbler_api, value, expected_exception):
    # Arrange
    file = File(cobbler_api)

    # Act
    with expected_exception:
        file.is_dir = value

        # Assert
        assert file.is_dir is value
