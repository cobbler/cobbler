import os

import pytest

FAKE_INITRD = "initrd1.img"
FAKE_INITRD2 = "initrd2.img"
FAKE_INITRD3 = "initrd3.img"
FAKE_KERNEL = "vmlinuz1"
FAKE_KERNEL2 = "vmlinuz2"
FAKE_KERNEL3 = "vmlinuz3"


@pytest.fixture(scope="class")
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
    ]


@pytest.fixture(scope="class")
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
        ["enable_gpxe", ["yes", "YES", "1", "0", "no"], []],
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
        ["virt_auto_boot", ["1", "0"], ["yes", "no"]],
        ["virt_bridge", ["<<inherit>>", "br0", "virbr0", "xenbr0"], []],
        ["virt_cpus", ["<<inherit>>", "1", "2"], ["a"]],
        ["virt_disk_driver", ["<<inherit>>", "raw", "qcow2", "vmdk"], []],
        ["virt_file_size", ["<<inherit>>", "5", "10"], ["a"]],
        ["virt_path", ["<<inherit>>", "/path/to/test", ], []],
        ["virt_ram", ["<<inherit>>", "256", "1024"], ["a", ]],
        ["virt_type", ["<<inherit>>", "xenpv", "xenfv", "qemu", "kvm", "vmware", "openvz"], ["bad", ]],
    ]


@pytest.fixture(scope="class")
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
        ["enable_gpxe", ["yes", "YES", "1", "0", "no"], []],
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


@pytest.fixture(scope="class")
def topdir():
    """
    The path to the directory of the fake test files.
    """
    return "/dev/shm/cobbler_test"


@pytest.fixture(scope="class")
def create_tempdir(topdir):
    """
    Creates the top-directory for the tests.
    :param topdir: See the corresponding fixture.
    """
    # Create temp dir
    try:
        os.makedirs(topdir)
    except OSError:
        pass


@pytest.fixture(scope="class")
def fk_initrd(topdir):
    """
    The path to the first fake initrd.
    :param topdir: See the corresponding fixture.
    :return: A path as a string.
    """
    return os.path.join(topdir, FAKE_INITRD)


@pytest.fixture(scope="class")
def fk_initrd2(topdir):
    """
    The path to the second fake initrd.
    :param topdir: See the corresponding fixture.
    :return: A path as a string.
    """
    return os.path.join(topdir, FAKE_INITRD2)


@pytest.fixture(scope="class")
def fk_initrd3(topdir):
    """
    The path to the third fake initrd.
    :param topdir: See the corresponding fixture.
    :return: A path as a string.
    """
    return os.path.join(topdir, FAKE_INITRD3)


@pytest.fixture(scope="class")
def fk_kernel(topdir):
    """
    The path to the first fake kernel.
    :param topdir: See the corresponding fixture.
    :return: A path as a string.
    """
    return os.path.join(topdir, FAKE_KERNEL)


@pytest.fixture(scope="class")
def fk_kernel2(topdir):
    """
    The path to the second fake kernel.
    :param topdir: See the corresponding fixture.
    :return: A path as a string.
    """
    return os.path.join(topdir, FAKE_KERNEL2)


@pytest.fixture(scope="class")
def fk_kernel3(topdir):
    """
    The path to the third fake kernel.
    :param topdir: See the corresponding fixture.
    :return: A path as a string.
    """
    return os.path.join(topdir, FAKE_KERNEL3)


@pytest.fixture(scope="class")
def redhat_autoinstall():
    """
    The path to the test.ks file for redhat autoinstall.
    :return: A path as a string.
    """
    return os.path.join("", "test.ks")


@pytest.fixture(scope="class")
def suse_autoyast():
    """
    The path to the suse autoyast xml-file.
    :return: A path as a string.
    """
    return os.path.join("", "test.xml")


@pytest.fixture(scope="class")
def ubuntu_preseed():
    """
    The path to the ubuntu preseed file.
    :return: A path as a string.
    """
    return os.path.join("", "test.seed")


