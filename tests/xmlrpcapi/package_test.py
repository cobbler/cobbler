import pytest

"""
Order is important currently:
self._get_packages()
self._create_package()
self._get_package()
self._find_package()
self._copy_package()
self._rename_package()
self._remove_package()
"""


@pytest.fixture()
def create_package(remote, token):
    """
    Adds a "testpackage0" for a test.
    :param remote: See the correesponding fixture.
    :param token: See the correesponding fixture.
    """
    package = remote.new_package(token)
    remote.modify_package(package, "name", "testpackage0", token)
    remote.save_package(package, token)


@pytest.fixture()
def remove_package(remote, token):
    """
    Removes a "testpackage0" for a test.
    :param remote: See the correesponding fixture.
    :param token: See the correesponding fixture.
    """
    yield
    remote.remove_package("testpackage0", token)


class TestPackage:

    @pytest.mark.usefixtures("remove_package")
    def test_create_package(self, remote, token):
        """
        Test: create/edit a package object
        """

        packages = remote.get_packages(token)
        package = remote.new_package(token)

        assert remote.modify_package(package, "name", "testpackage0", token)
        assert remote.save_package(package, token)

        new_packages = remote.get_packages(token)
        assert len(new_packages) == len(packages) + 1

    @pytest.mark.usefixtures("create_package", "remove_package")
    def test_get_packages(self, remote, token):
        """
        Test: Get packages
        """

        package = remote.get_packages()

    @pytest.mark.usefixtures("create_package", "remove_package")
    def test_get_package(self, remote):
        """
        Test: Get a package object
        """

        package = remote.get_package("testpackage0")

    @pytest.mark.usefixtures("create_package", "remove_package")
    def test_find_package(self, remote, token):
        """
        Test: find a package object
        """

        result = remote.find_package({"name": "testpackage0"}, token)
        assert result

    @pytest.mark.usefixtures("create_package", "remove_package")
    def test_copy_package(self, remote, token):
        """
        Test: copy a package object
        """
        # Arrange --> Done in fixture

        # Act
        package = remote.get_item_handle("package", "testpackage0", token)
        result = remote.copy_package(package, "testpackagecopy", token)

        # Assert
        assert result

        # Cleanup
        remote.remove_package("testpackagecopy", token)

    @pytest.mark.usefixtures("create_package", "remove_package")
    def test_rename_package(self, remote, token):
        """
        Test: rename a package object
        """

        package = remote.get_item_handle("package", "testpackage0", token)
        assert remote.rename_package(package, "testpackage1", token)
        package = remote.get_item_handle("package", "testpackage1", token)
        assert remote.rename_package(package, "testpackage0", token)

    @pytest.mark.usefixtures("create_package")
    def test_remove_package(self, remote, token):
        """
        Test: remove a package object
        """
        # Arrange --> Done in Fixture
        # Act & Assert
        assert remote.remove_package("testpackage0", token)
