"""
Tests for SystemGroup XML-RPC endpoints
"""

import time

import pytest

from cobbler.remote import CobblerXMLRPCInterface


def test_get_system_groups(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get system groups
    """
    # Arrange --> Nothing to arrange

    # Act
    result = remote.get_system_groups(token)

    # Assert
    assert result == []


def test_new_system_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: create a new system group object
    """
    # Arrange --> Nothing to arrange

    # Act
    handle = remote.new_system_group(token)

    # Assert
    assert handle is not None


def test_modify_save_and_get_system_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: modify, save and get a system group object
    """
    # Arrange
    handle = remote.new_system_group(token)
    remote.modify_system_group(handle, ["name"], "test_system_group", token)
    remote.save_system_group(handle, token, editmode="new")

    # Act
    group = remote.get_system_group("test_system_group", token=token)

    # Assert
    assert group is not None
    assert group["name"] == "test_system_group"  # type: ignore


@pytest.mark.parametrize(
    "create_item,expected_len",
    [
        (False, 0),
        (True, 1),
    ],
)
def test_find_system_group(
    remote: CobblerXMLRPCInterface, token: str, create_item: bool, expected_len: int
):
    """
    Test: find a system group object
    """
    # Arrange
    if create_item:
        handle = remote.new_system_group(token)
        remote.modify_system_group(handle, ["name"], "test_system_group", token)
        remote.save_system_group(handle, token, editmode="new")

    # Act
    result = remote.find_system_group(
        criteria={"name": "test_system_group"}, token=token
    )

    # Assert
    assert len(result) == expected_len


def test_copy_system_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: copy a system group object
    """
    # Arrange
    handle = remote.new_system_group(token)
    remote.modify_system_group(handle, ["name"], "test_system_group", token)
    remote.save_system_group(handle, token, editmode="new")
    system_group = remote.get_system_group_handle("test_system_group")

    # Act
    result = remote.copy_system_group(system_group, "test_system_group_copy", token)

    # Assert
    assert result


def test_rename_system_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: rename a system group object
    """
    # Arrange
    handle = remote.new_system_group(token)
    remote.modify_system_group(handle, ["name"], "test_system_group", token)
    remote.save_system_group(handle, token, editmode="new")
    system_group = remote.get_system_group_handle("test_system_group")

    # Act
    result = remote.rename_system_group(
        system_group, "test_system_group_renamed", token
    )

    # Assert
    assert result


def test_remove_system_group(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: remove a system group object
    """
    # Arrange
    handle = remote.new_system_group(token)
    remote.modify_system_group(handle, ["name"], "test_system_group_to_remove", token)
    remote.save_system_group(handle, token, editmode="new")

    # Act
    result = remote.remove_system_group("test_system_group_to_remove", token)

    # Assert
    assert result is True
    group = remote.get_system_group("test_system_group_to_remove", token=token)
    assert group == "~"


def test_get_system_groups_since(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get system groups since
    """
    # Arrange
    mtime = time.time()
    handle = remote.new_system_group(token)
    remote.modify_system_group(handle, ["name"], "test_system_group_since", token)
    remote.save_system_group(handle, token, editmode="new")

    # Act
    result = remote.get_system_groups_since(mtime)

    # Assert
    assert len(result) == 1  # pyright: ignore[reportArgumentType]
    assert result[0]["name"] == "test_system_group_since"  # type: ignore


def test_get_system_group_as_rendered(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get system group as rendered
    """
    # Arrange
    handle = remote.new_system_group(token)
    remote.modify_system_group(handle, ["name"], "test_system_group", token)
    remote.save_system_group(handle, token, editmode="new")

    # Act
    result = remote.get_system_group_as_rendered("test_system_group", token)

    # Assert
    assert result is not None
    assert result["name"] == "test_system_group"  # type: ignore
