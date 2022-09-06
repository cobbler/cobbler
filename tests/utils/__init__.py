import os
import re
import shutil
from pathlib import Path

import pytest
from netaddr.ip import IPAddress

from cobbler import enums
from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.items.distro import Distro
from tests.conftest import does_not_raise


def test_pretty_hex():
    # Arrange
    value = IPAddress("10.0.0.1")

    # Act
    result = utils.pretty_hex(value)

    # Assert
    assert result == "0A000001"


def test_get_host_ip():
    # Arrange

    # Act
    result = utils.get_host_ip("10.0.0.1")

    # Assert
    assert result == "0A000001"


@pytest.mark.parametrize(
    "testvalue,expected_result", [("10.0.0.1", True), ("Test", False)]
)
def test_is_ip(testvalue, expected_result):
    # Arrange

    # Act
    result = utils.is_ip(testvalue)

    # Assert
    assert expected_result == result


def test_get_random_mac(cobbler_api):
    # Arrange

    # Act
    result = utils.get_random_mac(cobbler_api)

    # Assert
    # TODO: Check for MAC validity
    assert result


def test_find_matching_files():
    # Arrange
    # TODO: Get testdir und check for files
    directory = "/test_dir/tests"
    expected = [
        "/test_dir/tests/settings_test.py",
        "/test_dir/tests/utils_test.py",
        "/test_dir/tests/template_api_test.py",
        "/test_dir/tests/templar_test.py",
        "/test_dir/tests/module_loader_test.py",
    ]

    # Act
    results = utils.find_matching_files(directory, re.compile(r".*_test.py"))
    results.sort()

    # Assert
    assert expected.sort() == results.sort()


def test_find_highest_files():
    # Arrange
    # TODO: Build a directory with some versioned files.
    search_directory = "/dev/shm/"
    basename = "testfile"
    search_regex = re.compile(r"testfile.*")
    expected = "/dev/shm/testfile"
    Path(os.path.join(search_directory, basename)).touch()

    # Act
    result = utils.find_highest_files(search_directory, basename, search_regex)

    # Assert
    assert expected == result


def test_find_kernel():
    # Arrange
    fake_env = "/dev/shm/fakekernelfolder"
    os.mkdir(fake_env)
    expected = os.path.join(fake_env, "vmlinuz")
    Path(expected).touch()

    # Act
    result = utils.find_kernel(fake_env)

    # Assert
    assert expected == result


def test_remove_yum_olddata():
    # Arrange
    fake_env = "/dev/shm/fakefolder"
    os.mkdir(fake_env)
    expected_to_exist = "testfolder/existing"
    folders = [
        ".olddata",
        ".repodata",
        ".repodata/.olddata",
        "repodata",
        "repodata/.olddata",
        "repodata/repodata",
        "testfolder",
    ]
    for folder in folders:
        os.mkdir(os.path.join(fake_env, folder))
    files = ["test", expected_to_exist]
    for file in files:
        Path(os.path.join(fake_env, file)).touch()

    # Act
    utils.remove_yum_olddata(fake_env)

    # Assert
    assert os.path.exists(os.path.join(fake_env, expected_to_exist))
    assert not os.path.exists(os.path.join(fake_env, ".olddata"))


def test_find_initrd():
    # Arrange
    fake_env = "/dev/shm/fakeinitrdfolder"
    os.mkdir(fake_env)
    expected = os.path.join(fake_env, "initrd.img")
    Path(expected).touch()

    # Act
    result = utils.find_initrd(fake_env)

    # Assert
    assert expected == result


def test_read_file_contents():
    # Arrange
    # TODO: Do this remotely & also a failed test
    fake_file = "/dev/shm/fakeloremipsum"
    content = "Lorem Ipsum Bla"

    with open(fake_file, "w") as f:
        f.write(content)

    # Act
    result = utils.read_file_contents(fake_file)

    # Cleanup
    os.remove(fake_file)

    # Assert
    assert content == result


@pytest.mark.parametrize(
    "remote_url,expected_result",
    [
        ("https://cobbler.github.io/signatures/latest.json", True),
        ("https://cobbler.github.io/signatures/not_existing", False),
    ],
)
def test_remote_file_exists(remote_url, expected_result):
    # Arrange

    # Act
    result = utils.remote_file_exists(remote_url)

    # Assert
    assert expected_result == result


@pytest.mark.parametrize(
    "remote_url,expected_result",
    [("http://bla", True), ("https://bla", True), ("ftp://bla", True), ("xyz", False)],
)
def test_file_is_remote(remote_url, expected_result):
    # Arrange

    # Act
    result = utils.file_is_remote(remote_url)

    # Assert
    assert expected_result == result


