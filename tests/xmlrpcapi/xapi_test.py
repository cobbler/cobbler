"""
All tests that are realted to ensuring the xapi_object_edit functionallity.
"""

import os
from typing import Callable

import pytest

from cobbler.remote import CobblerXMLRPCInterface


def test_xapi_object_edit(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
):
    """
    Test that asserts that objects can be successfully edited.
    """
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    name = "testdistro_xapi_edit"

    # Act
    result = remote.xapi_object_edit(
        "distro",
        name,
        "add",
        {
            "name": name,
            "arch": "x86_64",
            "breed": "suse",
            "kernel": path_kernel,
            "initrd": path_initrd,
        },
        token,
    )

    # Assert
    assert result


def test_xapi_system_edit(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
):
    """
    Test that asserts if system objects can be correctly edited.
    """
    # Arrange
    name_distro = "testsystem_xapi_edit"
    name_profile = "testsystem_xapi_edit"
    name_system = "testsystem_xapi_edit"
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "a=1 b=2 c=3 c=4 c=5 d e")

    # Act
    result = remote.xapi_object_edit(
        "system",
        name_system,
        "add",
        {
            "name": name_system,
            "profile": name_profile,
        },
        token,
    )

    # Assert
    assert result
    # There won't be any interface until the user adds implicitly or explicitly the first interface
    assert len(remote.get_system("testsystem_xapi_edit").get("interfaces", {})) == 0


def test_xapi_system_edit_interface_name(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
):
    """
    TODO
    """
    # Arrange
    name_distro = "testsystem_xapi_edit"
    name_profile = "testsystem_xapi_edit"
    name_system = "testsystem_xapi_edit"
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "a=1 b=2 c=3 c=4 c=5 d e")

    # Act
    result = remote.xapi_object_edit(
        "system",
        name_system,
        "add",
        {
            "name": name_system,
            "profile": name_profile,
            "interface": "eth1",
        },
        token,
    )

    # Assert
    assert result
    assert len(remote.get_system("testsystem_xapi_edit").get("interfaces", {})) == 1
    assert "eth1" in remote.get_system("testsystem_xapi_edit").get("interfaces", {})


def test_xapi_system_edit_two_interfaces_no_default(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
):
    """
    Test that asserts that more then one interface can be added successfully.
    """
    # Arrange
    name_distro = "testsystem_xapi_edit"
    name_profile = "testsystem_xapi_edit"
    name_system = "testsystem_xapi_edit"
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "a=1 b=2 c=3 c=4 c=5 d e")

    # Act
    result_add = remote.xapi_object_edit(
        "system",
        name_system,
        "add",
        {
            "name": name_system,
            "profile": name_profile,
            "interface": "eth1",
        },
        token,
    )
    result_edit = remote.xapi_object_edit(
        "system",
        name_system,
        "edit",
        {
            "name": name_system,
            "interface": "eth2",
        },
        token,
    )

    # Assert
    assert result_add
    assert result_edit
    assert len(remote.get_system("testsystem_xapi_edit").get("interfaces", {})) == 2
    assert "eth1" in remote.get_system("testsystem_xapi_edit").get("interfaces", {})
    assert "eth2" in remote.get_system("testsystem_xapi_edit").get("interfaces", {})


def test_xapi_system_edit_two_interfaces_default(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
):
    """
    Test that asserts that on a system with a single interface that has not the name "default", the correct network
    interface key is edited.
    """
    # Arrange
    name_distro = "testsystem_xapi_edit"
    name_profile = "testsystem_xapi_edit"
    name_system = "testsystem_xapi_edit"
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "a=1 b=2 c=3 c=4 c=5 d e")
    remote.xapi_object_edit(
        "system",
        name_system,
        "add",
        {
            "name": name_system,
            "profile": name_profile,
        },
        token,
    )
    remote.xapi_object_edit(
        "system",
        name_system,
        "edit",
        {
            "name": name_system,
            "interface": "eth2",
        },
        token,
    )

    # Act
    result = remote.xapi_object_edit(
        "system",
        name_system,
        "edit",
        {
            "name": name_system,
            "mac_address": "aa:bb:cc:dd:ee:ff",
        },
        token,
    )

    # Assert
    assert result
    assert (
        remote.get_system(name_system)
        .get("interfaces", {})
        .get("eth2", {})
        .get("mac_address")
        == "aa:bb:cc:dd:ee:ff"
    )


def test_xapi_system_edit_two_interfaces_no_default_negative(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
):
    """
    Test that asserts that on a system with two interfaces, you must pass the interface name if you edit an interface
    specifc field.
    """
    # Arrange
    name_distro = "testsystem_xapi_edit"
    name_profile = "testsystem_xapi_edit"
    name_system = "testsystem_xapi_edit"
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "a=1 b=2 c=3 c=4 c=5 d e")
    remote.xapi_object_edit(
        "system",
        name_system,
        "add",
        {
            "name": name_system,
            "profile": name_profile,
            "interface": "eth1",
        },
        token,
    )
    remote.xapi_object_edit(
        "system",
        name_system,
        "edit",
        {
            "name": name_system,
            "interface": "eth2",
        },
        token,
    )

    # Act & Assert
    with pytest.raises(ValueError):
        remote.xapi_object_edit(
            "system",
            name_system,
            "edit",
            {
                "name": name_system,
                "mac_address": "aa:bb:cc:dd:ee:ff",
            },
            token,
        )
