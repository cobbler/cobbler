import os
import re
import shutil
from pathlib import Path

import pytest
from netaddr.ip import IPAddress

from cobbler.api import CobblerAPI
from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.repo import Repo
from cobbler.items.system import System
from cobbler.cobbler_collections.manager import CollectionManager
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


@pytest.mark.parametrize("testvalue,expected_result", [
    ("10.0.0.1", True),
    ("Test", False)
])
def test_is_ip(testvalue, expected_result):
    # Arrange

    # Act
    result = utils.is_ip(testvalue)

    # Assert
    assert expected_result == result


@pytest.mark.parametrize("testvalue,expected_result", [
    ("AA:AA:AA:AA:AA:AA", True),
    ("FF:FF:FF:FF:FF:FF", True),
    ("FF:FF:FF:FF:FF", False),
    ("Test", False)
])
def test_is_mac(testvalue, expected_result):
    # Arrange

    # Act
    result = utils.is_mac(testvalue)

    # Assert
    assert expected_result == result


def test_is_systemd():
    # Arrange

    # Act
    result = utils.is_systemd()

    # Assert
    assert result


def test_get_random_mac():
    # Arrange
    api = CobblerAPI()

    # Act
    result = utils.get_random_mac(api)

    # Assert
    # TODO: Check for MAC validity
    assert result


def test_find_matching_files():
    # Arrange
    # TODO: Get testdir und check for files
    directory = "/test_dir/tests"
    expected = ["/test_dir/tests/settings_test.py", "/test_dir/tests/utils_test.py",
                "/test_dir/tests/template_api_test.py", "/test_dir/tests/templar_test.py",
                "/test_dir/tests/module_loader_test.py"]

    # Act
    results = utils.find_matching_files(directory, re.compile(r'.*_test.py'))

    # Assert
    assert expected.sort() == results.sort()


def test_find_highest_files():
    # Arrange
    # TODO: Build a directory with some versioned files.
    search_directory = "/dev/shm/"
    basename = "testfile"
    search_regex = re.compile(r'testfile.*')
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
    folders = [".olddata", ".repodata", ".repodata/.olddata", "repodata", "repodata/.olddata", "repodata/repodata",
               "testfolder"]
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


@pytest.mark.parametrize("remote_url,expected_result", [
    ("https://cobbler.github.io/signatures/latest.json", True),
    ("https://cobbler.github.io/signatures/not_existing", False)
])
def test_remote_file_exists(remote_url, expected_result):
    # Arrange

    # Act
    result = utils.remote_file_exists(remote_url)

    # Assert
    assert expected_result == result


@pytest.mark.parametrize("remote_url,expected_result", [
    ("http://bla", True),
    ("https://bla", True),
    ("ftp://bla", True),
    ("xyz", False)
])
def test_file_is_remote(remote_url, expected_result):
    # Arrange

    # Act
    result = utils.file_is_remote(remote_url)

    # Assert
    assert expected_result == result


@pytest.mark.parametrize("test_input,expected_result", [
    ("<<inherit>>", "<<inherit>>"),
    ("delete", [])
])
def test_input_string_or_list(test_input, expected_result):
    # Arrange

    # Act
    result = utils.input_string_or_list(test_input)

    # Assert
    assert expected_result == result


@pytest.mark.parametrize("testinput,expected_result,possible_exception", [
    ("<<inherit>>", (True, {}), does_not_raise()),
    ([""], None, pytest.raises(CX)),
    ("a b=10 c=abc", (True, {"a": None, "b": '10', "c": "abc"}), does_not_raise()),
    ({"ab": 0}, (True, {"ab": 0}), does_not_raise()),
    (0, None, pytest.raises(CX))
])
def test_input_string_or_dict(testinput, expected_result, possible_exception):
    # Arrange

    # Act
    with possible_exception:
        result = utils.input_string_or_dict(testinput)

        # Assert
        assert expected_result == result


@pytest.mark.parametrize("testinput,expected_result", [
    (True, True),
    (1, True),
    ("oN", True),
    ("yEs", True),
    ("Y", True),
    ("Test", False),
    (-5, False),
    (.5, False)
])
def test_input_boolean(testinput, expected_result):
    # Arrange

    # Act
    result = utils.input_boolean(testinput)

    # Assert
    assert expected_result == result


