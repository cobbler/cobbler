"""
Tests for ProfileGroup XML-RPC endpoints
"""

import time

import pytest

from cobbler.remote import CobblerXMLRPCInterface


def test_get_profile_groups(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get profile groups
    """
    # Arrange --> Nothing to arrange

    # Act
    result = remote.get_profile_groups(token)

    # Assert
    assert result == []


def test_new_profile_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: create a new profile group object
    """
    # Arrange --> Nothing to arrange

    # Act
    handle = remote.new_profile_group(token)

    # Assert
    assert handle is not None


def test_modify_save_and_get_profile_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: modify, save and get a profile group object
    """
    # Arrange
    handle = remote.new_profile_group(token)
    remote.modify_profile_group(handle, ["name"], "test_profile_group", token)
    remote.save_profile_group(handle, token, editmode="new")

    # Act
    group = remote.get_profile_group("test_profile_group", token=token)

    # Assert
    assert group is not None
    assert group["name"] == "test_profile_group"  # type: ignore


@pytest.mark.parametrize(
    "create_item,expected_len",
    [
        (False, 0),
        (True, 1),
    ],
)
def test_find_profile_group(
    remote: CobblerXMLRPCInterface, token: str, create_item: bool, expected_len: int
):
    """
    Test: find a profile group object
    """
    # Arrange
    if create_item:
        handle = remote.new_profile_group(token)
        remote.modify_profile_group(handle, ["name"], "test_profile_group", token)
        remote.save_profile_group(handle, token, editmode="new")

    # Act
    result = remote.find_profile_group(
        criteria={"name": "test_profile_group"}, token=token
    )

    # Assert
    assert len(result) == expected_len


def test_copy_profile_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: copy a profile group object
    """
    # Arrange
    handle = remote.new_profile_group(token)
    remote.modify_profile_group(handle, ["name"], "test_profile_group", token)
    remote.save_profile_group(handle, token, editmode="new")
    profile_group = remote.get_profile_group_handle("test_profile_group")

    # Act
    result = remote.copy_profile_group(profile_group, "test_profile_group_copy", token)

    # Assert
    assert result


def test_rename_profile_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: rename a profile group object
    """
    # Arrange
    handle = remote.new_profile_group(token)
    remote.modify_profile_group(handle, ["name"], "test_profile_group", token)
    remote.save_profile_group(handle, token, editmode="new")
    profile_group = remote.get_profile_group_handle("test_profile_group")

    # Act
    result = remote.rename_profile_group(
        profile_group, "test_profile_group_renamed", token
    )

    # Assert
    assert result


def test_remove_profile_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: remove a profile group object
    """
    # Arrange
    handle = remote.new_profile_group(token)
    remote.modify_profile_group(handle, ["name"], "test_profile_group_to_remove", token)
    remote.save_profile_group(handle, token, editmode="new")

    # Act
    result = remote.remove_profile_group("test_profile_group_to_remove", token)

    # Assert
    assert result is True
    group = remote.get_profile_group("test_profile_group_to_remove", token=token)
    assert group == "~"


def test_get_profile_groups_since(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get profile groups since
    """
    # Arrange
    mtime = time.time()
    handle = remote.new_profile_group(token)
    remote.modify_profile_group(handle, ["name"], "test_profile_group_since", token)
    remote.save_profile_group(handle, token, editmode="new")

    # Act
    result = remote.get_profile_groups_since(mtime)

    # Assert
    assert len(result) == 1  # pyright: ignore[reportArgumentType]
    assert result[0]["name"] == "test_profile_group_since"  # type: ignore


def test_get_profile_group_as_rendered(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get profile group as rendered
    """
    # Arrange
    handle = remote.new_profile_group(token)
    remote.modify_profile_group(handle, ["name"], "test_profile_group", token)
    remote.save_profile_group(handle, token, editmode="new")

    # Act
    result = remote.get_profile_group_as_rendered("test_profile_group", token)

    # Assert
    assert result is not None
    assert result["name"] == "test_profile_group"  # type: ignore
