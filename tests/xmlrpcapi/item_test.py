import pytest

from cobbler.api import CobblerAPI
from cobbler.items.menu import Menu
from cobbler.remote import CobblerXMLRPCInterface


@pytest.mark.usefixtures("create_testdistro", "remove_testdistro")
def test_get_item_resolved(remote, fk_initrd, fk_kernel):
    """
    Test: get an item object (in this case distro) which is resolved
    """
    # Arrange --> Done in fixture

    # Act
    distro = remote.get_item("distro", "testdistro0", resolved=True)

    # Assert
    assert distro.get("name") == "testdistro0"
    assert distro.get("redhat_management_key") == ""
    assert fk_initrd in distro.get("initrd")
    assert fk_kernel in distro.get("kernel")


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