def test_grab_tree():
    # Arrange
    api = CobblerAPI()
    object_to_check = Distro(api._collection_mgr)
    # TODO: Create some objects and give them some inheritance.

    # Act
    result = utils.grab_tree(api, object_to_check)

    # Assert
    assert isinstance(result, list)
    assert result[-1].server == "127.0.0.1"


@pytest.mark.skip("We know this works through the xmlrpc tests. Generating corner cases to test this more, is hard.")
def test_blender():
    # Arrange
    # TODO: Create some objects
    api = CobblerAPI()
    root_item = None
    expected = {}

    # Act
    result = utils.blender(api, False, root_item)

    # Assert
    assert expected == result


@pytest.mark.parametrize("testinput,expected_result", [
    (None, None),
    ("data", None),
    (0, None),
    ({}, {})
])
def test_flatten(testinput, expected_result):
    # Arrange
    # TODO: Add more examples

    # Act
    result = utils.flatten(testinput)

    # Assert
    assert expected_result == result


@pytest.mark.parametrize("testinput,expected_result", [
    (["A", "a", 1, 5, 1], ["A", "a", 1, 5])
])
def test_uniquify(testinput, expected_result):
    # Arrange

    # Act
    result = utils.uniquify(testinput)

    # Assert
    assert expected_result == result


@pytest.mark.parametrize("testdict,subkey,expected_result", [
    ({}, "", {}),
    ({"Test": 0, "Test2": {"SubTest": 0, "!SubTest2": 0}}, "Test2", {"Test": 0, "Test2": {"SubTest": 0}})
])
def test_dict_removals(testdict, subkey, expected_result):
    # Arrange
    # TODO: Generate more parameter combinations

    # Act
    utils.dict_removals(testdict, subkey)

    # Assert
    assert expected_result == testdict


@pytest.mark.parametrize("testinput,expected_result", [
    ({}, "")
])
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
    utils.run_this(test_cmd, test_args, None)

    # Assert - If above method get's a zero exitcode it counts as successfully completed. Otherwise we die.
    assert True


@pytest.mark.skip("This method does magic. Since we havn't had the time to break it down, this test is skipped.")
def test_run_triggers():
    # Arrange
    api = CobblerAPI()
    globber = ""

    # Act
    utils.run_triggers(api, None, globber)

    # Assert
    # TODO: How the heck do we check that this actually did what it is supposed to do?
    assert False


def test_get_family():
    # Arrange
    # TODO: Make this nicer so it doesn't need to run on suse specific distros to succeed.

    # Act
    result = utils.get_family()

    # Assert
    assert result == "suse"


def test_os_release():
    # Arrange
    # TODO: Make this nicer so it doesn't need to run on suse specific distros to succeed.

    # Act
    result = utils.os_release()

    # Assert
    assert ("suse", 15.2) == result


@pytest.mark.parametrize("test_src,test_dst,expected_result", [
    # ("", "", False), --> This has a task in utils.py
    ("/usr/bin/os-release", "/tmp", True),
    ("/etc/os-release", "/tmp", False)
])
def test_is_safe_to_hardlink(test_src, test_dst, expected_result):
    # Arrange
    # TODO: Generate cases
    api = CobblerAPI()

    # Act
    result = utils.is_safe_to_hardlink(test_src, test_dst, api)

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
    utils.cachefile(cache_src, cache_dst, api=api)

    # Assert
    # TODO: Check .link_cache folder exists and the link cache file in it
    # TODO: Assert file exists in the cache destination
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_linkfile():
    # Arrange
    test_api = CobblerAPI()
    test_source = ""
    test_destination = ""

    # Act
    utils.linkfile(test_source, test_destination, api=test_api)

    # Assert
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_copyfile():
    # Arrange
    test_source = ""
    test_destination = ""

    # Act
    utils.copyfile(test_source, test_destination, None)

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