@pytest.fixture(scope="class")
def fake_files(fk_initrd, fk_initrd2, fk_initrd3, fk_kernel, fk_kernel2, fk_kernel3, redhat_autoinstall, suse_autoyast,
               ubuntu_preseed):
    """
    This fixture has an array of all the paths to the generated fake files.
    :param fk_initrd: See the corresponding fixture.
    :param fk_initrd2: See the corresponding fixture.
    :param fk_initrd3: See the corresponding fixture.
    :param fk_kernel: See the corresponding fixture.
    :param fk_kernel2: See the corresponding fixture.
    :param fk_kernel3: See the corresponding fixture.
    :param redhat_autoinstall: See the corresponding fixture.
    :param suse_autoyast: See the corresponding fixture.
    :param ubuntu_preseed: See the corresponding fixture.
    :return: An array which contains all paths to the corresponding fake files.
    """
    return [fk_initrd, fk_initrd2, fk_initrd3, fk_kernel, fk_kernel2, fk_kernel3, redhat_autoinstall,
            suse_autoyast, ubuntu_preseed]


@pytest.fixture(scope="class")
def files_create(create_tempdir, fake_files, redhat_autoinstall, suse_autoyast, ubuntu_preseed):
    """
    This creates all the fake files which need to be present for the tests.
    :param ubuntu_preseed: See the corresponding fixture.
    :param suse_autoyast: See the corresponding fixture.
    :param redhat_autoinstall: See the corresponding fixture.
    :param create_tempdir: See the corresponding fixture.
    :param fake_files: See the corresponding fixture.
    """
    base = "/var/lib/cobbler/templates/"
    f = open(base + redhat_autoinstall, "w+")
    f.close()
    f = open(base + suse_autoyast, "w+")
    f.close()
    f = open(base + ubuntu_preseed, "w+")
    f.close()

    for fn in fake_files:
        f = open(fn, "w+")
        f.close()


@pytest.fixture(scope="class")
def remove_fakefiles(files_create, fake_files, redhat_autoinstall, suse_autoyast, ubuntu_preseed):
    """
    This represents the init and teardown of the TestDistroProfileSystem class.
    :param ubuntu_preseed: See the corresponding fixture.
    :param suse_autoyast: See the corresponding fixture.
    :param redhat_autoinstall: See the corresponding fixture.
    :param files_create: See the corresponding fixture.
    :param fake_files: See the corresponding fixture.
    """
    yield

    base = "/var/lib/cobbler/templates/"
    os.remove(base + redhat_autoinstall)
    os.remove(base + suse_autoyast)
    os.remove(base + ubuntu_preseed)
    for fn in fake_files:
        os.remove(fn)


@pytest.fixture()
def create_profile(remote, token):
    """
    Create a profile with the name "testprofile0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    profile = remote.new_profile(token)
    remote.modify_profile(profile, "name", "testprofile0", token)
    remote.modify_profile(profile, "distro", "testdistro0", token)
    remote.modify_profile(profile, "kernel_options", "a=1 b=2 c=3 c=4 c=5 d e", token)
    remote.save_profile(profile, token)


@pytest.fixture()
def remove_testprofile(remote, token):
    """
    Removes the profile with the name "testprofile0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_profile("testprofile0", token)


@pytest.fixture()
def remove_testdistro(remote, token):
    """
    Removes the distro "testdistro0" from the running cobbler after the test.
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_distro("testdistro0", token, False)


@pytest.fixture()
def create_testdistro(remote, token, fk_kernel, fk_initrd):
    """
    Creates a distro "testdistro0" with the architecture "x86_64", breed "suse" and the fixtures which are setting the
    fake kernel and initrd.
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    :param fk_kernel: See the corresponding fixture.
    :param fk_initrd: See the corresponding fixture.
    """
    distro = remote.new_distro(token)
    remote.modify_distro(distro, "name", "testdistro0", token)
    remote.modify_distro(distro, "arch", "x86_64", token)
    remote.modify_distro(distro, "breed", "suse", token)
    remote.modify_distro(distro, "kernel", fk_kernel, token)
    remote.modify_distro(distro, "initrd", fk_initrd, token)
    remote.save_distro(distro, token)


@pytest.fixture()
def create_testsystem(remote, token):
    """
    Add a system with the name "testsystem0", the system is assigend to the profile "testprofile0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    system = remote.new_system(token)
    remote.modify_system(system, "name", "testsystem0", token)
    remote.modify_system(system, "profile", "testprofile0", token)
    remote.save_system(system, token)