def test_blender(cobbler_api):
    # Arrange
    root_item = Distro(cobbler_api)

    # Act
    result = utils.blender(cobbler_api, False, root_item)

    # Assert
    assert len(result) == 161
    # Must be present because the settings have it
    assert "server" in result
    # Must be present because it is a field of distro
    assert "os_version" in result
    # Must be present because it inherits but is a field of distro
    assert "boot_loaders" in result


@pytest.mark.parametrize(
    "testinput,expected_result,expected_exception",
    [
        (None, None, does_not_raise()),
        ("data", None, does_not_raise()),
        (0, None, does_not_raise()),
        ({}, {}, does_not_raise()),
    ],
)
def test_flatten(testinput, expected_result, expected_exception):
    # Arrange
    # TODO: Add more examples

    # Act
    with expected_exception:
        result = utils.flatten(testinput)

        # Assert
        assert expected_result == result


@pytest.mark.parametrize(
    "testinput,expected_result", [(["A", "a", 1, 5, 1], ["A", "a", 1, 5])]
)
def test_uniquify(testinput, expected_result):
    # Arrange

    # Act
    result = utils.uniquify(testinput)

    # Assert
    assert expected_result == result


@pytest.mark.parametrize(
    "testdict,subkey,expected_result",
    [
        ({}, "", {}),
        (
            {"Test": 0, "Test2": {"SubTest": 0, "!SubTest2": 0}},
            "Test2",
            {"Test": 0, "Test2": {"SubTest": 0}},
        ),
    ],
)
def test_dict_removals(testdict, subkey, expected_result):
    # Arrange
    # TODO: Generate more parameter combinations

    # Act
    utils.dict_removals(testdict, subkey)

    # Assert
    assert expected_result == testdict


@pytest.mark.parametrize("testinput,expected_result", [({}, "")])
def test_dict_to_string(testinput, expected_result):
    # Arrange
    # TODO: Generate more parameter combinations

    # Act
    result = utils.dict_to_string(testinput)

    # Assert
    assert expected_result == result


@pytest.mark.skip("This method needs mocking of subprocess_call. We do this later.")
def test_rsync_files():
    # Arrange
    # TODO: Generate test env with data to check
    testsrc = ""
    testdst = ""
    testargs = ""

    # Act
    result = utils.rsync_files(testsrc, testdst, testargs)

    # Assert
    assert result
    # TODO: Check if the files were copied correctly.
    assert False


def test_run_this():
    # Arrange
    test_cmd = "echo %s"
    test_args = "Test"

    # Act
    utils.run_this(test_cmd, test_args)

    # Assert - If above method get's a zero exitcode it counts as successfully completed. Otherwise we die.
    assert True


@pytest.mark.skip(
    "This method does magic. Since we havn't had the time to break it down, this test is skipped."
)
def test_run_triggers(cobbler_api):
    # Arrange
    globber = ""

    # Act
    utils.run_triggers(cobbler_api, None, globber)

    # Assert
    # TODO: How the heck do we check that this actually did what it is supposed to do?
    assert False


def test_get_family():
    # Arrange
    distros = ("suse", "redhat", "debian")

    # Act
    result = utils.get_family()

    # Assert
    assert result in distros


def test_os_release():
    # Arrange
    # TODO: Make this nicer so it doesn't need to run on suse specific distros to succeed.

    # Act
    result = utils.os_release()

    # Assert
    assert ("suse", 15.2) or ("suse", 15.3) == result


