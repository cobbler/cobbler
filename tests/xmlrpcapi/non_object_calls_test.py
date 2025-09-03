"""
Tests that validate the functionality of the module that is responsible for providing XML-RPC calls related to
non object calls.
"""

import os
import re
import time
from typing import Any, Callable, Dict, Union

import pytest

from cobbler.remote import CobblerXMLRPCInterface

from tests.conftest import does_not_raise

WaitTaskEndType = Callable[[str, CobblerXMLRPCInterface], None]
TEST_POWER_MANAGEMENT = True
TEST_SYSTEM = ""


@pytest.fixture(scope="function")
def wait_task_end() -> WaitTaskEndType:
    """
    Wait until a task is finished
    """

    def _wait_task_end(tid: str, remote: CobblerXMLRPCInterface) -> None:
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


def test_token(token: str):
    """
    Test: authentication token validation
    """

    assert token not in ("", None)


def test_get_user_from_token(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get user data from authentication token
    """

    assert remote.get_user_from_token(token)


def test_check(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: check Cobbler status
    """

    assert remote.check(token)


def test_last_modified_time(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get last modification time
    """

    assert remote.last_modified_time(token) != 0


def test_power_system(
    remote: CobblerXMLRPCInterface, token: str, wait_task_end: WaitTaskEndType
):
    """
    Test: reboot a system
    """

    if TEST_SYSTEM and TEST_POWER_MANAGEMENT:
        tid = remote.background_power_system(
            {"systems": [TEST_SYSTEM], "power": "reboot"}, token
        )
        wait_task_end(tid, remote)


def test_sync(
    remote: CobblerXMLRPCInterface, token: str, wait_task_end: WaitTaskEndType
):
    """
    Test: synchronize Cobbler internal data with managed services
    (dhcp, tftp, dns)
    """

    tid = remote.background_sync({}, token)
    events = remote.get_events(token)

    assert len(events) > 0

    wait_task_end(tid, remote)

    event_log = remote.get_event_log(tid)

    assert isinstance(event_log, str)


def test_get_autoinstall_templates(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get autoinstall templates
    """

    result = remote.get_autoinstall_templates(token)
    assert len(result) > 0


def test_get_autoinstall_snippets(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get autoinstall snippets
    """

    result = remote.get_autoinstall_snippets(token)
    assert len(result) > 0


def test_generate_autoinstall(remote: CobblerXMLRPCInterface):
    """
    Test: generate autoinstall content
    """

    if TEST_SYSTEM:
        remote.generate_autoinstall(None, TEST_SYSTEM)


def test_generate_ipxe(remote: CobblerXMLRPCInterface):
    """
    Test: generate iPXE file content
    """

    if TEST_SYSTEM:
        remote.generate_ipxe(None, TEST_SYSTEM)


def test_generate_bootcfg(remote: CobblerXMLRPCInterface):
    """
    Test: generate boot loader configuration file content
    """

    if TEST_SYSTEM:
        remote.generate_bootcfg(None, TEST_SYSTEM)


def test_get_settings(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get settings
    """

    remote.get_settings(token)


def test_get_signatures(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get distro signatures
    """

    remote.get_signatures(token)


def test_get_valid_breeds(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get valid OS breeds
    """

    breeds = remote.get_valid_breeds(token)
    assert len(breeds) > 0


def test_get_valid_os_versions_for_breed(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get valid OS versions for a OS breed
    """

    versions = remote.get_valid_os_versions_for_breed("generic", token)
    assert len(versions) > 0


def test_get_valid_os_versions(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get valid OS versions
    """

    versions = remote.get_valid_os_versions(token)
    assert len(versions) > 0


def test_get_random_mac(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get a random mac for a virtual network interface
    """

    mac = remote.get_random_mac("kvm", token)
    hexa = "[0-9A-Fa-f]{2}"
    match_obj = re.match(
        "%s:%s:%s:%s:%s:%s" % (hexa, hexa, hexa, hexa, hexa, hexa), mac
    )
    assert match_obj


@pytest.mark.parametrize(
    "input_attribute,checked_object,expected_result,expected_exception",
    [
        ("kernel_options", "system", {"a": "1", "b": "2", "d": "~"}, does_not_raise()),
        ("arch", "distro", "x86_64", does_not_raise()),
        ("distro", "profile", "testdistro_item_resolved_value", does_not_raise()),
        ("profile", "system", "<VALUE IGNORED>", does_not_raise()),
        (
            "interfaces",
            "system",
            {
                "eth0": {
                    "bonding_opts": "",
                    "bridge_opts": "",
                    "cnames": [],
                    "connected_mode": False,
                    "dhcp_tag": "",
                    "dns_name": "",
                    "if_gateway": "",
                    "interface_master": "",
                    "interface_type": "na",
                    "ip_address": "",
                    "ipv6_address": "",
                    "ipv6_default_gateway": "",
                    "ipv6_mtu": "",
                    "ipv6_prefix": "",
                    "ipv6_secondaries": [],
                    "ipv6_static_routes": [],
                    "mac_address": "aa:bb:cc:dd:ee:ff",
                    "management": False,
                    "mtu": "",
                    "netmask": "",
                    "static": False,
                    "static_routes": [],
                    "virt_bridge": "virbr0",
                }
            },
            does_not_raise(),
        ),
        ("modify_interface", "system", {}, pytest.raises(ValueError)),
        ("doesnt_exist", "system", {}, pytest.raises(AttributeError)),
    ],
)
def test_get_item_resolved_value(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
    create_system: Callable[[str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
    input_attribute: str,
    checked_object: str,
    expected_result: Union[str, Dict[str, Any]],
    expected_exception: Any,
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

    distro_uid = create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    profile_uid = create_profile(name_profile, distro_uid, "a=1 b=2 c=3 c=4 c=5 d e")
    test_system_handle = create_system(name_system, profile_uid)
    remote.modify_system(test_system_handle, "kernel_options", "!c !e", token=token)
    remote.modify_system(
        test_system_handle,
        "modify_interface",
        {"macaddress-eth0": "aa:bb:cc:dd:ee:ff"},
        token=token,
    )
    if checked_object == "distro":
        test_item = remote.get_distro(name_distro, token=token)
    elif checked_object == "profile":
        test_item = remote.get_profile(name_profile, token=token)
    elif checked_object == "system":
        test_item = remote.get_system(name_system, token=token)
    else:
        raise ValueError("checked_object has wrong value")

    # Act
    with expected_exception:
        result = remote.get_item_resolved_value(test_item.get("uid"), input_attribute)  # type: ignore

        if input_attribute == "interfaces" and "default" in result:  # type: ignore
            result.pop("default")  # type: ignore

        # Assert
        if input_attribute == "profile":
            assert profile_uid == result
        else:
            assert expected_result == result
