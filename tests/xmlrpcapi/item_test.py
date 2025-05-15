"""
Tests that validate the functionality of the module that is responsible for providing XML-RPC calls related to
generic items.
"""

import pytest

from cobbler.remote import CobblerXMLRPCInterface


@pytest.mark.usefixtures("create_testdistro", "remove_testdistro")
def test_get_item_resolved(
    remote: CobblerXMLRPCInterface, fk_initrd: str, fk_kernel: str
):
    """
    Test: get an item object (in this case distro) which is resolved
    """
    # Arrange --> Done in fixture

    # Act
    distro = remote.get_item("distro", "testdistro0", resolved=True)

    # Assert
    assert distro.get("name") == "testdistro0"  # type: ignore
    assert distro.get("redhat_management_key") == ""  # type: ignore
    assert distro.get("redhat_management_org") == ""  # type: ignore
    assert distro.get("redhat_management_user") == ""  # type: ignore
    assert distro.get("redhat_management_password") == ""  # type: ignore
    assert fk_initrd in distro.get("initrd")  # type: ignore
    assert fk_kernel in distro.get("kernel")  # type: ignore


def test_remove_item(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: remove item object (in this case menu).
    """
    # Arrange
    test_menu = remote.new_menu(token)  # type: ignore
    remote.modify_menu(test_menu, "name", "testmenu0", token)
    remote.modify_menu(test_menu, "display_name", "testmenu0", token)

    # Act
    result = remote.remove_menu("testmenu0", token, True)  # type: ignore

    # Assert
    assert result
    assert not test_menu in remote.unsaved_items


def test_create_unsaved_item(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: create unsaved item (in this case menu)
    """
    test_menu = remote.new_menu(token)
    remote.modify_menu(test_menu, "name", "testmenu0", token)
    remote.modify_menu(test_menu, "display_name", "testmenu", token)
    assert test_menu in remote.unsaved_items
