"""
Tests that validate the functionality of the module that is responsible for providing XML-RPC calls related to
non object calls.
"""

import os
import re
from typing import Any, Callable, Dict, List, Union

import pytest

from cobbler.remote import CobblerXMLRPCInterface

from tests.conftest import does_not_raise
from tests.integration.conftest import WaitTaskEndType

TEST_POWER_MANAGEMENT = True
TEST_SYSTEM = ""


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


def test_generate_autoinstall(
    create_kernel_initrd: Callable[[str, str], str],
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
    create_system: Callable[[str, str], str],
    create_autoinstall_template: Callable[[str, str], str],
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: generate autoinstall content
    """
    # Arrange
    template_uid = create_autoinstall_template(
        "system-tests.sh",
        "${dns.name_servers} ${server} ${kernel_options}\n",
    )
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
    remote.modify_system(test_system_handle, ["autoinstall"], template_uid, token)

    # Act
    result = remote.generate_autoinstall("", name_system)

    # Assert
    assert result != ""
    assert not result.startswith("# This automatic OS installation file had errors")


def test_generate_autoinstall_empty_string_normalization(
    create_kernel_initrd: Callable[[str, str], str],
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
    create_autoinstall_template: Callable[[str, str], str],
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: generate autoinstall with empty string should normalize to None (issue #3807)
    """
    template_uid = create_autoinstall_template(
        "empty-test.ks",
        "# Test template\n",
    )
    fk_kernel = "vmlinuz2"
    fk_initrd = "initrd2.img"
    name_distro = "testdistro_empty_normalization"
    name_profile = "testprofile_empty_normalization"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)

    distro_uid = create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    _ = create_profile(name_profile, distro_uid, "")
    profile_handle = remote.get_profile_handle(name_profile)
    remote.modify_profile(profile_handle, ["autoinstall"], template_uid, token)
    remote.save_profile(profile_handle, token)

    result = remote.generate_autoinstall(name_profile, "")

    assert result != ""
    assert not result.startswith("# This automatic OS installation file had errors")


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
        (
            ["kernel_options"],
            "system",
            {"a": "1", "b": "2", "d": "~"},
            does_not_raise(),
        ),
        (["arch"], "distro", "x86_64", does_not_raise()),
        (["distro"], "profile", "testdistro_item_resolved_value", does_not_raise()),
        (["profile"], "system", "<VALUE IGNORED>", does_not_raise()),
        (
            ["interfaces"],
            "system",
            {
                "eth0": {
                    "bonding_opts": "",
                    "bridge_opts": "",
                    "comment": "",
                    "connected_mode": False,
                    "ctime": 0.0,
                    "dhcp_tag": "",
                    "dns": {"name": "", "common_names": []},
                    "if_gateway": "",
                    "interface_master": "",
                    "interface_type": "na",
                    "ipv4": {
                        "address": "",
                        "mtu": "",
                        "netmask": "",
                        "static_routes": [],
                    },
                    "ipv6": {
                        "address": "",
                        "default_gateway": "",
                        "mtu": "",
                        "prefix": "",
                        "secondaries": [],
                        "static_routes": [],
                    },
                    "mac_address": "aa:bb:cc:dd:ee:ff",
                    "management": False,
                    "mtime": 0.0,
                    "name": "eth0",
                    "owners": ["admin"],
                    "static": False,
                    "system_uid": "",
                    "uid": "",
                    "virt_bridge": "virbr0",
                }
            },
            does_not_raise(),
        ),
        (["doesnt_exist"], "system", {}, pytest.raises(AttributeError)),
    ],
)
def test_get_item_resolved_value(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
    create_system: Callable[[str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
    input_attribute: List[str],
    checked_object: str,
    expected_result: Union[str, Dict[str, Any]],
    expected_exception: Any,
):
    """
    Verify that getting resolved values via XML-RPC works as expected.
    """
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
    remote.modify_system(test_system_handle, ["kernel_options"], "!c !e", token=token)
    remote.save_system(test_system_handle, token)
    test_network_interface_handle = remote.new_network_interface(
        test_system_handle, token
    )
    remote.modify_network_interface(
        test_network_interface_handle, ["name"], "eth0", token
    )
    remote.modify_network_interface(
        test_network_interface_handle, ["mac_address"], "aa:bb:cc:dd:ee:ff", token
    )
    remote.save_network_interface(test_network_interface_handle, token, "new")
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

        if input_attribute == ["interfaces"] and "default" in result:  # type: ignore
            result.pop("default")  # type: ignore

        # Assert
        if isinstance(result, dict) and "eth0" in result and "ctime" in result["eth0"]:
            result["eth0"]["ctime"] = 0.0
        if isinstance(result, dict) and "eth0" in result and "mtime" in result["eth0"]:
            result["eth0"]["mtime"] = 0.0
        if isinstance(result, dict) and "eth0" in result and "uid" in result["eth0"]:
            result["eth0"]["uid"] = ""
        if (
            isinstance(result, dict)
            and "eth0" in result
            and "system_uid" in result["eth0"]
        ):
            result["eth0"]["system_uid"] = ""
        if input_attribute == ["profile"]:
            assert profile_uid == result
        else:
            assert expected_result == result
