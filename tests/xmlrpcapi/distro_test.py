import os

import pytest


@pytest.fixture(scope="function")
def distro_fields(fk_initrd, fk_kernel):
    """
    Field format: field_name, good value(s), bad value(s)
    Field order is the order in which they will be set

    :param fk_initrd:
    :param fk_kernel:
    :return:
    """
    # TODO: include fields with dependencies: fetchable files, boot files, etc.
    return [
        ["arch", ["i386", "x86_64", "ppc", "ppc64"], ["badarch"]],
        # generic must be last breed to be set so os_version test below will work
        ["breed", ["debian", "freebsd", "redhat", "suse", "ubuntu", "unix", "vmware", "windows", "xen", "generic"],
         ["badbreed"]],
        ["comment", ["test comment", ], []],
        ["initrd", [fk_initrd, ], ["", ]],
        ["name", ["testdistro0"], []],
        ["kernel", [fk_kernel, ], ["", ]],
        ["kernel_options", ["a=1 b=2 c=3 c=4 c=5 d e", ], []],
        ["kernel_options_post", ["a=1 b=2 c=3 c=4 c=5 d e", ], []],
        ["autoinstall_meta", ["a=1 b=2 c=3 c=4 c=5 d e", ], []],
        ["mgmt_classes", ["one two three", ], []],
        ["os_version", ["generic26", ], ["bados", ]],
        ["owners", ["user1 user2 user3", ], []],
        ["boot_loaders", ["pxe ipxe grub yaboot", ], ["badloader"]],
    ]


@pytest.mark.usefixtures("cobbler_xmlrpc_base")
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

    @pytest.mark.usefixtures("remove_testdistro")
    def test_create_distro_positive(self, remote, token, distro_fields, create_kernel_initrd, fk_kernel, fk_initrd):
        """
        Test: create/edit a distro with valid values
        """
        # Arrange --> Nothing to do.
        folder = create_kernel_initrd(fk_kernel, fk_initrd)

        # Act
        distro = remote.new_distro(token)
        remote.modify_distro(distro, "name", "testdistro", token)

        # Assert
        for field in distro_fields:
            (fname, fgood, _) = field
            for fg in fgood:
                try:
                    if fname in ("kernel", "initrd"):
                        fg = os.path.join(folder, fg)
                    result = remote.modify_distro(distro, fname, fg, token)
                    assert result
                except Exception as e:
                    pytest.fail("good field (%s=%s) raised exception: %s" % (fname, fg, str(e)))

        result_save_success = remote.save_distro(distro, token)
        assert result_save_success

    @pytest.mark.usefixtures("remove_testdistro")
    def test_create_distro_negative(self, remote, token, distro_fields, fk_kernel, fk_initrd):
        """
        Test: create/edit a distro with invalid values
        """
        # Arrange --> Nothing to do.

        # Act
        distro = remote.new_distro(token)
        remote.modify_distro(distro, "name", "testdistro0", token)

        # Assert
        for field in distro_fields:
            (fname, _, fbad) = field
            for fb in fbad:
                try:
                    remote.modify_distro(distro, fname, fb, token)
                except:
                    pass
                else:
                    pytest.fail("bad field (%s=%s) did not raise an exception" % (fname, fb))
        assert True

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
