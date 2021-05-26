import pytest


@pytest.fixture(scope="function")
def system_fields(redhat_autoinstall, suse_autoyast, ubuntu_preseed):
    """
    Field format: field_name, good value(s), bad value(s)

    :param redhat_autoinstall:
    :param suse_autoyast:
    :param ubuntu_preseed:
    :return:
    """
    # TODO: include fields with dependencies: fetchable files, boot files, template files, images
    return [
        ["comment", ["test comment"], []],
        ["enable_ipxe", ["yes", "YES", "1", "0", "no"], []],
        ["kernel_options", ["a=1 b=2 c=3 c=4 c=5 d e"], []],
        ["kernel_options_post", ["a=1 b=2 c=3 c=4 c=5 d e"], []],
        ["autoinstall", [redhat_autoinstall, suse_autoyast, ubuntu_preseed],
         ["/path/to/bad/autoinstall", ]],
        ["autoinstall_meta", ["a=1 b=2 c=3 c=4 c=5 d e", ], []],
        ["mgmt_classes", ["one two three", ], []],
        ["mgmt_parameters", ["<<inherit>>"], ["badyaml"]],  # needs more test cases that are valid yaml
        ["name", ["testsystem0"], []],
        ["netboot_enabled", ["yes", "YES", "1", "0", "no"], []],
        ["owners", ["user1 user2 user3"], []],
        ["profile", ["testprofile0"], ["badprofile", ]],
        ["repos_enabled", [], []],
        ["status", ["development", "testing", "acceptance", "production"], []],
        ["proxy", ["testproxy"], []],
        ["server", ["1.1.1.1"], []],
        ["boot_loaders", ["pxe ipxe grub", ], ["badloader"]],
        ["virt_auto_boot", ["1", "0"], ["yes", "no"]],
        ["virt_cpus", ["<<inherit>>", "1", "2"], ["a"]],
        ["virt_file_size", ["<<inherit>>", "5", "10"], ["a"]],
        ["virt_disk_driver", ["<<inherit>>", "raw", "qcow2", "vmdk"], []],
        ["virt_ram", ["<<inherit>>", "256", "1024"], ["a", ]],
        ["virt_type", ["<<inherit>>", "xenpv", "xenfv", "qemu", "kvm", "vmware", "openvz"], ["bad", ]],
        ["virt_path", ["<<inherit>>", "/path/to/test", ], []],
        ["virt_pxe_boot", ["1", "0"], []],

        # network
        ["gateway", [], []],
        ["hostname", ["test"], []],
        ["ipv6_autoconfiguration", [], []],
        ["ipv6_default_device", [], []],
        ["name_servers", ["9.1.1.3"], []],
        ["name_servers_search", [], []],

        # network - network interface specific
        # TODO: test these fields
        ["bonding_opts-eth0", [], []],
        ["bridge_opts-eth0", [], []],
        ["cnames-eth0", [], []],
        ["dhcp_tag-eth0", [], []],
        ["dns_name-eth0", [], []],
        ["if_gateway-eth0", [], []],
        ["interface_type-eth0", [], []],
        ["interface_master-eth0", [], []],
        ["ip_address-eth0", [], []],
        ["ipv6_address-eth0", [], []],
        ["ipv6_secondaries-eth0", [], []],
        ["ipv6_mtu-eth0", [], []],
        ["ipv6_static_routes-eth0", [], []],
        ["ipv6_default_gateway-eth0", [], []],
        ["mac_address-eth0", [], []],
        ["mtu-eth0", [], []],
        ["management-eth0", [], []],
        ["netmask-eth0", [], []],
        ["static-eth0", [], []],
        ["static_routes-eth0", [], []],
        ["virt_bridge-eth0", [], []],

        # power management
        ["power_type", ["ipmilan"], ["bla"]],
        ["power_address", ["127.0.0.1"], []],
        ["power_id", ["pmachine:lpar1"], []],
        ["power_pass", ["pass"], []],
        ["power_user", ["user"], []]
    ]


@pytest.mark.usefixtures("cobbler_xmlrpc_base")
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

    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "create_testprofile", "remove_testdistro",
                             "remove_testmenu", "remove_testprofile", "remove_testsystem")
    def test_create_system_positive(self, system_fields, remote, token, template_files):
        """
        Test: create/edit a system object
        """

        # Arrange
        systems = remote.get_systems(token)

        # Act
        system = remote.new_system(token)

        # Assert
        assert remote.modify_system(system, "name", "testsystem0", token)
        assert remote.modify_system(system, "profile", "testprofile0", token)
        for field in system_fields:
            (fname, fgood, _) = field
            for fg in fgood:
                try:
                    assert remote.modify_system(system, fname, fg, token)
                except Exception as e:
                    pytest.fail("good field (%s=%s) raised exception: %s" % (fname, fg, str(e)))

        assert remote.save_system(system, token)

        new_systems = remote.get_systems(token)
        assert len(new_systems) == len(systems) + 1

    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "create_testprofile", "remove_testdistro",
                             "remove_testmenu", "remove_testprofile", "remove_testsystem")
    def test_create_system_negative(self, system_fields, remote, token):
        """
        Test: create/edit a system object
        """

        # Arrange
        systems = remote.get_systems(token)

        # Act
        system = remote.new_system(token)

        # Assert
        assert remote.modify_system(system, "name", "testsystem0", token)
        assert remote.modify_system(system, "profile", "testprofile0", token)
        for field in system_fields:
            (fname, _, fbad) = field
            for fb in fbad:
                try:
                    remote.modify_system(system, fname, fb, token)
                except:
                    pass
                else:
                    pytest.fail("bad field (%s=%s) did not raise an exception" % (fname, fb))

        assert remote.save_system(system, token)

        new_systems = remote.get_systems(token)
        assert len(new_systems) == len(systems) + 1

    def test_find_system(self, remote, token):
        """
        Test: find a system object
        """

        # Arrange --> Nothing to arrange

        # Act
        result = remote.find_system({"name": "notexisting"}, token)

        # Assert --> A not exiting system returns an empty list
        assert result == []

    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "create_testprofile", "create_testsystem",
                             "remove_testdistro",
                             "remove_testmenu", "remove_testprofile", "remove_testsystem")
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

    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "create_testprofile", "create_testsystem",
                             "remove_testdistro",
                             "remove_testmenu", "remove_testprofile", "remove_testsystem")
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