@pytest.mark.parametrize(
    "test_src,test_dst,expected_result",
    [
        # ("", "", False), --> This has a task in utils.py
        ("/usr/bin/os-release", "/tmp", True),
        ("/etc/os-release", "/tmp", False),
    ],
)
def test_is_safe_to_hardlink(cobbler_api, test_src, test_dst, expected_result):
    # Arrange
    # TODO: Generate cases

    # Act
    result = utils.is_safe_to_hardlink(test_src, test_dst, cobbler_api)

    # Assert
    assert expected_result == result


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_hashfile():
    # Arrange
    # TODO: Create testfile
    testfilepath = "/dev/shm/bigtestfile"
    expected_hash = ""

    # Act
    result = utils.hashfile(testfilepath)

    # Assert
    assert expected_hash == result


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_cachefile():
    # Arrange
    cache_src = ""
    cache_dst = ""
    api = None

    # Act
    utils.cachefile(cache_src, cache_dst)

    # Assert
    # TODO: Check .link_cache folder exists and the link cache file in it
    # TODO: Assert file exists in the cache destination
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_linkfile(cobbler_api):
    # Arrange
    test_source = ""
    test_destination = ""

    # Act
    utils.linkfile(test_source, test_destination, api=cobbler_api)

    # Assert
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_copyfile():
    # Arrange
    test_source = ""
    test_destination = ""

    # Act
    utils.copyfile(test_source, test_destination)

    # Assert
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_copyremotefile():
    # Arrange
    test_source = ""
    test_destination = ""

    # Act
    utils.copyremotefile(test_source, test_destination, None)

    # Assert
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_copyfile_pattern():
    # Arrange
    test_pattern = ""
    test_destination = ""

    # Act
    utils.copyfile_pattern(test_pattern, test_destination)

    # Assert
    assert False


def test_rmfile(tmpdir: Path):
    # Arrange
    tfile = tmpdir.join("testfile")

    # Act
    utils.rmfile(tfile)

    # Assert
    assert not os.path.exists(tfile)


def test_rmglob_files(tmpdir: Path):
    # Arrange
    tfile1 = tmpdir.join("file1.tfile")
    tfile2 = tmpdir.join("file2.tfile")

    # Act
    utils.rmglob_files(tmpdir, "*.tfile")

    # Assert
    assert not os.path.exists(tfile1)
    assert not os.path.exists(tfile2)


def test_rmtree_contents():
    # Arrange
    testfolder = "/dev/shm/"
    testfiles = ["test1", "blafile", "testremove"]
    for file in testfiles:
        Path(os.path.join(testfolder, file)).touch()

    # Act
    utils.rmtree_contents(testfolder)

    # Assert
    assert len(os.listdir(testfolder)) == 0


def test_rmtree():
    # Arrange
    testtree = "/dev/shm/testtree"
    os.mkdir(testtree)

    # Pre assert to check the creation succeeded.
    assert os.path.exists(testtree)

    # Act
    utils.rmtree(testtree)

    # Assert
    assert not os.path.exists(testtree)


def test_mkdir():
    # TODO: Check how already existing folder is handled.
    # Arrange
    testfolder = "/dev/shm/testfoldercreation"
    testmode = 0o600

    try:
        shutil.rmtree(testfolder)
    except OSError:
        pass

    # Pre assert to check that this actually does something
    assert not os.path.exists(testfolder)

    # Act
    utils.mkdir(testfolder, testmode)

    # Assert
    assert os.path.exists(testfolder)


@pytest.mark.parametrize(
    "test_first_path,test_second_path,expected_result",
    [("/tmp/test/a", "/tmp/test/a/b/c", "/b/c"), ("/tmp/test/a", "/opt/test/a", "")],
)
def test_path_tail(test_first_path, test_second_path, expected_result):
    # Arrange
    # TODO: Check if this actually makes sense...

    # Act
    result = utils.path_tail(test_first_path, test_second_path)

    # Assert
    assert expected_result == result


@pytest.mark.parametrize(
    "test_input,expected_exception",
    [
        ("Test", does_not_raise()),
        ("Test;Test", pytest.raises(CX)),
        ("Test..Test", pytest.raises(CX)),
    ],
)
def test_safe_filter(test_input, expected_exception):
    # Arrange, Act & Assert
    with expected_exception:
        assert utils.safe_filter(test_input) is None


def test_is_selinux_enabled():
    # Arrange, Act & Assert
    # TODO: Functionality test is something which needs SELinux knowledge
    assert isinstance(utils.is_selinux_enabled(), bool)


@pytest.mark.parametrize(
    "input_cmd,expected_result", [("foobaz", False), ("echo", True)]
)
def test_command_existing(input_cmd, expected_result):
    # Arrange & Act
    result = utils.command_existing(input_cmd)

    # Assert
    assert result == expected_result


def test_subprocess_sp():
    # Arrange

    # Act
    result_out, result_rc = utils.subprocess_sp("echo Test")

    # Assert
    # The newline makes sense in my (@SchoolGuy) eyes since we want to have multiline output also in a single string.
    assert result_out == "Test\n"
    assert result_rc == 0


def test_subprocess_call():
    # Arrange

    # Act
    result = utils.subprocess_call("echo Test")

    # Assert
    assert result == 0


def test_subprocess_get():
    # Arrange

    # Act
    result = utils.subprocess_get("echo Test")

    # Assert
    # The newline makes sense in my (@SchoolGuy) eyes since we want to have multiline output also in a single string.
    assert result == "Test\n"


