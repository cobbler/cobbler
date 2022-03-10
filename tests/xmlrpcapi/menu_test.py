import pytest


@pytest.fixture
def create_menu(remote, token):
    """
    Creates a Menu "testmenu0" with a display_name "Test Menu0"

    :param remote: The xmlrpc object to connect to.
    :param token: The token to authenticate against the remote object.
    """
    menu = remote.new_menu(token)
    remote.modify_menu(menu, "name", "testmenu0", token)
    remote.modify_menu(menu, "display_name", "Test Menu0", token)
    remote.save_menu(menu, token)


@pytest.fixture
def remove_menu(remote, token):
    """
    Removes the Menu "testmenu0" which can be created with create_menu.

    :param remote: The xmlrpc object to connect to.
    :param token: The token to authenticate against the remote object.
    """
    yield
    remote.remove_menu("testmenu0", token)


class TestMenu:
    @pytest.mark.usefixtures("create_testmenu", "remove_testmenu")
    def test_create_submenu(self, remote, token):
        """
        Test: create/edit a submenu object
        """
        # Arrange
        menus = remote.get_menus(token)

        # Act
        submenu = remote.new_menu(token)

        # Assert
        assert remote.modify_menu(submenu, "name", "testsubmenu0", token)
        assert remote.modify_menu(submenu, "parent", "testmenu0", token)

        assert remote.save_menu(submenu, token)

        new_menus = remote.get_menus(token)
        assert len(new_menus) == len(menus) + 1
        remote.remove_menu("testsubmenu0", token, False)

    @pytest.mark.usefixtures("remove_menu")
    def test_create_menu(self, remote, token):
        """
        Test: create/edit a menu object
        """
        # Arrange --> Nothing to arrange

        # Act & Assert
        menu = remote.new_menu(token)
        assert remote.modify_menu(menu, "name", "testmenu0", token)
        assert remote.modify_menu(menu, "display_name", "Test Menu0", token)
        assert remote.save_menu(menu, token)

    def test_get_menus(self, remote):
        """
        Test: Get menus
        """
        # Arrange --> Nothing to do

        # Act
        result = remote.get_menus()

        # Assert
        assert result == []

    @pytest.mark.usefixtures("create_menu", "remove_menu")
    def test_get_menu(self, remote, token):
        """
        Test: Get a menu object
        """

        # Arrange --> Done in fixture

        # Act
        menu = remote.get_menu("testmenu0")

        # Assert
        assert menu.get("name") == "testmenu0"

    @pytest.mark.usefixtures("create_menu", "remove_menu")
    def test_find_menu(self, remote, token):
        """
        Test: find a menu object
        """

        # Arrange --> Done in fixture

        # Act
        result = remote.find_menu({"name": "testmenu0"}, token)

        # Assert
        assert result

    @pytest.mark.usefixtures("create_menu", "remove_menu")
    def test_copy_menu(self, remote, token):
        """
        Test: copy a menu object
        """

        # Arrange --> Done in fixture

        # Act
        menu = remote.get_item_handle("menu", "testmenu0", token)

        # Assert
        assert remote.copy_menu(menu, "testmenucopy", token)

        # Cleanup
        remote.remove_menu("testmenucopy", token)

    @pytest.mark.usefixtures("create_menu")
    def test_rename_menu(self, remote, token):
        """
        Test: rename a menu object
        """

        # Arrange

        # Act
        menu = remote.get_item_handle("menu", "testmenu0", token)
        result = remote.rename_menu(menu, "testmenu1", token)

        # Assert
        assert result

        # Cleanup
        remote.remove_menu("testmenu1", token)

    @pytest.mark.usefixtures("create_menu")
    def test_remove_menu(self, remote, token):
        """
        Test: remove a menu object
        """

        # Arrange --> Done in fixture

        # Act
        result = remote.remove_menu("testmenu0", token)

        # Assert
        assert result
