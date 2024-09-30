import binascii
import datetime
import os
import re
import time
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING, Any

import pytest
from netaddr.ip import IPAddress

from cobbler import enums, utils
from cobbler.items.distro import Distro

from tests.conftest import does_not_raise

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


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
def test_is_ip(testvalue, expected_result):  # type: ignore
    # Arrange

    # Act
    result = utils.is_ip(testvalue)  # type: ignore

    # Assert
    assert expected_result == result


def test_get_random_mac(cobbler_api):  # type: ignore
    # Arrange

    # Act
    result = utils.get_random_mac(cobbler_api)  # type: ignore

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
        (
            "https://cobbler.github.io/libcobblersignatures/data/v2/distro_signatures.json",
            True,
        ),
        ("https://cobbler.github.io/signatures/not_existing", False),
    ],
)
def test_remote_file_exists(remote_url, expected_result):  # type: ignore
    # Arrange

    # Act
    result = utils.remote_file_exists(remote_url)  # type: ignore

    # Assert
    assert expected_result == result


@pytest.mark.parametrize(
    "remote_url,expected_result",
    [("http://bla", True), ("https://bla", True), ("ftp://bla", True), ("xyz", False)],
)
def test_file_is_remote(remote_url, expected_result):  # type: ignore
    # Arrange

    # Act
    result = utils.file_is_remote(remote_url)  # type: ignore

    # Assert
    assert expected_result == result


def test_blender(cobbler_api):  # type: ignore
    # Arrange
    root_item = Distro(cobbler_api)  # type: ignore

    # Act
    result = utils.blender(cobbler_api, False, root_item)  # type: ignore

    # Assert
    assert len(result) == 170
    # Must be present because the settings have it
    assert "server" in result
    # Must be present because it is a field of distro
    assert "os_version" in result
    # Must be present because it inherits but is a field of distro
    assert "template_files" in result


@pytest.mark.parametrize(
    "testinput,expected_result,expected_exception",
    [
        (None, None, does_not_raise()),
        ("data", None, does_not_raise()),
        (0, None, does_not_raise()),
        ({}, {}, does_not_raise()),
    ],
)
def test_flatten(testinput, expected_result, expected_exception):  # type: ignore
    # Arrange
    # TODO: Add more examples

    # Act
    with expected_exception:
        result = utils.flatten(testinput)  # type: ignore

        # Assert
        assert expected_result == result


@pytest.mark.parametrize(
    "testinput,expected_result", [(["A", "a", 1, 5, 1], ["A", "a", 1, 5])]
)
def test_uniquify(testinput, expected_result):  # type: ignore
    # Arrange

    # Act
    result = utils.uniquify(testinput)  # type: ignore

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
def test_dict_removals(testdict, subkey, expected_result):  # type: ignore
    # Arrange
    # TODO: Generate more parameter combinations

    # Act
    utils.dict_removals(testdict, subkey)  # type: ignore

    # Assert
    assert expected_result == testdict


@pytest.mark.parametrize("testinput,expected_result", [({}, "")])
def test_dict_to_string(testinput, expected_result):  # type: ignore
    # Arrange
    # TODO: Generate more parameter combinations

    # Act
    result = utils.dict_to_string(testinput)  # type: ignore

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


@pytest.mark.skip(
    "This method does magic. Since we havn't had the time to break it down, this test is skipped."
)
def test_run_triggers(cobbler_api):  # type: ignore
    # Arrange
    globber = ""

    # Act
    utils.run_triggers(cobbler_api, None, globber)  # type: ignore

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
    assert ("suse", 15.2) or ("suse", 15.3) == result  # type: ignore


def test_is_selinux_enabled():
    # Arrange, Act & Assert
    # TODO: Functionality test is something which needs SELinux knowledge
    assert isinstance(utils.is_selinux_enabled(), bool)


@pytest.mark.parametrize(
    "input_cmd,expected_result", [("foobaz", False), ("echo", True)]
)
def test_command_existing(input_cmd, expected_result):  # type: ignore
    # Arrange & Act
    result = utils.command_existing(input_cmd)  # type: ignore

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


@pytest.mark.parametrize(
    "input_command,expected_exception,expected_result",
    [
        ("echo Test", pytest.raises(ValueError), None),
        ("true", does_not_raise(), 0),
    ],
)
def test_subprocess_call(input_command, expected_exception, expected_result):  # type: ignore
    # Arrange

    # Act
    with expected_exception:
        result = utils.subprocess_call(input_command)  # type: ignore

        # Assert
        assert result == expected_result


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