def test_rmfile():
    # Arrange
    filepath = "/dev/shm/testfile"
    Path(filepath).touch()

    assert os.path.exists(filepath)

    # Act
    result = utils.rmfile(filepath)

    # Assert
    assert result
    assert not os.path.exists(filepath)


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


@pytest.mark.parametrize("test_first_path,test_second_path,expected_result", [
    ("/tmp/test/a", "/tmp/test/a/b/c", "/b/c"),
    ("/tmp/test/a", "/opt/test/a", "")
])
def test_path_tail(test_first_path, test_second_path, expected_result):
    # Arrange
    # TODO: Check if this actually makes sense...

    # Act
    result = utils.path_tail(test_first_path, test_second_path)

    # Assert
    assert expected_result == result


@pytest.mark.parametrize("test_architecture,test_raise", [
    ("x86_64", does_not_raise()),
    ("abc", pytest.raises(CX))
])
def test_set_arch(test_architecture, test_raise):
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    testdistro = Distro(test_manager)

    # Act
    with test_raise:
        utils.set_arch(testdistro, test_architecture)

        # Assert
        assert testdistro.arch == test_architecture


def test_set_os_version():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    testdistro = Distro(test_manager)
    testdistro.set_breed("redhat")

    # Act
    utils.set_os_version(testdistro, "rhel4")

    # Assert
    assert testdistro.breed == "redhat"
    assert testdistro.os_version == "rhel4"


def test_set_breed():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    testdistro = Distro(test_manager)

    # Act
    utils.set_breed(testdistro, "redhat")

    # Assert
    assert testdistro.breed == "redhat"


def test_set_repo_os_version():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    testrepo = Repo(test_manager)
    testrepo.set_breed("yum")

    # Act
    utils.set_repo_os_version(testrepo, "rhel4")

    # Assert
    assert testrepo.breed == "yum"
    assert testrepo.os_version == "rhel4"


def test_set_repo_breed():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    testrepo = Repo(test_manager)

    # Act
    utils.set_repo_breed(testrepo, "yum")

    # Assert
    assert testrepo.breed == "yum"


def test_set_repos():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    testprofile = Profile(test_manager)

    # Act
    # TODO: Test this also with the bypass check
    utils.set_repos(testprofile, "testrepo1 testrepo2", bypass_check=True)

    # Assert
    assert testprofile.repos == ["testrepo1", "testrepo2"]


def test_set_virt_file_size():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    testprofile = Profile(test_manager)

    # Act
    # TODO: Test multiple disks via comma separation
    utils.set_virt_file_size(testprofile, "8")

    # Assert
    assert isinstance(testprofile.virt_file_size, int)
    assert testprofile.virt_file_size == 8


@pytest.mark.parametrize("test_driver,expected_result,test_raise", [
    ("qcow2", "qcow2", does_not_raise()),
    ("bad_driver", "", pytest.raises(CX))
])
def test_set_virt_disk_driver(test_driver, expected_result, test_raise):
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    testprofile = Profile(test_manager)

    # Act
    with test_raise:
        utils.set_virt_disk_driver(testprofile, test_driver)

        # Assert
        assert testprofile.virt_disk_driver == expected_result


@pytest.mark.parametrize("test_autoboot,expectation", [
    (0, does_not_raise()),
    (1, does_not_raise()),
    (2, pytest.raises(CX)),
    ("Test", pytest.raises(CX))
])
def test_set_virt_auto_boot(test_autoboot, expectation):
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    testprofile = Profile(test_manager)

    # Act
    with expectation:
        utils.set_virt_auto_boot(testprofile, test_autoboot)

        # Assert
        assert isinstance(testprofile.virt_auto_boot, bool)
        assert testprofile.virt_auto_boot is True or testprofile.virt_auto_boot is False


@pytest.mark.parametrize("test_input,expected_exception", [
    (0, does_not_raise()),
    (1, does_not_raise()),
    (5, pytest.raises(CX)),
    ("", pytest.raises(CX))
])
def test_set_virt_pxe_boot(test_input, expected_exception):
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    test_system = System(test_manager)

    # Act
    with expected_exception:
        result = utils.set_virt_pxe_boot(test_system, test_input)

        # Assert
        assert test_system.virt_pxe_boot == 0 or test_system.virt_pxe_boot == 1


