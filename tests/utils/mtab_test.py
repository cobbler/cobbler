from cobbler.utils import mtab


def test_get_mtab():
    # Arrange

    # Act
    result = mtab.get_mtab()

    # Assert
    assert isinstance(result, list)


def test_get_file_device_path():
    # Arrange

    # Act
    result = mtab.get_file_device_path("/etc/os-release")

    # Assert
    # TODO Does not work in all environments (e.g. openSUSE TW with BTRFS)
    assert result == ("overlay", "/usr/lib/os-release")


def test_is_remote_file():
    # Arrange

    # Act
    result = mtab.is_remote_file("/etc/os-release")

    # Assert
    assert not result
