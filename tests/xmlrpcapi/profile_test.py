import pytest


@pytest.fixture(scope="function")
def profile_fields(redhat_autoinstall, suse_autoyast, ubuntu_preseed):
    """
    Field format: field_name, good value(s), bad value(s)

    :param redhat_autoinstall:
    :param suse_autoyast:
    :param ubuntu_preseed:
    :return:
    """
    # TODO: include fields with dependencies: fetchable files, boot files, template files, repos
    return [
        ["comment", ["test comment"], []],
        ["dhcp_tag", ["", "foo"], []],
        ["distro", ["testdistro0"], ["baddistro", ]],
        ["enable_ipxe", ["yes", "YES", "1", "0", "no"], []],
        ["enable_menu", ["yes", "YES", "1", "0", "no"], []],
        ["kernel_options", ["a=1 b=2 c=3 c=4 c=5 d e"], []],
        ["kernel_options_post", ["a=1 b=2 c=3 c=4 c=5 d e"], []],
        ["autoinstall", [redhat_autoinstall, suse_autoyast, ubuntu_preseed],
         ["/path/to/bad/autoinstall", ]],
        ["autoinstall_meta", ["a=1 b=2 c=3 c=4 c=5 d e", ], []],
        ["mgmt_classes", ["one two three", ], []],
        ["mgmt_parameters", ["<<inherit>>"], ["badyaml"]],  # needs more test cases that are valid yaml
        ["name", ["testprofile0"], []],
        ["name_servers", ["1.1.1.1 1.1.1.2 1.1.1.3"], []],
        ["name_servers_search", ["example.com foo.bar.com"], []],
        ["owners", ["user1 user2 user3"], []],
        ["proxy", ["testproxy"], []],
        ["server", ["1.1.1.1"], []],
        ["menu", ["testmenu0"], ["badmenu", ]],
        ["virt_auto_boot", ["1", "0"], ["yes", "no"]],
        ["virt_bridge", ["<<inherit>>", "br0", "virbr0", "xenbr0"], []],
        ["virt_cpus", ["<<inherit>>", "1", "2"], ["a"]],
        ["virt_disk_driver", ["<<inherit>>", "raw", "qcow2", "vmdk"], []],
        ["virt_file_size", ["<<inherit>>", "5", "10"], ["a"]],
        ["virt_path", ["<<inherit>>", "/path/to/test", ], []],
        ["virt_ram", ["<<inherit>>", "256", "1024"], ["a", ]],
        ["virt_type", ["<<inherit>>", "xenpv", "xenfv", "qemu", "kvm", "vmware", "openvz"], ["bad", ]],
        ["boot_loaders", ["pxe ipxe grub", ], ["badloader"]],
    ]