def test_set_virt_ram():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    test_system = System(test_manager)

    # Act
    utils.set_virt_ram(test_system, 1024)

    # Assert
    assert test_system.virt_ram == 1024


def test_set_virt_type():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    test_system = System(test_manager)

    # Act
    utils.set_virt_type(test_system, "qemu")

    # Assert
    assert test_system.virt_type == "qemu"


def test_set_virt_bridge():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    test_system = System(test_manager)

    # Act
    utils.set_virt_bridge(test_system, "testbridge")

    # Assert
    assert test_system.virt_bridge == "testbridge"


def test_set_virt_path():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    test_system = System(test_manager)
    test_location = "/somerandomfakelocation"

    # Act
    utils.set_virt_path(test_system, test_location)

    # Assert
    assert test_system.virt_path == test_location


def test_set_virt_cpus():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    test_system = System(test_manager)

    # Act -> These are develishly bad tests. Please spare me the lecture and let my joke in here.
    utils.set_virt_cpus(test_system, 666)

    # Assert
    assert test_system.virt_cpus == 666


@pytest.mark.parametrize("test_input,expected_exception", [
    ("Test", does_not_raise()),
    ("Test;Test", pytest.raises(CX)),
    ("Test..Test", pytest.raises(CX))
])
def test_safe_filter(test_input, expected_exception):
    # Arrange, Act & Assert
    with expected_exception:
        assert utils.safe_filter(test_input) is None


def test_is_selinux_enabled():
    # Arrange, Act & Assert
    # TODO: Functionality test is something which needs SELinux knowledge
    assert isinstance(utils.is_selinux_enabled(), bool)


def test_get_mtab():
    # Arrange

    # Act
    result = utils.get_mtab()

    # Assert
    assert isinstance(result, list)


def test_set_serial_device():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    test_system = System(test_manager)

    # Act
    result = utils.set_serial_device(test_system, 0)

    # Assert
    assert result
    assert test_system.serial_device == 0


def test_set_serial_baud_rate():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    test_system = System(test_manager)

    # Act
    utils.set_serial_baud_rate(test_system, 9600)

    # Assert
    assert test_system.serial_baud_rate == 9600


def test_get_file_device_path():
    # Arrange

    # Act
    result = utils.get_file_device_path("/etc/os-release")

    # Assert
    # TODO Does not work in all environments (e.g. openSUSE TW with BTRFS)
    assert result == ("overlay", "/usr/lib/os-release")


def test_is_remote_file():
    # Arrange

    # Act
    result = utils.is_remote_file("/etc/os-release")

    # Assert
    assert not result


def test_subprocess_sp():
    # Arrange

    # Act
    result_out, result_rc = utils.subprocess_sp(None, "echo Test")

    # Assert
    # The newline makes sense in my (@SchoolGuy) eyes since we want to have multiline output also in a single string.
    assert result_out == "Test\n"
    assert result_rc == 0


def test_subprocess_call():
    # Arrange

    # Act
    result = utils.subprocess_call(None, "echo Test")

    # Assert
    assert result == 0


def test_subprocess_get():
    # Arrange

    # Act
    result = utils.subprocess_get(None, "echo Test")

    # Assert
    # The newline makes sense in my (@SchoolGuy) eyes since we want to have multiline output also in a single string.
    assert result == "Test\n"


def test_clear_from_fields():
    # Arrange
    test_api = CobblerAPI()
    test_distro = Distro(test_api._collection_mgr)
    test_distro.name = "Test"

    # Pre Assert to check this works
    assert test_distro.name == "Test"

    # Act
    utils.clear_from_fields(test_distro, test_distro.get_fields())

    # Assert
    assert test_distro.name == ""


def test_from_dict_from_fields():
    # Arrange
    test_api = CobblerAPI()
    test_distro = Distro(test_api._collection_mgr)

    # Act
    utils.from_dict_from_fields(test_distro, {"name": "testname"},
                                [
                                    ["name", "", 0, "Name", True, "Ex: Fedora-11-i386", 0, "str"]
                                ])

    # Assert
    assert test_distro.name == "testname"


