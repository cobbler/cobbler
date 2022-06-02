import os

import pytest

from cobbler import enums
from cobbler.cexceptions import CX


@pytest.fixture(autouse=True)
def cleanup_create_distro_positive(cobbler_api):
    yield
    cobbler_api.remove_distro("create_distro_positive")


class TestDistro:
    """
    Test remote calls related to distros.
    """

    def test_get_distros(self, remote, token):
        """
        Test: get distros
        """
        # Arrange --> Nothing to arrange

        # Act
        result = remote.get_distros(token)

        # Assert
        assert result == []

    @pytest.mark.parametrize("field_name,field_value", [
        ("arch", "i386"),
        ("breed", "debian"),
        ("breed", "freebsd"),
        ("breed", "redhat"),
        ("breed", "suse"),
        ("breed", "ubuntu"),
        ("breed", "unix"),
        ("breed", "vmware"),
        ("breed", "windows"),
        ("breed", "xen"),
        ("breed", "generic"),
        ("comment", "test comment"),
        ("initrd", ""),
        ("name", "testdistro0"),
        ("kernel", ""),
        ("kernel_options", "a=1 b=2 c=3 c=4 c=5 d e"),
        ("kernel_options_post", "a=1 b=2 c=3 c=4 c=5 d e"),
        ("autoinstall_meta", "a=1 b=2 c=3 c=4 c=5 d e"),
        ("mgmt_classes", "one two three"),
        ("os_version", "rhel4"),
        ("owners", "user1 user2 user3"),
        ("boot_loaders", "pxe ipxe grub")
    ])
    def test_create_distro_positive(self, remote, token, create_kernel_initrd, fk_kernel, fk_initrd, field_name,
                                    field_value, cleanup_create_distro_positive):
        """
        Test: create/edit a distro with valid values
        """
        # Arrange --> Nothing to do.
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        distro = remote.new_distro(token)
        remote.modify_distro(distro, "name", "create_distro_positive", token)

        # Act
        if field_name == "kernel":
            field_value = os.path.join(folder, fk_kernel)
        if field_name == "initrd":
            field_value = os.path.join(folder, fk_initrd)
        result = remote.modify_distro(distro, field_name, field_value, token)

        # Assert
        assert result

    @pytest.mark.parametrize("field_name,field_value", [
        ("arch", "badarch"),
        ("breed", "badbreed"),
        # ("boot_loader", "badloader") FIXME: This does not raise but did in the past
    ])
    def test_create_distro_negative(self, remote, token, field_name, field_value):
        """
        Test: create/edit a distro with invalid values
        """
        # Arrange
        distro = remote.new_distro(token)
        remote.modify_distro(distro, "name", "testdistro0", token)

        # Act & Assert
        try:
            remote.modify_distro(distro, field_name, field_value, token)
        except (CX, TypeError, ValueError):
            assert True
        else:
            pytest.fail("Bad field did not raise an exception!")

    @pytest.mark.usefixtures("create_testdistro", "remove_testdistro")
    def test_get_distro(self, remote, fk_initrd, fk_kernel):
        """
        Test: get a distro object
        """
        # Arrange --> Done in fixture

        # Act
        distro = remote.get_distro("testdistro0")

        # Assert
        assert distro.get("name") == "testdistro0"
        assert distro.get("redhat_management_key") == enums.VALUE_INHERITED
        assert fk_initrd in distro.get("initrd")
        assert fk_kernel in distro.get("kernel")

    def test_get_system(self, remote):
        """
        Test: get a system object
        """
        # Arrange --> There should be no system present. --> Nothing to Init.

        # Act
        system = remote.get_system("testsystem0")

        # Assert
        assert system is "~"

    def test_find_distro(self, remote, token):
        """
        Test: find a distro object
        """
        # Arrange --> No distros means no setup

        # Act
        result = remote.find_distro({"name": "testdistro0"}, token)

        # Assert
        assert result == []

    @pytest.mark.usefixtures("create_testdistro", "remove_testdistro")
    def test_copy_distro(self, remote, token):
        """
        Test: copy a distro object
        """
        # Arrange --> Done in the fixture

        # Act
        distro = remote.get_item_handle("distro", "testdistro0", token)
        result = remote.copy_distro(distro, "testdistrocopy", token)

        # Assert
        assert result

        # Cleanup --> Plus fixture
        remote.remove_distro("testdistrocopy", token)

    @pytest.mark.usefixtures("create_testdistro")
    def test_rename_distro(self, remote, token):
        """
        Test: rename a distro object
        """
        # Arrange
        distro = remote.get_item_handle("distro", "testdistro0", token)

        # Act
        result = remote.rename_distro(distro, "testdistro1", token)

        # Assert
        assert result

        # Cleanup
        remote.remove_distro("testdistro1", token)

    def test_remove_distro(self, remote, token):
        """
        Test: remove a distro object
        """
        # Arrange
        # TODO: Verify why the test passes without the fixture for creating the distro!

        # Act
        result = remote.remove_distro("testdistro0", token)

        # Assert
        assert result
