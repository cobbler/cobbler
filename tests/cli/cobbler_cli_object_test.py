import os

import pytest

dummy_file_path = "/root/dummy"


@pytest.fixture(scope="class")
def setup():
    """
    Initializes testcase
    """
    # create files if necessary
    if not os.path.exists(dummy_file_path):
        open(dummy_file_path, 'w').close()


@pytest.fixture(scope="class")
def teardown():
    """
    Cleans up testcase
    """
    yield
    # remove files
    if os.path.exists(dummy_file_path):
        os.remove(dummy_file_path)


@pytest.fixture(scope="function")
def generate_run_cmd_array():
    def _generate_run_cmd_array(dict_to_convert):
        result_array = []
        for key in dict_to_convert:
            result_array.append("--%s=%s" % (key, dict_to_convert[key]))
        return result_array

    return _generate_run_cmd_array


@pytest.fixture(scope="function")
def add_object_via_cli(run_cmd, generate_run_cmd_array):
    def _add_object_via_cli(object_type, attributes):
        cmd_list = [object_type, "add"]
        options = generate_run_cmd_array(attributes)
        cmd_list.extend(options)
        run_cmd(cmd=cmd_list)

    return _add_object_via_cli


@pytest.fixture(scope="function")
def remove_object_via_cli(run_cmd):
    def _remove_object_via_cli(object_type, name):
        run_cmd(cmd=[object_type, "remove", "--name=%s" % name])

    return _remove_object_via_cli


