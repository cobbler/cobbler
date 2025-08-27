import os
from typing import Any, Callable

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.remote import CobblerXMLRPCInterface


@pytest.fixture(autouse=True)
def cleanup_create_distro_positive(cobbler_api: CobblerAPI):
    yield
    cobbler_api.remove_distro("create_distro_positive")


def test_get_distros(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get distros
    """
    # Arrange --> Nothing to arrange

    # Act
    result = remote.get_distros(token)

    # Assert
    assert result == []


@pytest.mark.parametrize(
    "field_name,field_value",
    [
        ("arch", "i386"),
        ("breed", "debian"),
        ("breed", "freebsd"),
        ("breed", "redhat"),
        ("breed", "suse"),
        ("breed", "ubuntu"),
        ("breed", "unix"),
        ("breed", "vmware"),
        ("breed", "windows"),
        ("breed", "xen"),
        ("breed", "generic"),
        ("comment", "test comment"),
        ("initrd", ""),
        ("name", "testdistro0"),
        ("kernel", ""),
        ("kernel_options", "a=1 b=2 c=3 c=4 c=5 d e"),
        ("kernel_options_post", "a=1 b=2 c=3 c=4 c=5 d e"),
        ("autoinstall_meta", "a=1 b=2 c=3 c=4 c=5 d e"),
        ("os_version", "rhel4"),
        ("owners", "user1 user2 user3"),
        ("boot_loaders", "pxe ipxe grub"),
    ],
)
def test_create_distro_positive(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
    field_name: str,
    field_value: str,
    cleanup_create_distro_positive: Any,
):
    """
    Test: create/edit a distro with valid values
    """
    # Arrange --> Nothing to do.
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    distro = remote.new_distro(token)
    remote.modify_distro(distro, "name", "create_distro_positive", token)

    # Act
    if field_name == "kernel":
        field_value = os.path.join(folder, fk_kernel)
    if field_name == "initrd":
        field_value = os.path.join(folder, fk_initrd)
    result = remote.modify_distro(distro, field_name, field_value, token)

    # Assert
    assert result


@pytest.mark.parametrize(
    "field_name,field_value",
    [
        ("arch", "badarch"),
        ("breed", "badbreed"),
        # ("boot_loader", "badloader") FIXME: This does not raise but did in the past
    ],
)
def test_create_distro_negative(
    remote: CobblerXMLRPCInterface, token: str, field_name: str, field_value: str
):
    """
    Test: create/edit a distro with invalid values
    """
    # Arrange
    distro = remote.new_distro(token)
    remote.modify_distro(distro, "name", "testdistro0", token)

    # Act & Assert
    try:
        remote.modify_distro(distro, field_name, field_value, token)
    except (CX, TypeError, ValueError):
        assert True
    else:
        pytest.fail("Bad field did not raise an exception!")


@pytest.mark.usefixtures("create_testdistro", "remove_testdistro")
def test_get_distro(remote: CobblerXMLRPCInterface, fk_initrd: str, fk_kernel: str):
    """
    Test: get a distro object
    """
    # Arrange --> Done in fixture

    # Act
    distro = remote.get_distro("testdistro0")

    # Assert
    assert distro.get("name") == "testdistro0"  # type: ignore
    assert distro.get("redhat_management_key") == enums.VALUE_INHERITED  # type: ignore
    assert distro.get("redhat_management_org") == enums.VALUE_INHERITED  # type: ignore
    assert distro.get("redhat_management_user") == enums.VALUE_INHERITED  # type: ignore
    assert distro.get("redhat_management_password") == enums.VALUE_INHERITED  # type: ignore
    assert fk_initrd in distro.get("initrd")  # type: ignore
    assert fk_kernel in distro.get("kernel")  # type: ignore


def test_get_system(remote: CobblerXMLRPCInterface):
    """
    Test: get a system object
    """
    # Arrange --> There should be no system present. --> Nothing to Init.

    # Act
    system = remote.get_system("testsystem0")

    # Assert
    assert system is "~"


def test_find_distro(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: find a distro object
    """
    # Arrange --> No distros means no setup

    # Act
    result = remote.find_distro(criteria={"name": "testdistro0"}, token=token)

    # Assert
    assert result == []


@pytest.mark.usefixtures("create_testdistro", "remove_testdistro")
def test_copy_distro(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: copy a distro object
    """
    # Arrange --> Done in the fixture

    # Act
    distro = remote.get_item_handle("distro", "testdistro0")
    result = remote.copy_distro(distro, "testdistrocopy", token)

    # Assert
    assert result

    # Cleanup --> Plus fixture
    remote.remove_distro("testdistrocopy", token)


@pytest.mark.usefixtures("create_testdistro")
def test_rename_distro(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: rename a distro object
    """
    # Arrange
    distro = remote.get_item_handle("distro", "testdistro0")

    # Act
    result = remote.rename_distro(distro, "testdistro1", token)

    # Assert
    assert result

    # Cleanup
    remote.remove_distro("testdistro1", token)


def test_remove_distro(
    request: "pytest.FixtureRequest",
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
    create_distro: Callable[[str, str, str, str, str], str],
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: remove a distro object
    """
    # Arrange
    distro_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    kernel_path = os.path.join(folder, fk_kernel)
    initrd_path = os.path.join(folder, fk_initrd)
    create_distro(distro_name, "x86_64", "suse", kernel_path, initrd_path)  # type: ignore

    # Act
    result = remote.remove_distro(distro_name, token)  # type: ignore

    # Assert
    assert result