@pytest.mark.parametrize("web_ss_exists", [True, False])
def test_get_shared_secret(mocker: "MockerFixture", web_ss_exists: bool):
    # Arrange
    open_mock = mocker.mock_open()
    random_data = binascii.hexlify(os.urandom(512)).decode()
    mock_web_ss = mocker.mock_open(read_data=random_data)

    def mock_open(*args: Any, **kwargs: Any):
        if not web_ss_exists:
            open_mock.side_effect = FileNotFoundError
            return open_mock(*args, **kwargs)
        if args[0] == "/var/lib/cobbler/web.ss":
            return mock_web_ss(*args, **kwargs)
        return open_mock(*args, **kwargs)

    mocker.patch("builtins.open", mock_open)

    # Act
    result = utils.get_shared_secret()

    # Assert
    if web_ss_exists:
        assert result == random_data
    else:
        assert result == -1


def test_local_get_cobbler_api_url():
    # Arrange

    # Act
    result = utils.local_get_cobbler_api_url()

    # Assert
    assert result in [
        "http://192.168.1.1:80/cobbler_api",
        "http://127.0.0.1:80/cobbler_api",
    ]


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
def test_strip_none(input_data, expected_output):  # type: ignore
    # Arrange

    # Act
    result = utils.strip_none(input_data)  # type: ignore

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
def test_revert_strip_none(input_data, expected_output):  # type: ignore
    # Arrange

    # Act
    result = utils.revert_strip_none(input_data)  # type: ignore

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


@pytest.mark.parametrize(
    "test_input_v1,test_input_v2,expected_output,error_expectation",
    [("0.9", "0.1", True, does_not_raise()), ("0.1", "0.9", False, does_not_raise())],
)
def test_compare_version_gt(
    test_input_v1, test_input_v2, expected_output, error_expectation  # type: ignore
):
    # Arrange

    # Act
    result = utils.compare_versions_gt(test_input_v1, test_input_v2)  # type: ignore

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


def test_filelock():
    # Arrange
    filelock_path = "/tmp/filelock_test"
    thread_times = []

    def thread_fun():
        thread_times.append(datetime.datetime.now())  # type: ignore
        with utils.filelock(filelock_path):
            thread_times.append(datetime.datetime.now())  # type: ignore

    t = Thread(target=thread_fun)

    # Act
    with utils.filelock(filelock_path):
        t.start()
        time.sleep(1)

    t.join()

    # Assert
    assert os.path.isfile(filelock_path)

    # Running time for Thread must be higher than 1 second, as
    # the lock was locked when thread started.
    assert thread_times[1] - thread_times[0] >= datetime.timedelta(seconds=1)


def test_merge_dicts_recursive():
    # Arrange
    base = {  # type: ignore
        "toplevel_1": 1,
        "toplevel_2": 2,
        "nested_dict": {"default": {"deep_key_1": []}},
    }
    update = {
        "toplevel_1": "One",
        "nested_dict": {"default": {"deep_key_1": True, "deep_key_2": None}},
    }

    expected = {
        "toplevel_1": "One",
        "toplevel_2": 2,
        "nested_dict": {"default": {"deep_key_1": True, "deep_key_2": None}},
    }

    # Act
    result = utils.merge_dicts_recursive(base, update)  # type: ignore

    # Assert
    assert expected == result


def test_merge_dicts_recursive_extend():
    # Arrange
    base = {
        "str-key": "Hello, ",
    }
    update = {
        "str-key": "World!",
    }

    expected = {
        "str-key": "Hello, World!",
    }

    # Act
    result = utils.merge_dicts_recursive(base, update, True)

    # Assert
    assert expected == result


def test_merge_dicts_recursive_extend_deep():
    # Arrange
    base = {
        "default": {"str-key": "Hello, "},
    }
    update = {
        "default": {"str-key": "World!"},
    }

    expected = {
        "default": {"str-key": "Hello, World!"},
    }

    # Act
    result = utils.merge_dicts_recursive(base, update, True)

    # Assert
    assert expected == result


def test_create_files_if_not_existing(tmp_path: Path):
    # Arrange
    file1 = str(tmp_path / "a")
    file2 = str(tmp_path / "b" / "c")
    files = [file1, file2]

    # Act
    utils.create_files_if_not_existing(files)

    # Assert
    assert os.path.exists(file1)
    assert os.path.exists(file2)