@pytest.fixture()
def remove_testsystem(remote, token):
    """
    Remove a system "testsystem0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_system("testsystem0", token, False)


@pytest.fixture()
def create_testrepo(remote, token):
    """
    Create a testrepository with the name "testrepo0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    repo = remote.new_repo(token)
    remote.modify_repo(repo, "name", "testrepo0", token)
    remote.modify_repo(repo, "arch", "x86_64", token)
    remote.modify_repo(repo, "mirror", "http://something", token)
    remote.save_repo(repo, token)
    remote.background_sync([], token)


@pytest.fixture()
def remove_testrepo(remote, token):
    """
    Remove a repo "testrepo0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_repo("testrepo0", token, False)


@pytest.fixture()
def create_testimage(remote, token):
    """
    Create a testrepository with the name "testimage0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    image = remote.new_image(token)
    remote.modify_image(image, "name", "testimage0", token)
    remote.save_image(image, token)
    remote.background_sync([], token)


@pytest.fixture()
def remove_testimage(remote, token):
    """
    Remove the image "testimage0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_image("testimage0", token, False)


@pytest.fixture()
def create_testpackage(remote, token):
    """
    Create a testpackage with the name "testpackage0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    package = remote.new_package(token)
    remote.modify_package(package, "name", "testpackage0", token)
    remote.save_package(package, token)
    remote.background_sync([], token)


@pytest.fixture()
def remove_testpackage(remote, token):
    """
    Remove a package "testpackage0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """

    yield
    remote.remove_package("testpackage0", token, False)


@pytest.fixture()
def create_testfile(remote, token):
    """
    Create a testfile with the name "testfile0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """

    mfile = remote.new_file(token)
    remote.modify_file(mfile, "name", "testfile0", token)
    remote.modify_file(mfile, "path", "/dev/shm/", token)
    remote.modify_file(mfile, "group", "root", token)
    remote.modify_file(mfile, "owner", "root", token)
    remote.modify_file(mfile, "mode", "0600", token)
    remote.modify_file(mfile, "is_dir", "True", token)
    remote.save_file(mfile, token)
    remote.background_sync([], token)


@pytest.fixture()
def remove_testfile(remote, token):
    """
    Remove a file "testfile0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_file("testfile0", token, False)


@pytest.fixture()
def create_mgmtclass(remote, token):
    """
    Create a mgmtclass with the name "mgmtclass0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """

    mgmtclass0 = remote.new_mgmtclass(token)
    remote.modify_mgmtclass(mgmtclass0, "name", "mgmtclass0", token)
    remote.save_mgmtclass(mgmtclass0, token)
    remote.background_sync([], token)