def test_to_dict_from_fields():
    # Arrange
    test_api = CobblerAPI()
    test_distro = Distro(test_api._collection_mgr)

    # Act
    result = utils.to_dict_from_fields(test_distro, test_distro.get_fields())

    # Assert - This test is specific to a Distro object
    assert len(result.keys()) == 25


def test_to_string_from_fields():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    test_distro = Distro(test_manager)

    # Act
    result = utils.to_string_from_fields(test_distro.__dict__, test_distro.get_fields())

    # Assert - This test is specific to a Distro object
    assert len(result.splitlines()) == 19


def test_get_setter_methods_from_fields():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    test_distro = Distro(test_manager)

    # Act
    result = utils.get_setter_methods_from_fields(test_distro, test_distro.get_fields())

    # Assert
    assert isinstance(result, dict)


def test_load_signatures():
    # Arrange
    utils.SIGNATURE_CACHE = {}
    old_cache = utils.SIGNATURE_CACHE

    # Act
    utils.load_signatures("/var/lib/cobbler/distro_signatures.json")

    # Assert
    assert old_cache != utils.SIGNATURE_CACHE


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
    assert result == "http://127.0.0.1:80/cobbler_api"


def test_local_get_cobbler_xmlrpc_url():
    # Arrange

    # Act
    result = utils.local_get_cobbler_xmlrpc_url()

    # Assert
    assert result == "http://127.0.0.1:25151"


@pytest.mark.parametrize("input_data,expected_output", [
    (None, "~"),
    ([], []),
    ({}, {}),
    (0, 0),
    ("Test", "Test")
])
def test_strip_none(input_data, expected_output):
    # Arrange

    # Act
    result = utils.strip_none(input_data)

    # Assert
    assert expected_output == result


@pytest.mark.parametrize("input_data,expected_output", [
    ("~", None),
    ("Test~", "Test~"),
    ("Te~st", "Te~st"),
    (["~", "Test"], [None, "Test"]),
    ({}, {})
])
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


def test_dhcpconf_location():
    # Arrange

    # Act
    result = utils.dhcpconf_location()

    # Assert
    assert result == "/etc/dhcpd.conf"


def test_namedconf_location():
    # Arrange

    # Act
    result = utils.namedconf_location()

    # Assert
    assert result == "/etc/named.conf"


def test_zonefile_base():
    # Arrange

    # Act
    result = utils.zonefile_base()

    # Assert
    assert result == "/var/lib/named/"


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


@pytest.mark.skip("This is hard to test as we are creating a symlink in the method. For now we skip it.")
def test_link_distro():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    test_distro = Distro(test_manager)

    # Act
    utils.link_distro(test_manager.settings(), test_distro)

    # Assert
    assert False


def test_find_distro_path():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    test_distro = Distro(test_manager)
    test_distro.kernel = "/dev/shm/fakekernelfile"

    # Act
    result = utils.find_distro_path(test_manager.settings(), test_distro)

    # Assert
    assert result == "/dev/shm"


@pytest.mark.parametrize("test_input_v1,test_input_v2,expected_output,error_expectation", [
    ("0.9", "0.1", True, does_not_raise()),
    ("0.1", "0.9", False, does_not_raise())
])
def test_compare_version_gt(test_input_v1, test_input_v2, expected_output, error_expectation):
    # Arrange

    # Act
    result = utils.compare_versions_gt(test_input_v1, test_input_v2)

    # Assert
    with error_expectation:
        assert expected_output == result


def test_kopts_overwrite():
    # Arrange
    test_api = CobblerAPI()
    test_manager = CollectionManager(test_api)
    test_distro = Distro(test_manager)
    test_distro.set_breed("suse")
    test_distro.name = "kopts_test_distro"
    test_profile = Profile(test_manager)
    test_profile.distro = test_distro.name
    test_system = System(test_manager)
    test_system.name = "kopts_test_system"
    kopts = {"textmode": False, "text": True}

    # Act
    utils.kopts_overwrite(test_system, test_distro, kopts, test_api.settings())

    # Assert
    assert "textmode" in kopts
    assert "info" in kopts
