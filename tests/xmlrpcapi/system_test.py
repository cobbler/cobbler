"""
Test module that contains all tests that are related to XML-RPC methods that perform actions with a Cobbler system.
"""

import os
from typing import Any, Callable, Union

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
        ("comment", "test comment"),
        ("enable_ipxe", True),
        ("enable_ipxe", False),
        ("kernel_options", "a=1 b=2 c=3 c=4 c=5 d e"),
        ("kernel_options_post", "a=1 b=2 c=3 c=4 c=5 d e"),
        ("autoinstall", "test.ks"),
        ("autoinstall", "test.xml"),
        ("autoinstall", "test.seed"),
        ("autoinstall_meta", "a=1 b=2 c=3 c=4 c=5 d e"),
        ("name", "testsystem0"),
        ("netboot_enabled", True),
        ("netboot_enabled", False),
        ("owners", "user1 user2 user3"),
        ("profile", "testprofile0"),
        ("repos_enabled", True),
        ("repos_enabled", False),
        ("status", "development"),
        ("status", "testing"),
        ("status", "acceptance"),
        ("status", "production"),
        ("proxy", "testproxy"),
        ("server", "1.1.1.1"),
        # ("boot_loaders", "pxe ipxe grub"), FIXME: This raises currently but it did not in the past
        ("virt_auto_boot", True),
        ("virt_auto_boot", False),
        ("virt_auto_boot", "yes"),
        ("virt_auto_boot", "no"),
        ("virt_cpus", "<<inherit>>"),
        ("virt_cpus", 1),
        ("virt_cpus", 2),
        ("virt_cpus", "<<inherit>>"),
        ("virt_file_size", "<<inherit>>"),
        ("virt_file_size", 5),
        ("virt_file_size", 10),
        ("virt_disk_driver", "<<inherit>>"),
        ("virt_disk_driver", "raw"),
        ("virt_disk_driver", "qcow2"),
        ("virt_disk_driver", "vdmk"),
        ("virt_ram", "<<inherit>>"),
        ("virt_ram", 256),
        ("virt_ram", 1024),
        ("virt_type", "<<inherit>>"),
        ("virt_type", "xenpv"),
        ("virt_type", "xenfv"),
        ("virt_type", "qemu"),
        ("virt_type", "kvm"),
        ("virt_type", "vmware"),
        ("virt_type", "openvz"),
        ("virt_path", "<<inherit>>"),
        ("virt_path", "/path/to/test"),
        ("virt_pxe_boot", True),
        ("virt_pxe_boot", False),
        ("power_type", "ipmilanplus"),
        ("power_address", "127.0.0.1"),
        ("power_id", "pmachine:lpar1"),
        ("power_pass", "pass"),
        ("power_user", "user"),
    ],
)
def test_create_system_positive(
    remote: CobblerXMLRPCInterface,
    token: str,
    template_files: Any,
    field_name: str,
    field_value: Union[str, bool, int],
):
    """
    Test: create/edit a system object
    """
    # Arrange
    system = remote.new_system(token)
    remote.modify_system(system, "name", "testsystem0", token)
    remote.modify_system(system, "profile", "testprofile0", token)

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
        ("autoinstall", "/path/to/bad/autoinstall"),
        ("profile", "badprofile"),
        ("boot_loaders", "badloader"),
        ("virt_cpus", "a"),
        ("virt_file_size", "a"),
        ("virt_ram", "a"),
        ("virt_type", "bad"),
        ("power_type", "bla"),
    ],
)
def test_create_system_negative(
    remote: CobblerXMLRPCInterface, token: str, field_name: str, field_value: str
):
    """
    Test: create/edit a system object
    """
    # Arrange
    system = remote.new_system(token)
    remote.modify_system(system, "name", "testsystem0", token)
    remote.modify_system(system, "profile", "testprofile0", token)

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
)
def test_add_interface_to_system(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: add an interface to a system
    """

    # Arrange
    system = remote.new_system(token)
    remote.modify_system(system, "name", "testsystem0", token)
    remote.modify_system(system, "profile", "testprofile0", token)

    # Act
    result = remote.modify_system(
        system, "modify_interface", {"macaddress-eth0": "aa:bb:cc:dd:ee:ff"}, token
    )
    remote.save_system(system, token)

    # Assert --> returns true if successful
    assert result
    assert (
        remote.get_system("testsystem0")
        .get("interfaces", {})  # type: ignore
        .get("eth0", {})
        .get("mac_address")
        == "aa:bb:cc:dd:ee:ff"
    )


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
def test_remove_interface_from_system(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: remove an interface from a system
    """

    # Arrange
    system = remote.new_system(token)
    remote.modify_system(system, "name", "testsystem0", token)
    remote.modify_system(system, "profile", "testprofile0", token)
    remote.modify_system(
        system, "modify_interface", {"macaddress-eth0": "aa:bb:cc:dd:ee:ff"}, token
    )
    remote.save_system(system, token)

    # Act
    result = remote.modify_system(
        system, "delete_interface", {"interface": "eth0"}, token
    )
    remote.save_system(system, token)

    # Assert --> returns true if successful
    assert result
    assert (
        remote.get_system("testsystem0").get("interfaces", {}).get("eth0", None)  # type: ignore
        is None
    )


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
def test_rename_interface(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: rename an interface on a system
    """

    # Arrange
    system = remote.new_system(token)
    remote.modify_system(system, "name", "testsystem0", token)
    remote.modify_system(system, "profile", "testprofile0", token)
    result_add = remote.modify_system(
        system, "modify_interface", {"macaddress-eth0": "aa:bb:cc:dd:ee:ff"}, token
    )
    remote.save_system(system, token)

    # Act
    result_rename = remote.modify_system(
        system,
        "rename_interface",
        {"interface": "eth0", "rename_interface": "eth_new"},
        token,
    )
    remote.save_system(system, token)

    # Assert --> returns true if successful
    assert result_add
    assert result_rename
    assert (
        remote.get_system("testsystem0").get("interfaces", {}).get("eth0", None)  # type: ignore
        is None
    )
    assert (
        remote.get_system("testsystem0")
        .get("interfaces", {})  # type: ignore
        .get("eth_new", {})
        .get("mac_address")
        == "aa:bb:cc:dd:ee:ff"
    )


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
    create_distro(distro_name, "x86_64", "suse", kernel_path, initrd_path)  # type: ignore
    create_profile(profile_name, distro_name, "")  # type: ignore
    create_system(system_name, profile_name)  # type: ignore

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