@pytest.mark.usefixtures("setup", "teardown")
class TestCobblerCliTestObject:
    """
    Test CLI commands on objects
    """

    def test_report(self, run_cmd):
        # Arrange
        expected = """distros:
==========

profiles:
==========

systems:
==========

repos:
==========

images:
==========

mgmtclasses:
==========

packages:
==========

files:
==========

menus:
==========
"""

        # Act
        (outputstd, outputerr) = run_cmd(cmd=["report"])

        # Assert
        assert outputstd == expected

    @pytest.mark.parametrize("object_type", ["distro", "profile", "system", "image", "repo", "package", "mgmtclass",
                                             "file", "menu"])
    def test_report_with_type(self, run_cmd, object_type):
        # Arrange

        # Act
        (outputstd, outputerr) = run_cmd(cmd=[object_type, "report"])

        # Assert
        assert outputstd is None or not outputstd

    @pytest.mark.parametrize("object_type", ["distro", "profile", "system", "image", "repo", "package", "mgmtclass",
                                             "file", "menu"])
    def test_report_with_type_and_name(self, run_cmd, object_type):
        # Arrange
        name = "notexisting"

        # Act
        (outputstd, outputerr) = run_cmd(cmd=[object_type, "report", "--name=%s" % name])

        # Assert
        assert outputstd == "No %s found: %s\n" % (object_type, name)

    @pytest.mark.parametrize("object_type,attributes,to_change,attr_long_name", [
        ("distro",
         {"name": "testdistroedit", "kernel": "Set in method", "initrd": "Set in method", "breed": "suse",
          "arch": "x86_64"},
         ["comment", "Testcomment"], "Comment"),
        ("profile", {"name": "testprofileedit", "distro": "test_distro_edit_profile"},
         ["comment", "Testcomment"], "Comment"),
        ("system", {"name": "test_system_edit", "profile": "test_profile_edit_system"}, ["comment", "Testcomment"],
         "Comment"),
        ("image", {"name": "test_image_edit"}, ["comment", "Testcomment"], "Comment"),
        ("repo", {"name": "testrepoedit", "mirror": "http://localhost"}, ["comment", "Testcomment"], "Comment"),
        ("package", {"name": "testpackageedit"}, ["comment", "Testcomment"], "Comment"),
        ("mgmtclass", {"name": "testmgmtclassedit"}, ["comment", "Testcomment"], "Comment"),
        ("file", {"name": "testfileedit", "path": "/tmp", "owner": "root", "group": "root", "mode": "600",
                  "is-dir": "True"}, ["path", "/test_dir"], "Path"),
        ("menu", {"name": "testmenuedit"}, ["comment", "Testcomment"], "Comment"),
    ])
    def test_edit(self, run_cmd, add_object_via_cli, remove_object_via_cli, create_kernel_initrd, fk_kernel, fk_initrd,
                  object_type, attributes, to_change, attr_long_name):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_kernel)
        name_distro_profile = "test_distro_edit_profile"
        name_distro_system = "test_distro_edit_system"
        name_profile_system = "test_profile_edit_system"
        if object_type == "distro":
            attributes["kernel"] = kernel_path
            attributes["initrd"] = initrd_path
        elif object_type == "profile":
            add_object_via_cli("distro", {"name": name_distro_profile, "kernel": kernel_path, "initrd": initrd_path,
                                          "breed": "suse", "arch": "x86_64"})
        elif object_type == "system":
            add_object_via_cli("distro", {"name": name_distro_system, "kernel": kernel_path, "initrd": initrd_path,
                                          "breed": "suse", "arch": "x86_64"})
            add_object_via_cli("profile", {"name": name_profile_system, "distro": name_distro_system})
        add_object_via_cli(object_type, attributes)

        # Act
        run_cmd(cmd=[object_type, "edit", "--name=%s" % attributes["name"], "--%s='%s'" % (to_change[0], to_change[1])])
        (outputstd, outputerr) = run_cmd(cmd=[object_type, "report", "--name=%s" % attributes["name"]])

        # Cleanup
        remove_object_via_cli(object_type, attributes["name"])
        if object_type == "profile":
            remove_object_via_cli("distro", name_distro_profile)
        elif object_type == "system":
            remove_object_via_cli("profile", name_profile_system)
            remove_object_via_cli("distro", name_distro_system)

        # Assert
        expected = attr_long_name + ":'" + to_change[1] + "'"
        print("Expected: \"" + expected + "\"")
        lines = outputstd.split("\n")
        found = False
        for line in lines:
            line = line.replace(" ", "")
            print("Line: \"" + line + "\"")
            if line == expected:
                found = True
        assert found

    @pytest.mark.parametrize("object_type,attributes", [
        ("distro", {"name": "testdistrofind", "kernel": "Set in method", "initrd": "Set in method", "breed": "suse",
                    "arch": "x86_64"}),
        ("profile", {"name": "testprofilefind", "distro": ""}),
        ("system", {"name": "testsystemfind", "profile": ""}),
        ("image", {"name": "testimagefind"}),
        ("repo", {"name": "testrepofind", "mirror": "http://localhost"}),
        ("package", {"name": "testpackagefind"}),
        ("mgmtclass", {"name": "testmgmtclassfind"}),
        ("file", {"name": "testfilefind", "path": "/tmp", "owner": "root", "group": "root", "mode": "600",
                  "is-dir": "True"}),
        ("menu", {"name": "testmenufind"}),
    ])
    def test_find(self, run_cmd, add_object_via_cli, remove_object_via_cli, create_kernel_initrd, fk_initrd, fk_kernel,
                  object_type, attributes):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_kernel)
        name_distro_profile = "testdistro_find_profile"
        name_distro_system = "testdistro_find_system"
        name_profile_system = "testprofile_find_system"
        if object_type == "distro":
            attributes["kernel"] = kernel_path
            attributes["initrd"] = initrd_path
        elif object_type == "profile":
            attributes["distro"] = name_distro_profile
            add_object_via_cli("distro", {"name": name_distro_profile, "kernel": kernel_path, "initrd": initrd_path,
                                          "breed": "suse", "arch": "x86_64"})
        elif object_type == "system":
            attributes["profile"] = name_profile_system
            add_object_via_cli("distro", {"name": name_distro_system, "kernel": kernel_path, "initrd": initrd_path,
                                          "breed": "suse", "arch": "x86_64"})
            add_object_via_cli("profile", {"name": name_profile_system, "distro": name_distro_system})
        add_object_via_cli(object_type, attributes)

        # Act
        (outputstd, outputerr) = run_cmd(cmd=[object_type, "find", "--name='%s'" % attributes["name"]])

        # Cleanup
        remove_object_via_cli(object_type, attributes["name"])
        if object_type == "profile":
            remove_object_via_cli("distro", name_distro_profile)
        elif object_type == "system":
            remove_object_via_cli("profile", name_profile_system)
            remove_object_via_cli("distro", name_distro_system)

        # Assert
        lines = outputstd.split("\n")
        assert len(lines) >= 1

    @pytest.mark.parametrize("object_type,attributes", [
        ("distro", {"name": "testdistrocopy", "kernel": "Set in method", "initrd": "Set in method", "breed": "suse",
                    "arch": "x86_64"}),
        ("profile", {"name": "testprofilecopy", "distro": "testdistro_copy_profile"}),
        ("system", {"name": "testsystemcopy", "profile": "testprofile_copy_system"}),
        ("image", {"name": "testimagecopy"}),
        ("repo", {"name": "testrepocopy", "mirror": "http://localhost"}),
        ("package", {"name": "testpackagecopy"}),
        ("mgmtclass", {"name": "testmgmtclasscopy"}),
        ("file", {"name": "testfilecopy", "path": "/tmp", "owner": "root", "group": "root", "mode": "600",
                  "is-dir": "True"}),
        ("menu", {"name": "testmenucopy"}),
    ])
    def test_copy(self, run_cmd, add_object_via_cli, remove_object_via_cli, create_kernel_initrd, fk_initrd, fk_kernel,
                  object_type, attributes):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_kernel)
        name_distro_profile = "testdistro_copy_profile"
        name_distro_system = "testdistro_copy_system"
        name_profile_system = "testprofile_copy_system"
        if object_type == "distro":
            attributes["kernel"] = kernel_path
            attributes["initrd"] = initrd_path
        elif object_type == "profile":
            add_object_via_cli("distro", {"name": name_distro_profile, "kernel": kernel_path, "initrd": initrd_path,
                                          "breed": "suse", "arch": "x86_64"})
        elif object_type == "system":
            add_object_via_cli("distro", {"name": name_distro_system,  "kernel": kernel_path, "initrd": initrd_path,
                                          "breed": "suse", "arch": "x86_64"})
            add_object_via_cli("profile", {"name": name_profile_system, "distro": name_distro_system})
        add_object_via_cli(object_type, attributes)
        new_object_name = "%s-copy" % attributes["name"]

        # Act
        (outputstd, outputerr) = run_cmd(cmd=[object_type, "copy", "--name=%s" % attributes["name"], "--newname=%s"
                                              % new_object_name])

        # Cleanup
        remove_object_via_cli(object_type, attributes["name"])
        remove_object_via_cli(object_type, new_object_name)
        if object_type == "profile":
            remove_object_via_cli("distro", name_distro_profile)
        elif object_type == "system":
            remove_object_via_cli("profile", name_profile_system)
            remove_object_via_cli("distro", name_distro_system)

        # Assert
        assert not outputstd

    @pytest.mark.parametrize("object_type,attributes", [
        ("distro", {"name": "testdistrorename", "kernel": "Set in method", "initrd": "Set in method", "breed": "suse",
                    "arch": "x86_64"}),
        ("profile", {"name": "testprofilerename", "distro": "testdistro_rename_profile"}),
        ("system", {"name": "testsystemrename", "profile": "testprofile_rename_system"}),
        ("image", {"name": "testimagerename"}),
        ("repo", {"name": "testreporename", "mirror": "http://localhost"}),
        ("package", {"name": "testpackagerename"}),
        ("mgmtclass", {"name": "testmgmtclassrename"}),
        ("file", {"name": "testfilerename", "path": "/tmp", "owner": "root", "group": "root", "mode": "600",
                  "is-dir": "True"}),
        ("menu", {"name": "testmenurename"}),
    ])
    def test_rename(self, run_cmd, add_object_via_cli, remove_object_via_cli, create_kernel_initrd, fk_initrd,
                    fk_kernel, object_type, attributes):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_kernel)
        name_distro_profile = "testdistro_rename_profile"
        name_distro_system = "testdistro_rename_system"
        name_profile_system = "testprofile_rename_system"
        if object_type == "distro":
            attributes["kernel"] = kernel_path
            attributes["initrd"] = initrd_path
        elif object_type == "profile":
            add_object_via_cli("distro", {"name": name_distro_profile, "kernel": kernel_path, "initrd": initrd_path,
                                          "breed": "suse", "arch": "x86_64"})
        elif object_type == "system":
            add_object_via_cli("distro", {"name": name_distro_system, "kernel": kernel_path, "initrd": initrd_path,
                                          "breed": "suse", "arch": "x86_64"})
            add_object_via_cli("profile", {"name": name_profile_system, "distro": name_distro_system})
        add_object_via_cli(object_type, attributes)
        new_object_name = "%s-renamed" % attributes["name"]

        # Act
        (outputstd, outputerr) = run_cmd(
            cmd=[object_type, "rename", "--name=%s" % attributes["name"], "--newname=%s" % new_object_name])

        # Cleanup
        remove_object_via_cli(object_type, new_object_name)
        if object_type == "profile":
            remove_object_via_cli("distro", name_distro_profile)
        elif object_type == "system":
            remove_object_via_cli("profile", name_profile_system)
            remove_object_via_cli("distro", name_distro_system)

        # Assert
        assert not outputstd

    @pytest.mark.parametrize("object_type,attributes", [
        ("distro", {"name": "testdistroadd", "kernel": "Set in method", "initrd": "Set in method", "breed": "suse",
                    "arch": "x86_64"}),
        ("profile", {"name": "testprofileadd", "distro": "testdistroadd_profile"}),
        ("system", {"name": "testsystemadd", "profile": "testprofileadd_system"}),
        ("image", {"name": "testimageadd"}),
        ("repo", {"name": "testrepoadd", "mirror": "http://localhost"}),
        ("package", {"name": "testpackageadd"}),
        ("mgmtclass", {"name": "testmgmtclassadd"}),
        ("file", {"name": "testfileadd", "path": "/tmp", "owner": "root", "group": "root", "mode": "600",
                  "is-dir": "True"}),
        ("menu", {"name": "testmenuadd"}),
    ])
    def test_add(self, run_cmd, remove_object_via_cli, generate_run_cmd_array, create_kernel_initrd, fk_initrd,
                 fk_kernel, add_object_via_cli, object_type, attributes):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_kernel)
        name_distro_profile = "testdistroadd_profile"
        name_distro_system = "testdistroadd_system"
        name_profile_system = "testprofileadd_system"
        if object_type == "distro":
            attributes["kernel"] = kernel_path
            attributes["initrd"] = initrd_path
        elif object_type == "profile":
            add_object_via_cli("distro", {"name": name_distro_profile, "kernel": kernel_path, "initrd": initrd_path,
                                          "breed": "suse", "arch": "x86_64"})
        elif object_type == "system":
            add_object_via_cli("distro", {"name": name_distro_system, "kernel": kernel_path, "initrd": initrd_path,
                                          "breed": "suse", "arch": "x86_64"})
            add_object_via_cli("profile", {"name": name_profile_system, "distro": name_distro_system})

        cmd_list = [object_type, "add"]
        options = generate_run_cmd_array(attributes)
        cmd_list.extend(options)

        # Act
        (outputstd, outputerr) = run_cmd(cmd=cmd_list)

        # Cleanup
        remove_object_via_cli(object_type, attributes["name"])
        if object_type == "profile":
            remove_object_via_cli("distro", name_distro_profile)
        elif object_type == "system":
            remove_object_via_cli("profile", name_profile_system)
            remove_object_via_cli("distro", name_distro_system)

        # Assert
        assert not outputstd

    @pytest.mark.parametrize("object_type,attributes", [
        ("distro", {"name": "testdistroremove", "kernel": "Set in method", "initrd": "Set in method", "breed": "suse",
                    "arch": "x86_64"}),
        ("profile", {"name": "testprofileremove", "distro": "testdistroremove_profile"}),
        ("system", {"name": "testsystemremove", "profile": "testprofileremove_system"}),
        ("image", {"name": "testimageremove"}),
        ("repo", {"name": "testreporemove", "mirror": "http://localhost"}),
        ("package", {"name": "testpackageremove"}),
        ("mgmtclass", {"name": "testmgmtclassremove"}),
        ("file", {"name": "testfileremove", "path": "/tmp", "owner": "root", "group": "root", "mode": "600",
                  "is-dir": "True"}),
        ("menu", {"name": "testmenuremove"}),
    ])
    def test_remove(self, run_cmd, add_object_via_cli, remove_object_via_cli, create_kernel_initrd, fk_initrd,
                    fk_kernel, object_type, attributes):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_kernel)
        name_distro_profile = "testdistroremove_profile"
        name_distro_system = "testdistroremove_system"
        name_profile_system = "testprofileremove_system"
        if object_type == "distro":
            attributes["kernel"] = kernel_path
            attributes["initrd"] = initrd_path
        elif object_type == "profile":
            add_object_via_cli("distro", {"name": name_distro_profile, "kernel": kernel_path, "initrd": initrd_path,
                                          "breed": "suse", "arch": "x86_64"})
        elif object_type == "system":
            add_object_via_cli("distro", {"name": name_distro_system, "kernel": kernel_path, "initrd": initrd_path,
                                          "breed": "suse", "arch": "x86_64"})
            add_object_via_cli("profile", {"name": name_profile_system, "distro": name_distro_system})
        add_object_via_cli(object_type, attributes)

        # Act
        (outputstd, outputerr) = run_cmd(cmd=[object_type, "remove", "--name=%s" % attributes["name"]])

        # Cleanup
        if object_type == "profile":
            remove_object_via_cli("distro", name_distro_profile)
        elif object_type == "system":
            remove_object_via_cli("profile", name_profile_system)
            remove_object_via_cli("distro", name_distro_system)

        # Assert
        assert not outputstd
