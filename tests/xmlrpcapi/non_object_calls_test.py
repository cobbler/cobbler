import os

import pytest
import time
import re

TEST_POWER_MANAGEMENT = True
TEST_SYSTEM = ""


@pytest.fixture(scope="function")
def wait_task_end():
    """
    Wait until a task is finished
    """

    def _wait_task_end(tid, remote):
        timeout = 0
        # "complete" is the constant: EVENT_COMPLETE from cobbler.remote
        while remote.get_task_status(tid)[2] != "complete":
            if remote.get_task_status(tid)[2] == "failed":
                pytest.fail("Task failed")
            print("task %s status: %s" % (tid, remote.get_task_status(tid)))
            time.sleep(5)
            timeout += 5
            if timeout == 60:
                raise Exception

    return _wait_task_end


def test_token(token):
    """
    Test: authentication token validation
    """

    assert token not in ("", None)


def test_get_user_from_token(remote, token):
    """
    Test: get user data from authentication token
    """

    assert remote.get_user_from_token(token)


def test_check(remote, token):
    """
    Test: check Cobbler status
    """

    assert remote.check(token)


def test_last_modified_time(remote, token):
    """
    Test: get last modification time
    """

    assert remote.last_modified_time(token) != 0


def test_power_system(remote, token, wait_task_end):
    """
    Test: reboot a system
    """

    if TEST_SYSTEM and TEST_POWER_MANAGEMENT:
        tid = remote.background_power_system({"systems": [TEST_SYSTEM], "power": "reboot"}, token)
        wait_task_end(tid, remote)


def test_sync(remote, token, wait_task_end):
    """
    Test: synchronize Cobbler internal data with managed services
    (dhcp, tftp, dns)
    """

    tid = remote.background_sync({}, token)
    events = remote.get_events(token)

    assert len(events) > 0

    wait_task_end(tid, remote)

    event_log = remote.get_event_log(tid)


def test_get_autoinstall_templates(remote, token):
    """
    Test: get autoinstall templates
    """

    result = remote.get_autoinstall_templates(token)
    assert len(result) > 0


def test_get_autoinstall_snippets(remote, token):
    """
    Test: get autoinstall snippets
    """

    result = remote.get_autoinstall_snippets(token)
    assert len(result) > 0


def test_generate_autoinstall(remote):
    """
    Test: generate autoinstall content
    """

    if TEST_SYSTEM:
        remote.generate_autoinstall(None, TEST_SYSTEM)


def test_generate_ipxe(remote):
    """
    Test: generate iPXE file content
    """

    if TEST_SYSTEM:
        remote.generate_ipxe(None, TEST_SYSTEM)


def test_generate_bootcfg(remote):
    """
    Test: generate boot loader configuration file content
    """

    if TEST_SYSTEM:
        remote.generate_bootcfg(None, TEST_SYSTEM)


def test_get_settings(remote, token):
    """
    Test: get settings
    """

    remote.get_settings(token)


def test_get_signatures(remote, token):
    """
    Test: get distro signatures
    """

    remote.get_signatures(token)


def test_get_valid_breeds(remote, token):
    """
    Test: get valid OS breeds
    """

    breeds = remote.get_valid_breeds(token)
    assert len(breeds) > 0


def test_get_valid_os_versions_for_breed(remote, token):
    """
    Test: get valid OS versions for a OS breed
    """

    versions = remote.get_valid_os_versions_for_breed("generic", token)
    assert len(versions) > 0


def test_get_valid_os_versions(remote, token):
    """
    Test: get valid OS versions
    """

    versions = remote.get_valid_os_versions(token)
    assert len(versions) > 0


def test_get_random_mac(remote, token):
    """
    Test: get a random mac for a virtual network interface
    """

    mac = remote.get_random_mac("xen", token)
    hexa = "[0-9A-Fa-f]{2}"
    match_obj = re.match("%s:%s:%s:%s:%s:%s" % (hexa, hexa, hexa, hexa, hexa, hexa), mac)
    assert match_obj


def test_get_item_resolved_value(
    remote, token, create_distro, create_profile, create_system, create_kernel_initrd
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    name_distro = "testdistro_item_resolved_value"
    name_profile = "testprofile_item_resolved_value"
    name_system = "testsystem_item_resolved_value"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)

    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "a=1 b=2 c=3 c=4 c=5 d e")
    test_system_handle = create_system(name_system, name_profile)
    remote.modify_system(test_system_handle, "kernel_options", "!c !e", token=token)
    test_system = remote.get_system(name_system, token=token)
    expected_result = {"a": "1", "b": "2", "d": None}

    # Act
    result = remote.get_item_resolved_value(test_system.get("uid"), "kernel_options")

    # Assert
    assert expected_result == result
