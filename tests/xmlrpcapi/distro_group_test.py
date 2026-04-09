"""
Tests for DistroGroup XML-RPC endpoints
"""

import time

import pytest

from cobbler.remote import CobblerXMLRPCInterface


def test_get_distro_groups(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get distro groups
    """
    # Arrange --> Nothing to arrange

    # Act
    result = remote.get_distro_groups(token)

    # Assert
    assert result == []


def test_new_distro_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: create a new distro group object
    """
    # Arrange --> Nothing to arrange

    # Act
    handle = remote.new_distro_group(token)

    # Assert
    assert handle is not None


def test_modify_save_and_get_distro_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: modify, save and get a distro group object
    """
    # Arrange
    handle = remote.new_distro_group(token)
    remote.modify_distro_group(handle, ["name"], "test_distro_group", token)
    remote.save_distro_group(handle, token, editmode="new")

    # Act
    group = remote.get_distro_group("test_distro_group", token=token)

    # Assert
    assert group is not None
    assert group["name"] == "test_distro_group"  # type: ignore


@pytest.mark.parametrize(
    "create_item,expected_len",
    [
        (False, 0),
        (True, 1),
    ],
)
def test_find_distro_group(
    remote: CobblerXMLRPCInterface, token: str, create_item: bool, expected_len: int
):
    """
    Test: find a distro group object
    """
    # Arrange
    if create_item:
        handle = remote.new_distro_group(token)
        remote.modify_distro_group(handle, ["name"], "test_distro_group", token)
        remote.save_distro_group(handle, token, editmode="new")

    # Act
    result = remote.find_distro_group(
        criteria={"name": "test_distro_group"}, token=token
    )

    # Assert
    assert len(result) == expected_len


def test_copy_distro_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: copy a distro group object
    """
    # Arrange
    handle = remote.new_distro_group(token)
    remote.modify_distro_group(handle, ["name"], "test_distro_group", token)
    remote.save_distro_group(handle, token, editmode="new")
    distro_group = remote.get_distro_group_handle("test_distro_group")

    # Act
    result = remote.copy_distro_group(distro_group, "test_distro_group_copy", token)

    # Assert
    assert result


def test_rename_distro_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: rename a distro group object
    """
    # Arrange
    handle = remote.new_distro_group(token)
    remote.modify_distro_group(handle, ["name"], "test_distro_group", token)
    remote.save_distro_group(handle, token, editmode="new")
    distro_group = remote.get_distro_group_handle("test_distro_group")

    # Act
    result = remote.rename_distro_group(
        distro_group, "test_distro_group_renamed", token
    )

    # Assert
    assert result


def test_remove_distro_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: remove a distro group object
    """
    # Arrange
    handle = remote.new_distro_group(token)
    remote.modify_distro_group(handle, ["name"], "test_distro_group_to_remove", token)
    remote.save_distro_group(handle, token, editmode="new")

    # Act
    result = remote.remove_distro_group("test_distro_group_to_remove", token)

    # Assert
    assert result is True
    group = remote.get_distro_group("test_distro_group_to_remove", token=token)
    assert group == "~"


def test_get_distro_groups_since(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get distro groups since
    """
    # Arrange
    mtime = time.time()
    handle = remote.new_distro_group(token)
    remote.modify_distro_group(handle, ["name"], "test_distro_group_since", token)
    remote.save_distro_group(handle, token, editmode="new")

    # Act
    result = remote.get_distro_groups_since(mtime)

    # Assert
    assert len(result) == 1  # pyright: ignore[reportArgumentType]
    assert result[0]["name"] == "test_distro_group_since"  # type: ignore


def test_get_distro_group_as_rendered(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get distro group as rendered
    """
    # Arrange
    handle = remote.new_distro_group(token)
    remote.modify_distro_group(handle, ["name"], "test_distro_group", token)
    remote.save_distro_group(handle, token, editmode="new")

    # Act
    result = remote.get_distro_group_as_rendered("test_distro_group", token)

    # Assert
    assert result is not None
    assert result["name"] == "test_distro_group"  # type: ignore
