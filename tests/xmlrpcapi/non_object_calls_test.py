"""
Tests that validate the functionality of the module that is responsible for providing XML-RPC calls related to
non object calls.
"""

import os
import re
from typing import Any, Callable, Dict, List, Union

import pytest

from cobbler.cexceptions import CX
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


def test_background_power_system(
    remote: CobblerXMLRPCInterface,
    token: str,
    wait_task_end: WaitTaskEndType,
    create_kernel_initrd: Callable[[str, str], str],
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
    create_system: Callable[[str, str], str],
):
    """
    Test: power a system asynchronously in the background, identified by its uid
    """
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(folder, fk_kernel)
    path_initrd = os.path.join(folder, fk_initrd)
    distro_uid = create_distro(
        "test_distro_background_power_system",
        "x86_64",
        "suse",
        path_kernel,
        path_initrd,
    )
    profile_uid = create_profile("test_profile_background_power_system", distro_uid, "")
    system_uid = create_system("test_system_background_power_system", profile_uid)

    # Act
    tid = remote.background_power_system(
        {"systems": [system_uid], "power": "status"}, token
    )
    wait_task_end(tid, remote)


def test_background_syncsystems(
    remote: CobblerXMLRPCInterface,
    token: str,
    wait_task_end: WaitTaskEndType,
    create_kernel_initrd: Callable[[str, str], str],
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
    create_system: Callable[[str, str], str],
):
    """
    Test: run a lite sync for a single system, identified by its uid
    """
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(folder, fk_kernel)
    path_initrd = os.path.join(folder, fk_initrd)
    distro_uid = create_distro(
        "test_distro_background_syncsystems", "x86_64", "suse", path_kernel, path_initrd
    )
    profile_uid = create_profile("test_profile_background_syncsystems", distro_uid, "")
    system_uid = create_system("test_system_background_syncsystems", profile_uid)

    # Act
    tid = remote.background_syncsystems({"systems": [system_uid]}, token)
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
    result = remote.generate_autoinstall(name_system, "system", "name", "")

    # Assert
    assert result != ""


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
                    "ipv6_default_gateway": "",
                    "ipv6_static_routes": [],
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
        (
            ["power"],
            "system",
            {
                "address": "",
                "id": "",
                "identity_file": "",
                "options": "",
                "password": "",
                "type": "",
                "user": "",
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
    remote.save_system(test_system_handle, True, True, "bypass", token)
    test_network_interface_handle = remote.new_network_interface(
        test_system_handle, token
    )
    remote.modify_network_interface(
        test_network_interface_handle, ["name"], "eth0", token
    )
    remote.modify_network_interface(
        test_network_interface_handle, ["mac_address"], "aa:bb:cc:dd:ee:ff", token
    )
    remote.save_network_interface(
        test_network_interface_handle, True, True, "new", token
    )
    if checked_object == "distro":
        test_item = remote.get_distro(distro_uid, token=token)
    elif checked_object == "profile":
        test_item = remote.get_profile(profile_uid, token=token)
    elif checked_object == "system":
        test_item = remote.get_system(test_system_handle, token=token)
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


def test_remove_item_with_duplicate_names(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
    create_system: Callable[[str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    """
    Verify that an item can be removed via its handle even if its name is not globally unique.

    Network interface names are only unique per system, so two systems may both own an interface called "eth0". Since
    ``remove_network_interface`` takes an object id, the caller can address exactly one of them.
    """
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    distro_uid = create_distro(
        "testdistro_duplicate_names", "x86_64", "suse", path_kernel, path_initrd
    )
    profile_uid = create_profile("testprofile_duplicate_names", distro_uid, "")
    system_uids = [
        create_system(f"testsystem_duplicate_names{i}", profile_uid) for i in range(2)
    ]
    for system_uid in system_uids:
        interface_handle = remote.new_network_interface(system_uid, token)
        remote.modify_network_interface(interface_handle, ["name"], "eth0", token)
        remote.save_network_interface(interface_handle, True, True, "new", token)

    # The name alone is ambiguous, so a handle has to be obtained via a more specific search.
    with pytest.raises(CX):
        remote.get_network_interface_handle("eth0")
    interfaces = remote.find_network_interface(
        {"system_uid": system_uids[0], "name": "eth0"}, expand=True, token=token
    )
    assert len(interfaces) == 1
    interface_uid = interfaces[0]["uid"]

    # Act
    result = remote.remove_network_interface(interface_uid, token, False)

    # Assert
    assert result is True
    assert (
        remote.find_network_interface(
            {"system_uid": system_uids[0], "name": "eth0"}, token=token
        )
        == []
    )
    assert (
        len(
            remote.find_network_interface(
                {"system_uid": system_uids[1], "name": "eth0"}, token=token
            )
        )
        == 1
    )


def test_remove_item_with_name_instead_of_handle(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    """
    Verify that passing a name instead of an object id to ``remove_*`` does not remove anything.
    """
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    distro_name = "testdistro_name_instead_of_handle"
    distro_uid = create_distro(distro_name, "x86_64", "suse", path_kernel, path_initrd)

    # Act
    result = remote.remove_distro(distro_name, token, False)

    # Assert
    assert result is False
    assert remote.get_distro_handle(distro_name) == distro_uid

    # Cleanup
    assert remote.remove_distro(distro_uid, token, False) is True


def test_get_item_with_duplicate_names(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
    create_system: Callable[[str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    """
    Verify that an item can be retrieved via its handle even if its name is not globally unique.

    Network interface names are only unique per system, so two systems may both own an interface called "eth0". Since
    ``get_network_interface`` takes an object id, the caller can address exactly one of them.
    """
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    distro_uid = create_distro(
        "testdistro_get_duplicate_names", "x86_64", "suse", path_kernel, path_initrd
    )
    profile_uid = create_profile("testprofile_get_duplicate_names", distro_uid, "")
    system_uids = [
        create_system(f"testsystem_get_duplicate_names{i}", profile_uid)
        for i in range(2)
    ]
    interface_uids: List[str] = []
    for i, system_uid in enumerate(system_uids):
        interface_handle = remote.new_network_interface(system_uid, token)
        remote.modify_network_interface(interface_handle, ["name"], "eth0", token)
        remote.modify_network_interface(
            interface_handle, ["mac_address"], f"aa:bb:cc:dd:ee:0{i}", token
        )
        remote.save_network_interface(interface_handle, True, True, "new", token)
        interface_uids.append(interface_handle)

    # The name alone is ambiguous, so a handle has to be obtained via a more specific search.
    with pytest.raises(CX):
        remote.get_network_interface_handle("eth0")

    # Act & Assert
    first_interface = remote.get_network_interface(interface_uids[0], token=token)
    assert isinstance(first_interface, dict)
    assert first_interface.get("mac_address") == "aa:bb:cc:dd:ee:00"

    second_interface = remote.get_network_interface(interface_uids[1], token=token)
    assert isinstance(second_interface, dict)
    assert second_interface.get("mac_address") == "aa:bb:cc:dd:ee:01"


def test_find_items_does_not_crash_on_fully_duplicate_names(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
    create_system: Callable[[str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    """
    Verify that find_<type>/find_items doesn't crash when two or more items tie on every field
    the results are sorted by.

    Network interface names are only unique per system, so two systems may both own an interface
    called "eth0" - an unscoped ``find_network_interface({"name": "eth0"})`` then legitimately
    returns two items with an identical sort key. CobblerXMLRPCInterface.__sort() previously fell
    back to comparing the ITEM objects themselves once their sort_key() values tied, and ITEM
    doesn't implement rich comparison, raising "TypeError: '<' not supported between instances of
    'NetworkInterface' and 'NetworkInterface'".
    """
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    distro_uid = create_distro(
        "testdistro_find_duplicate_names", "x86_64", "suse", path_kernel, path_initrd
    )
    profile_uid = create_profile("testprofile_find_duplicate_names", distro_uid, "")
    system_uids = [
        create_system(f"testsystem_find_duplicate_names{i}", profile_uid)
        for i in range(2)
    ]
    for system_uid in system_uids:
        interface_handle = remote.new_network_interface(system_uid, token)
        remote.modify_network_interface(interface_handle, ["name"], "eth0", token)
        remote.save_network_interface(interface_handle, True, True, "new", token)

    # Act
    interfaces = remote.find_network_interface(
        {"name": "eth0"}, expand=True, token=token
    )

    # Assert
    assert len(interfaces) == 2


def test_get_item_with_name_instead_of_handle(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    """
    Verify that passing a name instead of an object id to ``get_item``/``get_<type>`` does not return the object.
    """
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    distro_name = "testdistro_get_name_instead_of_handle"
    distro_uid = create_distro(distro_name, "x86_64", "suse", path_kernel, path_initrd)

    # Act & Assert
    assert remote.get_distro(distro_name) == "~"
    assert remote.get_item("distro", distro_name) == "~"
    assert remote.get_distro(distro_uid).get("name") == distro_name  # type: ignore