@pytest.fixture()
def remove_mgmtclass(remote, token):
    """
    Remove a mgmtclass "mgmtclass0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_mgmtclass("mgmtclass0", token, False)


@pytest.mark.usefixtures("cobbler_xmlrpc_base", "remove_fakefiles")
class TestDistroProfileSystem:
    """
    Test remote calls related to distros, profiles and systems
    These item types are tested together because they have inter-dependencies
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

    def test_get_profiles(self, remote, token):
        """
        Test: get profiles
        """
        # Arrange --> Nothing to arrange

        # Act
        result = remote.get_profiles(token)

        # Assert
        assert result == []

    def test_get_systems(self, remote, token):
        """
        Test: get systems
        """
        # Arrange --> Nothing to arrange

        # Act
        result = remote.get_systems(token)

        # Assert
        assert result == []

    @pytest.mark.usefixtures("remove_testdistro")
    def test_create_distro_positive(self, remote, token, distro_fields):
        """
        Test: create/edit a distro with valid values
        """
        # Arrange --> Nothing to do.

        # Act
        distro = remote.new_distro(token)
        remote.modify_distro(distro, "name", "testdistro", token)

        # Assert
        for field in distro_fields:
            (fname, fgood, fbad) = field
            for fg in fgood:
                try:
                    result = remote.modify_distro(distro, fname, fg, token)
                    assert result
                except Exception as e:
                    pytest.fail("good field (%s=%s) raised exception: %s" % (fname, fg, str(e)))

        result_save_success = remote.save_distro(distro, token)
        assert result_save_success

        # FIXME: if field in item_<type>.FIELDS defines possible values, test all of them. This is valid for all item
        #  types
        # for field in item_system.FIELDS:
        #    (fname,def1,def2,display,editable,tooltip,values,type) = field
        #    if fname not in ["name","distro","parent"] and editable:
        #        if values and isinstance(values,list):
        #            fvalue = random.choice(values)
        #        else:
        #             fvalue = "testing_" + fname
        #        self.assertTrue(remote.modify_profile(subprofile,fname,fvalue,token))

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
            (fname, fgood, fbad) = field
            for fb in fbad:
                try:
                    remote.modify_distro(distro, fname, fb, token)
                except:
                    pass
                else:
                    pytest.fail("bad field (%s=%s) did not raise an exception" % (fname, fb))

        remote.modify_distro(distro, "kernel", fk_kernel, token)
        remote.modify_distro(distro, "initrd", fk_initrd, token)
        result_save_success = remote.save_distro(distro, token)
        assert result_save_success

        # FIXME: if field in item_<type>.FIELDS defines possible values, test all of them. This is valid for all item
        #  types
        # for field in item_system.FIELDS:
        #    (fname,def1,def2,display,editable,tooltip,values,type) = field
        #    if fname not in ["name","distro","parent"] and editable:
        #        if values and isinstance(values,list):
        #            fvalue = random.choice(values)
        #        else:
        #             fvalue = "testing_" + fname
        #        self.assertTrue(remote.modify_profile(subprofile,fname,fvalue,token))

    @pytest.mark.usefixtures("create_testdistro", "remove_testdistro", "remove_testprofile")
    def test_create_profile_positive(self, remote, token, profile_fields):
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

    @pytest.mark.usefixtures("create_testdistro", "remove_testdistro", "remove_testprofile")
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
        remote.modify_profile(profile, "name", "testprofile0", token)
        assert remote.save_profile(profile, token)

        # Assert
        new_profiles = remote.get_profiles(token)
        assert len(new_profiles) == 1

    @pytest.mark.usefixtures("create_testdistro", "create_profile", "remove_testdistro", "remove_testprofile")
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

    @pytest.mark.usefixtures("create_testdistro", "create_profile", "remove_testdistro", "remove_testprofile",
                             "remove_testsystem")
    def test_create_system_positive(self, system_fields, remote, token):
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

    @pytest.mark.usefixtures("create_testdistro", "create_profile", "remove_testdistro", "remove_testprofile",
                             "remove_testsystem")
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
        assert distro.get("initrd") == fk_initrd
        assert distro.get("kernel") == fk_kernel

    @pytest.mark.usefixtures("create_testdistro", "create_profile", "remove_testdistro", "remove_testprofile")
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
        assert profile.get("kernel_options") == {'a': '1', 'b': '2', 'c': ['3', '4', '5'], 'd': '~', 'e': '~'}

    def test_get_system(self, remote):
        """
        Test: get a system object
        """

        # Arrange --> There should be no system present. --> Nothing to Init.

        # Act
        system = remote.get_system("testsystem0")

        # Assert
        assert system is "~"

    @pytest.mark.usefixtures("create_testdistro", "create_profile", "create_testsystem", "remove_testdistro",
                             "remove_testprofile", "remove_testsystem")
    def test_get_systems_koan(self, remote):
        # Arrange

        # Act
        systems = remote.get_systems()

        # Assert
        # TODO Test more attributes
        for system in systems:
            if "autoinstall_meta" in system:
                assert "ks_meta" in system
                assert system.get("ks_meta") == system.get("autoinstall_meta")
            if "autoinstall" in system:
                assert "kickstart" in system
                assert system.get("kickstart") == system.get("autoinstall")
                
    @pytest.mark.usefixtures("create_testdistro", "create_profile", "create_testsystem", "remove_testdistro",
                             "remove_testprofile", "remove_testsystem")
    def test_get_system_for_koan(self, remote):
        # Arrange

        # Act
        system = remote.get_system_for_koan("testsystem0")

        # Assert
        assert "ks_meta" in system
        assert "kickstart" in system

    @pytest.mark.usefixtures("create_testdistro", "create_profile", "remove_testdistro", "remove_testprofile")
    def test_get_profile_for_koan(self, remote):
        # Arrange

        # Act
        profile = remote.get_profile_for_koan("testprofile0")

        # Assert
        assert "ks_meta" in profile
        assert "kickstart" in profile

    @pytest.mark.usefixtures("create_testdistro", "remove_testdistro")
    def test_get_distro_for_koan(self, remote):
        # Arrange

        # Act
        distro = remote.get_distro_for_koan("testdistro0")

        # Assert
        assert "ks_meta" in distro
        assert "kickstart" not in distro

    @pytest.mark.usefixtures("create_testrepo", "remove_testrepo")
    def test_get_repo_for_koan(self, remote):
        # Arrange

        # Act
        repo = remote.get_repo_for_koan("testrepo0")

        # Assert
        assert "ks_meta" not in repo
        assert "kickstart" not in repo

    @pytest.mark.usefixtures("create_testimage", "remove_testimage")
    def test_get_image_for_koan(self, remote):
        # Arrange

        # Act
        image = remote.get_image_for_koan("testimage0")

        # Assert
        assert "ks_meta" not in image
        assert "kickstart" in image

    @pytest.mark.usefixtures("create_mgmtclass", "remove_mgmtclass")
    def test_get_mgmtclass_for_koan(self, remote):
        # Arrange

        # Act
        mgmt_class = remote.get_mgmtclass_for_koan("mgmtclass0")

        # Assert
        assert "ks_meta" not in mgmt_class
        assert "kickstart" not in mgmt_class

    @pytest.mark.usefixtures("create_testpackage", "remove_testpackage")
    def test_get_package_for_koan(self, remote):
        # Arrange

        # Act
        package = remote.get_package_for_koan("package0")

        # Assert
        assert "ks_meta" not in package
        assert "kickstart" not in package

    @pytest.mark.usefixtures("create_testfile", "remove_testfile")
    def test_get_file_for_koan(self, remote):
        # Arrange

        # Act
        file = remote.get_file_for_koan("file0")

        # Assert
        assert "ks_meta" not in file
        assert "kickstart" not in file

    def test_find_distro(self, remote, token):
        """
        Test: find a distro object
        """

        # Arrange --> No distros means no setup

        # Act
        result = remote.find_distro({"name": "testdistro0"}, token)

        # Assert
        assert result == []

    @pytest.mark.usefixtures("create_testdistro", "create_profile", "remove_testdistro", "remove_testprofile")
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

    def test_find_system(self, remote, token):
        """
        Test: find a system object
        """

        # Arrange --> Nothing to arrange

        # Act
        result = remote.find_system({"name": "notexisting"}, token)

        # Assert --> A not exiting system returns an empty list
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

    @pytest.mark.usefixtures("create_testdistro", "create_profile", "remove_testdistro", "remove_testprofile")
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

    @pytest.mark.usefixtures("create_testdistro", "create_profile", "create_testsystem", "remove_testdistro",
                             "remove_testprofile", "remove_testsystem")
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

    @pytest.mark.usefixtures("create_testdistro", "create_profile", "remove_testprofile", "remove_testdistro")
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

    @pytest.mark.usefixtures("create_testdistro", "create_profile", "create_testsystem", "remove_testdistro",
                             "remove_testprofile", "remove_testsystem")
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

    def test_get_repo_config_for_profile(self, remote):
        """
        Test: get repository configuration of a profile
        """

        # Arrange --> There is nothing to be arranged

        # Act
        result = remote.get_repo_config_for_profile("testprofile0")

        # Assert --> Let the test pass if the call is okay.
        assert True

    def test_get_repo_config_for_system(self, remote):
        """
        Test: get repository configuration of a system
        """

        # Arrange --> There is nothing to be arranged

        # Act
        result = remote.get_repo_config_for_system("testprofile0")

        # Assert --> Let the test pass if the call is okay.
        assert True

    @pytest.mark.usefixtures("create_testdistro", "create_profile", "remove_testdistro", "remove_testprofile")
    def test_render_vars(self, remote, token):
        """
        Test: string replacements for @@xyz@@
        """

        # Arrange --> There is nothing to be arranged
        kernel_options = "tree=http://@@http_server@@/cblr/links/@@distro_name@@"

        # Act
        distro = remote.get_item_handle("distro", "testdistro0", token)
        remote.modify_distro(distro, "kernel_options", kernel_options, token)
        remote.save_distro(distro, token)

        # Assert --> Let the test pass if the call is okay.
        assert True
