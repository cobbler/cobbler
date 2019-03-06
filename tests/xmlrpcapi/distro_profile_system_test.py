import os

import pytest

FAKE_INITRD = "initrd1.img"
FAKE_INITRD2 = "initrd2.img"
FAKE_INITRD3 = "initrd3.img"
FAKE_KERNEL = "vmlinuz1"
FAKE_KERNEL2 = "vmlinuz2"
FAKE_KERNEL3 = "vmlinuz3"
TEST_POWER_MANAGEMENT = True
TEST_SYSTEM = ""
cleanup_dirs = []

"""
Order is currently important:
self._get_distros()
self._create_distro()
self._get_distro()
self._find_distro()
self._copy_distro()
self._rename_distro()

self._get_profiles()
self._create_profile()
self._create_subprofile()
self._get_profile()
self._find_profile()
self._copy_profile()
self._rename_profile()
self._get_repo_config_for_profile()

self._get_systems()
self._create_system()
self._get_system()
self._find_system()
self._copy_system()
self._rename_system()
self._get_repo_config_for_system()

self._remove_system()
self._remove_profile()
self._remove_distro()
"""


@pytest.fixture(scope="class")
def distro_fields(fk_initrd, fk_kernel):
    """

    :param fk_initrd:
    :param fk_kernel:
    :return:
    """
    return [
        # field format: field_name, good value(s), bad value(s)
        # field order is the order in which they will be set
        # TODO: include fields with dependencies: fetchable files, boot files, etc.
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

    :param redhat_autoinstall:
    :param suse_autoyast:
    :param ubuntu_preseed:
    :return:
    """
    return [
        # field format: field_name, good value(s), bad value(s)
        # TODO: include fields with dependencies: fetchable files, boot files,
        #         template files, repos
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

    :param redhat_autoinstall:
    :param suse_autoyast:
    :param ubuntu_preseed:
    :return:
    """
    return [
        # field format: field_name, good value(s), bad value(s)
        # TODO: include fields with dependencies: fetchable files, boot files,
        #         template files, images
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
        ["power_type", ["lpar"], ["bla"]],
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
def redhat_autoinstall(topdir):
    """
    The path to the test.ks file for redhat autoinstall.
    :param topdir: See the corresponding fixture.
    :return: A path as a string.
    """
    return os.path.join("", "test.ks")


@pytest.fixture(scope="class")
def suse_autoyast(topdir):
    """
    The path to the suse autoyast xml-file.
    :param topdir: See the corresponding fixture.
    :return: A path as a string.
    """
    return os.path.join("", "test.xml")


@pytest.fixture(scope="class")
def ubuntu_preseed(topdir):
    """
    The path to the ubuntu preseed file.
    :param topdir: See the corresponding fixture.
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
def init_teardown(files_create, fake_files):
    """
    This represents the init and teardown of the TestDistroProfileSystem class.
    :param files_create: See the corresponding fixture.
    :param fake_files: See the corresponding fixture.
    """
    yield

    for fn in fake_files:
        os.remove(fn)


@pytest.fixture()
def create_profile(remote, token, create_testdistro):
    """
    Create a profile with the name "testprofile0"
    :param create_testdistro: See the corresponding fixture.
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    profile = remote.new_profile(token)
    remote.modify_profile(profile, "name", "testprofile0", token)
    remote.modify_profile(profile, "distro", "testdistro0", token)
    remote.modify_profile(profile, "kernel_options", "a=1 b=2 c=3 c=4 c=5 d e", token)
    remote.save_profile(profile, token)


@pytest.fixture()
def remove_testprofile(init_teardown, remote, token):
    yield
    remote.remove_profile("testprofile0", token)


@pytest.fixture
def remove_testdistro(init_teardown, remote, token):
    """
    Removes the distro "testdistro0" from the running cobbler after the test.
    """
    yield
    remote.remove_distro("testdistro0", token)


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


@pytest.mark.usefixtures("cobbler_xmlrpc_base")
class TestDistroProfileSystem:
    """
    Test remote calls related to distros, profiles and systems
    These item types are tested together because they have inter-dependencies
    """

    @pytest.mark.usefixtures("init_teardown")
    def test_get_distros(self, remote, token):
        """
        Test: get distros
        """

        # Arrange --> Nothing to arrange

        # Act
        result = remote.get_distros(token)

        # Assert
        assert result == []

    @pytest.mark.usefixtures("init_teardown")
    def test_get_profiles(self, remote, token):
        """
        Test: get profiles
        """

        # Arrange --> Nothing to arrange

        # Act
        result = remote.get_profiles(token)

        # Assert
        assert result == []

    @pytest.mark.usefixtures("init_teardown")
    def test_get_systems(self, remote, token):
        """
        Test: get systems
        """

        # Arrange --> Nothing to arrange

        # Act
        result = remote.get_systems(token)

        # Assert
        assert result == []

    @pytest.mark.usefixtures("init_teardown", "remove_testdistro")
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

        # FIXME: if field in item_<type>.FIELDS defines possible values,
        # test all of them. This is valid for all item types
        # for field in item_system.FIELDS:
        #    (fname,def1,def2,display,editable,tooltip,values,type) = field
        #    if fname not in ["name","distro","parent"] and editable:
        #        if values and isinstance(values,list):
        #            fvalue = random.choice(values)
        #        else:
        #             fvalue = "testing_" + fname
        #        self.assertTrue(remote.modify_profile(subprofile,fname,fvalue,token))

    @pytest.mark.usefixtures("init_teardown", "remove_testdistro")
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

        # FIXME: if field in item_<type>.FIELDS defines possible values,
        # test all of them. This is valid for all item types
        # for field in item_system.FIELDS:
        #    (fname,def1,def2,display,editable,tooltip,values,type) = field
        #    if fname not in ["name","distro","parent"] and editable:
        #        if values and isinstance(values,list):
        #            fvalue = random.choice(values)
        #        else:
        #             fvalue = "testing_" + fname
        #        self.assertTrue(remote.modify_profile(subprofile,fname,fvalue,token))

    @pytest.mark.usefixtures("init_teardown", "create_testdistro", "remove_testdistro")
    def test_create_profile(self, remote, token, profile_fields):
        """
        Test: create/edit a profile object
        """

        # Arrange
        profiles = remote.get_profiles(token)
        profile = remote.new_profile(token)

        # Act
        for field in profile_fields:
            (fname, fgood, fbad) = field
            for fb in fbad:
                try:
                    remote.modify_profile(profile, fname, fb, token)
                except:
                    pass
                else:
                    pytest.fail("bad field (%s=%s) did not raise an exception" % (fname, fb))
            for fg in fgood:
                try:
                    assert remote.modify_profile(profile, fname, fg, token)
                except Exception as e:
                    pytest.fail("good field (%s=%s) raised exception: %s" % (fname, fg, str(e)))

        assert remote.save_profile(profile, token)

        # Assert
        new_profiles = remote.get_profiles(token)
        assert len(new_profiles) == len(profiles) + 1

    @pytest.mark.usefixtures("init_teardown", "create_profile")
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

    @pytest.mark.usefixtures("init_teardown", "create_profile", "remove_testdistro")
    def test_create_system(self, system_fields, remote, token):
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
            (fname, fgood, fbad) = field
            for fb in fbad:
                try:
                    remote.modify_system(system, fname, fb, token)
                except:
                    pass
                else:
                    pytest.fail("bad field (%s=%s) did not raise an exception" % (fname, fb))
            for fg in fgood:
                try:
                    assert remote.modify_system(system, fname, fg, token)
                except Exception as e:
                    pytest.fail("good field (%s=%s) raised exception: %s" % (fname, fg, str(e)))

        assert remote.save_system(system, token)

        new_systems = remote.get_systems(token)
        assert len(new_systems) == len(systems) + 1
        assert 0

    @pytest.mark.usefixtures("init_teardown", "create_testdistro", "remove_testdistro")
    def test_get_distro(self, remote, fk_initrd, fk_kernel):
        """
        Test: get a distro object"""

        # Arrange --> Done in fixture

        # Act
        distro = remote.get_distro("testdistro0")

        # Assert
        assert distro.name == "testdistro0"
        assert distro.initrd == fk_initrd
        assert distro.kernel == fk_kernel

    @pytest.mark.usefixtures("init_teardown", "create_profile", "remove_testprofile")
    def test_get_profile(self, remote):
        """
        Test: get a profile object
        """

        # Arrange --> Done in fixture.

        # Act
        profile = remote.get_profile("testprofile0")

        # Assert
        assert profile.name == "testprofile0"
        assert profile.distro == "testdistro0"
        assert profile.kernel_options == "a=1 b=2 c=3 c=4 c=5 d e"

    @pytest.mark.usefixtures("init_teardown")
    def test_get_system(self, remote):
        """
        Test: get a system object
        """

        # TODO: Arrange

        # Act
        system = remote.get_system("testsystem0")

        # TODO: Assert
        assert 0

    @pytest.mark.usefixtures("init_teardown")
    def test_find_distro(self, remote, token):
        """
        Test: find a distro object
        """

        # TODO: Arrange

        # Act
        result = remote.find_distro({"name": "testdistro0"}, token)

        # TODO: Assert
        assert result

    @pytest.mark.usefixtures("init_teardown")
    def test_find_profile(self, remote, token):
        """
        Test: find a profile object
        """

        # TODO: Arrange

        # Act
        result = remote.find_profile({"name": "testprofile0"}, token)

        # TODO: Assert
        assert result

    @pytest.mark.usefixtures("init_teardown")
    def test_find_system(self, remote, token):
        """
        Test: find a system object
        """

        # TODO: Arrange

        # Act
        result = remote.find_system({"name": "testsystem0"}, token)

        # TODO: Assert
        assert result

    @pytest.mark.usefixtures("init_teardown")
    def test_copy_distro(self, remote, token):
        """
        Test: copy a distro object
        """

        # TODO: Arrange

        # Act
        distro = remote.get_item_handle("distro", "testdistro0", token)

        # TODO: Assert
        assert remote.copy_distro(distro, "testdistrocopy", token)

    @pytest.mark.usefixtures("init_teardown")
    def test_copy_profile(self, remote, token):
        """
        Test: copy a profile object
        """

        # TODO: Arrange

        # Act
        profile = remote.get_item_handle("profile", "testprofile0", token)

        # TODO: Assert
        assert remote.copy_profile(profile, "testprofilecopy", token)

    @pytest.mark.usefixtures("init_teardown")
    def test_copy_system(self, remote, token):
        """
        Test: copy a system object
        """

        # TODO: Arrange

        # Act
        system = remote.get_item_handle("system", "testsystem0", token)

        # TODO: Assert
        assert remote.copy_system(system, "testsystemcopy", token)

    @pytest.mark.usefixtures("init_teardown")
    def test_rename_distro(self, remote, token):
        """
        Test: rename a distro object
        """

        # TODO: Arrange
        distro = remote.get_item_handle("distro", "testdistrocopy", token)

        # Act
        result = remote.rename_distro(distro, "testdistro1", token)

        # TODO: Assert
        assert result

    @pytest.mark.usefixtures("init_teardown")
    def test_rename_profile(self, remote, token):
        """
        Test: rename a profile object
        """

        # TODO: Arrange
        profile = remote.get_item_handle("profile", "testprofilecopy", token)

        # Act
        result = remote.rename_profile(profile, "testprofile1", token)

        # TODO: Assert
        assert result

    @pytest.mark.usefixtures("init_teardown")
    def test_rename_system(self, remote, token):
        """
        Test: rename a system object
        """

        # TODO: Arrange
        # Create System
        # Get Object-ID
        system = remote.get_item_handle("system", "testsystemcopy", token)

        # Act
        result = remote.rename_system(system, "testsystem1", token)

        # TODO: Assert
        assert result

    @pytest.mark.usefixtures("init_teardown")
    def test_remove_distro(self, remote, token):
        """
        Test: remove a distro object
        """

        # TODO: Arrange

        # Act
        result = remote.remove_distro("testdistro0", token)

        # TODO: Assert
        assert result

    @pytest.mark.usefixtures("init_teardown")
    def test_remove_profile(self, remote, token):
        """
        Test: remove a profile object
        """

        # TODO: Arrange

        # Act
        result_subprofile_remove = remote.remove_profile("testsubprofile0", token)
        result_profile_remove = remote.remove_profile("testprofile0", token)

        # TODO: Assert
        assert result_subprofile_remove
        assert result_profile_remove

    @pytest.mark.usefixtures("init_teardown")
    def test_remove_system(self, remote, token):
        """
        Test: remove a system object
        """

        # TODO: Arrange

        # Act
        result = remote.remove_system("testsystem0", token)

        # TODO: Assert
        assert result

    @pytest.mark.usefixtures("init_teardown")
    def test_get_repo_config_for_profile(self, remote):
        """
        Test: get repository configuration of a profile
        """

        # Arrange --> There is nothing to be arranged

        # Act
        result = remote.get_repo_config_for_profile("testprofile0")

        # Assert --> Let the test pass if the call is okay.
        assert True

    @pytest.mark.usefixtures("init_teardown")
    def test_get_repo_config_for_system(self, remote):
        """
        Test: get repository configuration of a system
        """

        # Arrange --> There is nothing to be arranged

        # Act
        result = remote.get_repo_config_for_system("testprofile0")

        # Assert --> Let the test pass if the call is okay.
        assert True
