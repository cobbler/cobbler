"""
Test module that contains all tests that are related to XML-RPC methods that perform actions with a Cobbler system.
"""

import os
from typing import Any, Callable, List, Union

import pytest

from cobbler.cexceptions import CX
from cobbler.remote import CobblerXMLRPCInterface


def test_get_systems(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get systems
    """
    # Arrange --> Nothing to arrange

    # Act
    result = remote.get_systems(token)

    # Assert
    assert result == []


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
@pytest.mark.parametrize(
    "field_name,field_value",
    [
        (["comment"], "test comment"),
        (["enable_ipxe"], True),
        (["enable_ipxe"], False),
        (["kernel_options"], "a=1 b=2 c=3 c=4 c=5 d e"),
        (["kernel_options_post"], "a=1 b=2 c=3 c=4 c=5 d e"),
        (["autoinstall"], "test.ks"),
        (["autoinstall"], "test.xml"),
        (["autoinstall"], "test.seed"),
        (["autoinstall_meta"], "a=1 b=2 c=3 c=4 c=5 d e"),
        (["name"], "testsystem0"),
        (["netboot_enabled"], True),
        (["netboot_enabled"], False),
        (["owners"], "user1 user2 user3"),
        (["profile"], "<VALUE IGNORED>"),
        (["repos_enabled"], True),
        (["repos_enabled"], False),
        (["status"], "development"),
        (["status"], "testing"),
        (["status"], "acceptance"),
        (["status"], "production"),
        (["proxy"], "testproxy"),
        (["server"], "1.1.1.1"),
        (["boot_loaders"], "pxe ipxe grub"),
        (["virt", "auto_boot"], True),
        (["virt", "auto_boot"], False),
        (["virt", "auto_boot"], "yes"),
        (["virt", "auto_boot"], "no"),
        (["virt", "cpus"], "<<inherit>>"),
        (["virt", "cpus"], 1),
        (["virt", "cpus"], 2),
        (["virt", "cpus"], "<<inherit>>"),
        (["virt", "file_size"], "<<inherit>>"),
        (["virt", "file_size"], 5),
        (["virt", "file_size"], 10),
        (["virt", "disk_driver"], "<<inherit>>"),
        (["virt", "disk_driver"], "raw"),
        (["virt", "disk_driver"], "qcow2"),
        (["virt", "disk_driver"], "vdmk"),
        (["virt", "ram"], "<<inherit>>"),
        (["virt", "ram"], 256),
        (["virt", "ram"], 1024),
        (["virt", "type"], "<<inherit>>"),
        (["virt", "type"], "xenpv"),
        (["virt", "type"], "xenfv"),
        (["virt", "type"], "qemu"),
        (["virt", "type"], "kvm"),
        (["virt", "type"], "vmware"),
        (["virt", "type"], "openvz"),
        (["virt", "path"], "<<inherit>>"),
        (["virt", "path"], "/path/to/test"),
        (["virt", "pxe_boot"], True),
        (["virt", "pxe_boot"], False),
        (["power", "type"], "ipmilanplus"),
        (["power", "address"], "127.0.0.1"),
        (["power", "id"], "pmachine:lpar1"),
        (["power", "pass"], "pass"),
        (["power", "user"], "user"),
    ],
)
def test_create_system_positive(
    remote: CobblerXMLRPCInterface,
    token: str,
    template_files: Any,
    field_name: List[str],
    field_value: Union[str, bool, int],
):
    """
    Test: create/edit a system object
    """
    # Arrange
    profile_uid = remote.get_profile_handle("testprofile0")
    system = remote.new_system(token)
    remote.modify_system(system, ["name"], "testsystem0", token)
    remote.modify_system(system, ["profile"], profile_uid, token)
    if field_name == ["profile"]:
        field_value = profile_uid

    # Act
    result = remote.modify_system(system, field_name, field_value, token)

    # Assert
    assert result


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
@pytest.mark.parametrize(
    "field_name,field_value",
    [
        (["autoinstall"], "/path/to/bad/autoinstall"),
        (["profile"], "badprofile"),
        (["boot_loaders"], "badloader"),
        (["virt", "cpus"], "a"),
        (["virt", "file_size"], "a"),
        (["virt", "ram"], "a"),
        (["virt", "type"], "bad"),
        (["power", "type"], "bla"),
    ],
)
def test_create_system_negative(
    remote: CobblerXMLRPCInterface, token: str, field_name: List[str], field_value: str
):
    """
    Test: create/edit a system object
    """
    # Arrange
    profile_uid = remote.get_profile_handle("testprofile0")
    system = remote.new_system(token)
    remote.modify_system(system, ["name"], "testsystem0", token)
    remote.modify_system(system, ["profile"], profile_uid, token)

    # Act & Assert
    try:
        remote.modify_system(system, field_name, field_value, token)
    except (CX, TypeError, ValueError, OSError):
        assert True
    else:
        pytest.fail("Bad field did not raise an exception!")


def test_find_system(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: find a system object
    """

    # Arrange --> Nothing to arrange

    # Act
    result = remote.find_system(criteria={"name": "notexisting"}, token=token)

    # Assert --> A not exiting system returns an empty list
    assert result == []


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "create_testsystem",
)
def test_copy_system(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: copy a system object
    """
    # Arrange
    system = remote.get_item_handle("system", "testsystem0")

    # Act
    result = remote.copy_system(system, "testsystemcopy", token)

    # Assert
    assert result


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "create_testsystem",
)
def test_rename_system(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: rename a system object
    """

    # Arrange --> Done in fixtures also.
    system = remote.get_item_handle("system", "testsystem0")

    # Act
    result = remote.rename_system(system, "testsystem1", token)

    # Assert
    assert result


def test_remove_system(
    request: "pytest.FixtureRequest",
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
    create_system: Callable[[str, str], str],
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: remove a system object
    """
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    distro_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    profile_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    system_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    kernel_path = os.path.join(folder, fk_kernel)
    initrd_path = os.path.join(folder, fk_initrd)
    distro_handle = create_distro(distro_name, "x86_64", "suse", kernel_path, initrd_path)  # type: ignore
    profile_handle = create_profile(profile_name, distro_handle, "")  # type: ignore
    create_system(system_name, profile_handle)  # type: ignore

    # Act
    result = remote.remove_system(system_name, token)  # type: ignore

    # Assert
    assert result


def test_get_repo_config_for_system(remote: CobblerXMLRPCInterface):
    """
    Test: get repository configuration of a system
    """

    # Arrange --> There is nothing to be arranged

    # Act
    result = remote.get_repo_config_for_system("testprofile0")  # type: ignore

    # Assert --> Let the test pass if the call is okay.
    assert True


def test_dns_name_servers_inheritance(
    request: "pytest.FixtureRequest",
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
    create_system: Callable[[str, str], str],
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Tests that DNS name servers are correctly inherited and resolved for a system when both the profile and the system
    specify their own DNS name servers.
    """
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    distro_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    profile_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    system_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    kernel_path = os.path.join(folder, fk_kernel)
    initrd_path = os.path.join(folder, fk_initrd)
    distro_handle = create_distro(distro_name, "x86_64", "suse", kernel_path, initrd_path)  # type: ignore
    profile_handle = create_profile(profile_name, distro_handle, "")  # type: ignore
    system_handle = create_system(system_name, profile_handle)  # type: ignore

    # Act
    remote.modify_profile(profile_handle, ["dns", "name_servers"], "8.8.4.4", token)
    remote.save_profile(profile_handle, token)
    remote.modify_system(system_handle, ["dns", "name_servers"], "8.8.8.8", token)
    remote.save_system(system_handle, token)

    # Assert
    assert remote.get_item_resolved_value(system_handle, ["dns", "name_servers"]) == [
        "8.8.4.4",
        "8.8.8.8",
    ]