def test_get_supported_system_boot_loaders():
    # Arrange

    # Act
    result = utils.get_supported_system_boot_loaders()

    # Assert
    assert result == ["grub", "pxe", "ipxe"]


def test_get_shared_secret():
    # Arrange
    # TODO: Test the case where the file is there.

    # Act
    result = utils.get_shared_secret()

    # Assert
    assert result == -1


def test_local_get_cobbler_api_url():
    # Arrange

    # Act
    result = utils.local_get_cobbler_api_url()

    # Assert
    assert result == "http://192.168.1.1:80/cobbler_api"


def test_local_get_cobbler_xmlrpc_url():
    # Arrange

    # Act
    result = utils.local_get_cobbler_xmlrpc_url()

    # Assert
    assert result == "http://127.0.0.1:25151"


@pytest.mark.parametrize(
    "input_data,expected_output",
    [(None, "~"), ([], []), ({}, {}), (0, 0), ("Test", "Test")],
)
def test_strip_none(input_data, expected_output):
    # Arrange

    # Act
    result = utils.strip_none(input_data)

    # Assert
    assert expected_output == result


@pytest.mark.parametrize(
    "input_data,expected_output",
    [
        ("~", None),
        ("Test~", "Test~"),
        ("Te~st", "Te~st"),
        (["~", "Test"], [None, "Test"]),
        ({}, {}),
    ],
)
def test_revert_strip_none(input_data, expected_output):
    # Arrange

    # Act
    result = utils.revert_strip_none(input_data)

    # Assert
    assert expected_output == result


def test_lod_to_dod():
    # Arrange
    list_of_dicts = [{"a": 2}, {"a": 3}]
    expected_result = {2: {"a": 2}, 3: {"a": 3}}

    # Act
    result = utils.lod_to_dod(list_of_dicts, "a")

    # Assert
    assert expected_result == result


def test_lod_sort_by_key():
    # Arrange
    list_of_dicts = [{"a": 3}, {"a": 5}, {"a": 2}]
    expected_result = [{"a": 2}, {"a": 3}, {"a": 5}]

    # Act
    result = utils.lod_sort_by_key(list_of_dicts, "a")

    # Assert
    assert expected_result == result


def test_dhcpv4conf_location():
    # TODO: Parameterize and check for wrong argument
    # Arrange

    # Act
    result = utils.dhcpconf_location(enums.DHCP.V4)

    # Assert
    assert result == "/etc/dhcpd.conf"


def test_dhcpv6conf_location():
    # TODO: Parameterize and check for wrong argument
    # Arrange

    # Act
    result = utils.dhcpconf_location(enums.DHCP.V6)

    # Assert
    assert result == "/etc/dhcpd6.conf"


def test_namedconf_location():
    # Arrange

    # Act
    result = utils.namedconf_location()

    # Assert
    assert result == "/etc/named.conf"


def test_dhcp_service_name():
    # Arrange

    # Act
    result = utils.dhcp_service_name()

    # Assert
    assert result == "dhcpd"


def test_named_service_name():
    # Arrange

    # Act
    result = utils.named_service_name()

    # Assert
    assert result == "named"


def test_find_distro_path(cobbler_api, create_testfile, tmp_path):
    # Arrange
    fk_kernel = "vmlinuz1"
    create_testfile(fk_kernel)
    test_distro = Distro(cobbler_api)
    test_distro.kernel = os.path.join(tmp_path, fk_kernel)

    # Act
    result = utils.find_distro_path(cobbler_api.settings(), test_distro)

    # Assert
    assert result == tmp_path.as_posix()


@pytest.mark.parametrize(
    "test_input_v1,test_input_v2,expected_output,error_expectation",
    [("0.9", "0.1", True, does_not_raise()), ("0.1", "0.9", False, does_not_raise())],
)
def test_compare_version_gt(
    test_input_v1, test_input_v2, expected_output, error_expectation
):
    # Arrange

    # Act
    result = utils.compare_versions_gt(test_input_v1, test_input_v2)

    # Assert
    with error_expectation:
        assert expected_output == result


def test_kopts_overwrite():
    # Arrange
    distro_breed = "suse"
    system_name = "kopts_test_system"
    kopts = {"textmode": False, "text": True}

    # Act
    utils.kopts_overwrite(kopts, "servername", distro_breed, system_name)

    # Assert
    assert "textmode" in kopts
    assert "info" in kopts