@pytest.mark.usefixtures("cobbler_xmlrpc_base")
class TestProfile:
    """
    Test remote calls related to profiles.
    """

    def test_get_profiles(self, remote, token):
        """
        Test: get profiles
        """
        # Arrange --> Nothing to arrange

        # Act
        result = remote.get_profiles(token)

        # Assert
        assert result == []

    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "remove_testdistro", "remove_testmenu",
                             "remove_testprofile")
    def test_create_profile_positive(self, remote, token, profile_fields, template_files):
        """
        Test: create/edit a profile object
        """
        # Arrange
        profile = remote.new_profile(token)

        # Act
        for field in profile_fields:
            (fname, fgood, _) = field
            for fg in fgood:
                try:
                    assert remote.modify_profile(profile, fname, fg, token)
                except Exception as e:
                    pytest.fail("good field (%s=%s) raised exception: %s" % (fname, fg, str(e)))

        remote.modify_profile(profile, "name", "testprofile0", token)
        assert remote.save_profile(profile, token)

        # Assert
        new_profiles = remote.get_profiles(token)
        assert len(new_profiles) == 1

    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "remove_testdistro", "remove_testmenu",
                             "remove_testprofile")
    def test_create_profile_negative(self, remote, token, profile_fields):
        """
        Test: create/edit a profile object
        """
        # Arrange
        profile = remote.new_profile(token)

        # Act
        for field in profile_fields:
            (fname, _, fbad) = field
            for fb in fbad:
                try:
                    remote.modify_profile(profile, fname, fb, token)
                except:
                    pass
                else:
                    pytest.fail("bad field (%s=%s) did not raise an exception" % (fname, fb))

        remote.modify_profile(profile, "distro", "testdistro0", token)
        remote.modify_profile(profile, "menu", "testmenu0", token)
        remote.modify_profile(profile, "name", "testprofile0", token)
        assert remote.save_profile(profile, token)

        # Assert
        new_profiles = remote.get_profiles(token)
        assert len(new_profiles) == 1

    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "create_testprofile", "remove_testdistro",
                             "remove_testmenu", "remove_testprofile")
    def test_create_subprofile(self, remote, token):
        """
        Test: create/edit a subprofile object
        """

        # Arrange
        profiles = remote.get_profiles(token)

        # Act
        subprofile = remote.new_subprofile(token)

        # Assert
        assert remote.modify_profile(subprofile, "name", "testsubprofile0", token)
        assert remote.modify_profile(subprofile, "parent", "testprofile0", token)

        assert remote.save_profile(subprofile, token)

        new_profiles = remote.get_profiles(token)
        assert len(new_profiles) == len(profiles) + 1

    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "create_testprofile", "remove_testdistro",
                             "remove_testmenu", "remove_testprofile")
    def test_get_profile(self, remote):
        """
        Test: get a profile object
        """

        # Arrange --> Done in fixture.

        # Act
        profile = remote.get_profile("testprofile0")

        # Assert
        assert profile.get("name") == "testprofile0"
        assert profile.get("distro") == "testdistro0"
        assert profile.get("menu") == "testmenu0"
        assert profile.get("kernel_options") == {'a': '1', 'b': '2', 'c': ['3', '4', '5'], 'd': '~', 'e': '~'}

    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "create_testprofile", "remove_testdistro",
                             "remove_testmenu", "remove_testprofile")
    def test_find_profile(self, remote, token):
        """
        Test: find a profile object
        """

        # Arrange --> Done in fixtures

        # Act
        result = remote.find_profile({"name": "testprofile0"}, token)

        # Assert
        assert len(result) == 1
        assert result[0].get("name") == "testprofile0"

    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "create_testprofile", "remove_testdistro",
                             "remove_testmenu", "remove_testprofile")
    def test_copy_profile(self, remote, token):
        """
        Test: copy a profile object
        """

        # Arrange --> Done in fixtures

        # Act
        profile = remote.get_item_handle("profile", "testprofile0", token)
        result = remote.copy_profile(profile, "testprofilecopy", token)

        # Assert
        assert result

        # Cleanup
        remote.remove_profile("testprofilecopy", token)

    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "create_testprofile", "remove_testprofile",
                             "remove_testmenu", "remove_testdistro")
    def test_rename_profile(self, remote, token):
        """
        Test: rename a profile object
        """

        # Arrange
        profile = remote.get_item_handle("profile", "testprofile0", token)

        # Act
        result = remote.rename_profile(profile, "testprofile1", token)

        # Assert
        assert result

        # Cleanup
        remote.remove_profile("testprofile1", token)

    def test_remove_profile(self, remote, token):
        """
        Test: remove a profile object
        """

        # Arrange
        # TODO: Verify why the test passes without the fixture for creating the profile!

        # Act
        # TODO: Why does the subprofile call return true? There shouldn't be one.
        result_subprofile_remove = remote.remove_profile("testsubprofile0", token)
        result_profile_remove = remote.remove_profile("testprofile0", token)

        # Assert
        assert result_subprofile_remove
        assert result_profile_remove

    def test_get_repo_config_for_profile(self, remote):
        """
        Test: get repository configuration of a profile
        """

        # Arrange --> There is nothing to be arranged

        # Act
        result = remote.get_repo_config_for_profile("testprofile0")

        # Assert --> Let the test pass if the call is okay.
        assert True
