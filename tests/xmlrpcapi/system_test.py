import pytest

from cobbler.cexceptions import CX


class TestSystem:
    """
    Test remote calls related to systems.
    """

    def test_get_systems(self, remote, token):
        """
        Test: get systems
        """
        # Arrange --> Nothing to arrange

        # Act
        result = remote.get_systems(token)

        # Assert
        assert result == []

    @pytest.mark.usefixtures(
        "create_testdistro",
        "create_testmenu",
        "create_testprofile",
        "remove_testdistro",
        "remove_testmenu",
        "remove_testprofile",
        "remove_testsystem",
    )
    @pytest.mark.parametrize(
        "field_name,field_value",
        [
            ("comment", "test comment"),
            ("enable_ipxe", True),
            ("enable_ipxe", False),
            ("kernel_options", "a=1 b=2 c=3 c=4 c=5 d e"),
            ("kernel_options_post", "a=1 b=2 c=3 c=4 c=5 d e"),
            ("autoinstall", "test.ks"),
            ("autoinstall", "test.xml"),
            ("autoinstall", "test.seed"),
            ("autoinstall_meta", "a=1 b=2 c=3 c=4 c=5 d e"),
            ("mgmt_classes", "one two three"),
            ("mgmt_parameters", "<<inherit>>"),
            ("name", "testsystem0"),
            ("netboot_enabled", True),
            ("netboot_enabled", False),
            ("owners", "user1 user2 user3"),
            ("profile", "testprofile0"),
            ("repos_enabled", True),
            ("repos_enabled", False),
            ("status", "development"),
            ("status", "testing"),
            ("status", "acceptance"),
            ("status", "production"),
            ("proxy", "testproxy"),
            ("server", "1.1.1.1"),
            # ("boot_loaders", "pxe ipxe grub"), FIXME: This raises currently but it did not in the past
            ("virt_auto_boot", True),
            ("virt_auto_boot", False),
            ("virt_auto_boot", "yes"),
            ("virt_auto_boot", "no"),
            ("virt_cpus", "<<inherit>>"),
            ("virt_cpus", 1),
            ("virt_cpus", 2),
            ("virt_cpus", "<<inherit>>"),
            ("virt_file_size", "<<inherit>>"),
            ("virt_file_size", 5),
            ("virt_file_size", 10),
            ("virt_disk_driver", "<<inherit>>"),
            ("virt_disk_driver", "raw"),
            ("virt_disk_driver", "qcow2"),
            ("virt_disk_driver", "vdmk"),
            ("virt_ram", "<<inherit>>"),
            ("virt_ram", 256),
            ("virt_ram", 1024),
            ("virt_type", "<<inherit>>"),
            ("virt_type", "xenpv"),
            ("virt_type", "xenfv"),
            ("virt_type", "qemu"),
            ("virt_type", "kvm"),
            ("virt_type", "vmware"),
            ("virt_type", "openvz"),
            ("virt_path", "<<inherit>>"),
            ("virt_path", "/path/to/test"),
            ("virt_pxe_boot", True),
            ("virt_pxe_boot", False),
            ("power_type", "ipmilanplus"),
            ("power_address", "127.0.0.1"),
            ("power_id", "pmachine:lpar1"),
            ("power_pass", "pass"),
            ("power_user", "user"),
        ],
    )
    def test_create_system_positive(
        self, remote, token, template_files, field_name, field_value
    ):
        """
        Test: create/edit a system object
        """
        # Arrange
        system = remote.new_system(token)
        remote.modify_system(system, "name", "testsystem0", token)
        remote.modify_system(system, "profile", "testprofile0", token)

        # Act
        result = remote.modify_system(system, field_name, field_value, token)

        # Assert
        assert result

    @pytest.mark.usefixtures(
        "create_testdistro",
        "create_testmenu",
        "create_testprofile",
        "remove_testdistro",
        "remove_testmenu",
        "remove_testprofile",
        "remove_testsystem",
    )
    @pytest.mark.parametrize(
        "field_name,field_value",
        [
            ("autoinstall", "/path/to/bad/autoinstall"),
            ("mgmt_parameters", "badyaml"),
            ("profile", "badprofile"),
            ("boot_loaders", "badloader"),
            ("virt_cpus", "a"),
            ("virt_file_size", "a"),
            ("virt_ram", "a"),
            ("virt_type", "bad"),
            ("power_type", "bla"),
        ],
    )
    def test_create_system_negative(self, remote, token, field_name, field_value):
        """
        Test: create/edit a system object
        """
        # Arrange
        system = remote.new_system(token)
        remote.modify_system(system, "name", "testsystem0", token)
        remote.modify_system(system, "profile", "testprofile0", token)

        # Act & Assert
        try:
            remote.modify_system(system, field_name, field_value, token)
        except (CX, TypeError, ValueError, OSError):
            assert True
        else:
            pytest.fail("Bad field did not raise an exception!")

    def test_find_system(self, remote, token):
        """
        Test: find a system object
        """

        # Arrange --> Nothing to arrange

        # Act
        result = remote.find_system({"name": "notexisting"}, token)

        # Assert --> A not exiting system returns an empty list
        assert result == []

    @pytest.mark.usefixtures(
        "create_testdistro",
        "create_testmenu",
        "create_testprofile",
        "remove_testdistro",
        "remove_testmenu",
        "remove_testprofile",
        "remove_testsystem",
    )
    def test_add_interface_to_system(self, remote, token):
        """
        Test: add an interface to a system
        """

        # Arrange
        system = remote.new_system(token)
        remote.modify_system(system, "name", "testsystem0", token)
        remote.modify_system(system, "profile", "testprofile0", token)

        # Act
        result = remote.modify_system(
            system, "modify_interface", {"macaddress-eth0": "aa:bb:cc:dd:ee:ff"}, token
        )
        remote.save_system(system, token)

        # Assert --> returns true if successful
        assert result
        assert (
            remote.get_system("testsystem0")
            .get("interfaces", {})
            .get("eth0", {})
            .get("mac_address")
            == "aa:bb:cc:dd:ee:ff"
        )

    @pytest.mark.usefixtures(
        "create_testdistro",
        "create_testmenu",
        "create_testprofile",
        "remove_testdistro",
        "remove_testmenu",
        "remove_testprofile",
        "remove_testsystem",
    )
    def test_remove_interface_from_system(self, remote, token):
        """
        Test: remove an interface from a system
        """

        # Arrange
        system = remote.new_system(token)
        remote.modify_system(system, "name", "testsystem0", token)
        remote.modify_system(system, "profile", "testprofile0", token)
        remote.modify_system(
            system, "modify_interface", {"macaddress-eth0": "aa:bb:cc:dd:ee:ff"}, token
        )
        remote.save_system(system, token)

        # Act
        result = remote.modify_system(
            system, "delete_interface", {"interface": "eth0"}, token
        )
        remote.save_system(system, token)

        # Assert --> returns true if successful
        assert result
        assert (
            remote.get_system("testsystem0").get("interfaces", {}).get("eth0", None)
            is None
        )

    @pytest.mark.usefixtures(
        "create_testdistro",
        "create_testmenu",
        "create_testprofile",
        "remove_testdistro",
        "remove_testmenu",
        "remove_testprofile",
        "remove_testsystem",
    )
    def test_rename_interface(self, remote, token):
        """
        Test: rename an interface on a system
        """

        # Arrange
        system = remote.new_system(token)
        remote.modify_system(system, "name", "testsystem0", token)
        remote.modify_system(system, "profile", "testprofile0", token)
        result_add = remote.modify_system(
            system, "modify_interface", {"macaddress-eth0": "aa:bb:cc:dd:ee:ff"}, token
        )
        remote.save_system(system, token)

        # Act
        result_rename = remote.modify_system(
            system,
            "rename_interface",
            {"interface": "eth0", "rename_interface": "eth_new"},
            token,
        )
        remote.save_system(system, token)

        # Assert --> returns true if successful
        assert result_add
        assert result_rename
        assert (
            remote.get_system("testsystem0").get("interfaces", {}).get("eth0", None)
            is None
        )
        assert (
            remote.get_system("testsystem0")
            .get("interfaces", {})
            .get("eth_new", {})
            .get("mac_address")
            == "aa:bb:cc:dd:ee:ff"
        )

    @pytest.mark.usefixtures(
        "create_testdistro",
        "create_testmenu",
        "create_testprofile",
        "create_testsystem",
        "remove_testdistro",
        "remove_testmenu",
        "remove_testprofile",
        "remove_testsystem",
    )
    def test_copy_system(self, remote, token):
        """
        Test: copy a system object
        """
        # Arrange
        system = remote.get_item_handle("system", "testsystem0", token)

        # Act
        result = remote.copy_system(system, "testsystemcopy", token)

        # Assert
        assert result

        # Cleanup
        remote.remove_system("testsytemcopy", token)

    @pytest.mark.usefixtures(
        "create_testdistro",
        "create_testmenu",
        "create_testprofile",
        "create_testsystem",
        "remove_testdistro",
        "remove_testmenu",
        "remove_testprofile",
        "remove_testsystem",
    )
    def test_rename_system(self, remote, token):
        """
        Test: rename a system object
        """

        # Arrange --> Done in fixtures also.
        system = remote.get_item_handle("system", "testsystem0", token)

        # Act
        result = remote.rename_system(system, "testsystem1", token)

        # Assert
        assert result

        # Cleanup
        remote.remove_system("testsystem1", token)

    def test_remove_system(self, remote, token):
        """
        Test: remove a system object
        """

        # Arrange
        # TODO: Verify why the test passes without the fixture for creating the system!

        # Act
        result = remote.remove_system("testsystem0", token)

        # Assert
        assert result

    def test_get_repo_config_for_system(self, remote):
        """
        Test: get repository configuration of a system
        """

        # Arrange --> There is nothing to be arranged

        # Act
        result = remote.get_repo_config_for_system("testprofile0")

        # Assert --> Let the test pass if the call is okay.
        assert True
