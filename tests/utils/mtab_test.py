import os

from cobbler.utils import mtab


def test_get_mtab():
    # Arrange

    # Act
    result = mtab.get_mtab()

    # Assert
    assert isinstance(result, list)


def test_get_file_device_path():
    # Arrange
    test_symlink = "/tmp/test_symlink"
    os.symlink("/foobar/test", test_symlink)

    # Act
    result = mtab.get_file_device_path(test_symlink)

    # Cleanup
    os.remove(test_symlink)

    # Assert
    assert len(result) == 2
    assert isinstance(result[0], str)
    assert result[1] == "/foobar/test"


def test_is_remote_file():
    # Arrange

    # Act
    result = mtab.is_remote_file("/etc/os-release")

    # Assert
    assert not result
