import os
from typing import Callable, Union

import pytest

from cobbler.cexceptions import CX
from cobbler.remote import CobblerXMLRPCInterface


def test_get_profiles(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get profiles
    """
    # Arrange --> Nothing to arrange

    # Act
    result = remote.get_profiles(token)

    # Assert
    assert result == []


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
@pytest.mark.parametrize(
    "field_name,field_value",
    [
        ("comment", "test comment"),
        ("dhcp_tag", ""),
        ("dhcp_tag", "foo"),
        ("distro", "testdistro0"),
        ("enable_ipxe", True),
        ("enable_ipxe", False),
        ("enable_menu", True),
        ("enable_menu", False),
        ("kernel_options", "a=1 b=2 c=3 c=4 c=5 d e"),
        ("kernel_options_post", "a=1 b=2 c=3 c=4 c=5 d e"),
        ("autoinstall", "test.ks"),
        ("autoinstall", "test.xml"),
        ("autoinstall", "test.seed"),
        ("autoinstall_meta", "a=1 b=2 c=3 c=4 c=5 d e"),
        ("mgmt_classes", "one two three"),
        ("mgmt_parameters", "<<inherit>>"),
        ("name", "testprofile0"),
        ("name_servers", "1.1.1.1 1.1.1.2 1.1.1.3"),
        ("name_servers_search", "example.com foo.bar.com"),
        ("owners", "user1 user2 user3"),
        ("proxy", "testproxy"),
        ("server", "1.1.1.1"),
        ("menu", "testmenu0"),
        ("virt_auto_boot", True),
        ("virt_auto_boot", False),
        ("enable_ipxe", True),
        ("enable_ipxe", False),
        ("enable_ipxe", "yes"),
        ("enable_ipxe", "YES"),
        ("enable_ipxe", "1"),
        ("enable_ipxe", "0"),
        ("enable_ipxe", "no"),
        ("enable_menu", True),
        ("enable_menu", False),
        ("enable_menu", "yes"),
        ("enable_menu", "YES"),
        ("enable_menu", "1"),
        ("enable_menu", "0"),
        ("enable_menu", "no"),
        ("virt_auto_boot", "yes"),
        ("virt_auto_boot", "no"),
        ("virt_bridge", "<<inherit>>"),
        ("virt_bridge", "br0"),
        ("virt_bridge", "virbr0"),
        ("virt_bridge", "xenbr0"),
        ("virt_cpus", "<<inherit>>"),
        ("virt_cpus", 1),
        ("virt_cpus", 2),
        ("virt_disk_driver", "<<inherit>>"),
        ("virt_disk_driver", "raw"),
        ("virt_disk_driver", "qcow2"),
        ("virt_disk_driver", "vdmk"),
        ("virt_file_size", "<<inherit>>"),
        ("virt_file_size", "5"),
        ("virt_file_size", "10"),
        ("virt_path", "<<inherit>>"),
        ("virt_path", "/path/to/test"),
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
        # ("boot_loaders", "pxe ipxe grub") FIXME: This raises currently but it did not in the past
    ],
)
def test_create_profile_positive(
    remote: CobblerXMLRPCInterface,
    token: str,
    template_files: Callable[[], None],
    field_name: str,
    field_value: Union[str, int, bool],
):
    """
    Test: create/edit a profile object
    """
    # Arrange
    profile = remote.new_profile(token)
    remote.modify_profile(profile, "name", "testprofile0", token)
    remote.modify_profile(profile, "distro", "testdistro0", token)

    # Act
    result = remote.modify_profile(profile, field_name, field_value, token)

    # Assert
    assert result


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
@pytest.mark.parametrize(
    "field_name,field_value",
    [
        ("distro", "baddistro"),
        ("autoinstall", "/path/to/bad/autoinstall"),
        ("mgmt_parameters", "badyaml"),
        ("menu", "badmenu"),
        ("virt_cpus", "a"),
        ("virt_file_size", "a"),
        ("virt_ram", "a"),
        ("virt_type", "bad"),
        ("boot_loaders", "badloader"),
    ],
)
def test_create_profile_negative(
    remote: CobblerXMLRPCInterface, token: str, field_name: str, field_value: str
):
    """
    Test: create/edit a profile object
    """
    # Arrange
    profile = remote.new_profile(token)
    remote.modify_profile(profile, "name", "testprofile0", token)

    # Act & Assert
    try:
        remote.modify_profile(profile, field_name, field_value, token)
    except (CX, TypeError, ValueError, OSError):
        assert True
    else:
        pytest.fail("Bad field did not raise an exception!")


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
def test_create_subprofile(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: create/edit a subprofile object
    """

    # Arrange
    profiles = remote.get_profiles(token)

    # Act
    subprofile = remote.new_subprofile(token)

    # Assert
    assert remote.modify_profile(subprofile, "name", "testsubprofile0", token)
    assert remote.modify_profile(subprofile, "parent", "testprofile0", token)

    assert remote.save_profile(subprofile, token)

    new_profiles = remote.get_profiles(token)
    assert len(new_profiles) == len(profiles) + 1


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
def test_get_profile(remote: CobblerXMLRPCInterface):
    """
    Test: get a profile object
    """
    # Arrange --> Done in fixture.

    # Act
    profile = remote.get_profile("testprofile0")

    # Assert
    assert profile.get("name") == "testprofile0"  # type: ignore
    assert profile.get("distro") == "testdistro0"  # type: ignore
    assert profile.get("menu") == "testmenu0"  # type: ignore
    assert profile.get("kernel_options") == {  # type: ignore
        "a": "1",
        "b": "2",
        "c": ["3", "4", "5"],
        "d": "~",
        "e": "~",
    }


def test_find_profile(
    request: "pytest.FixtureRequest",
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: find a profile object
    """
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    distro_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    profile_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    kernel_path = os.path.join(folder, fk_kernel)
    initrd_path = os.path.join(folder, fk_initrd)
    create_distro(distro_name, "x86_64", "suse", kernel_path, initrd_path)  # type: ignore
    create_profile(profile_name, distro_name, "")  # type: ignore

    # Act
    result = remote.find_profile(criteria={"name": profile_name}, token=token)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == profile_name


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
def test_copy_profile(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: copy a profile object
    """

    # Arrange --> Done in fixtures

    # Act
    profile = remote.get_item_handle("profile", "testprofile0")
    result = remote.copy_profile(profile, "testprofilecopy", token)

    # Assert
    assert result

    # Cleanup
    remote.remove_profile("testprofilecopy", token)


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testprofile",
    "remove_testmenu",
    "remove_testdistro",
)
def test_rename_profile(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: rename a profile object
    """

    # Arrange
    profile = remote.get_item_handle("profile", "testprofile0")

    # Act
    result = remote.rename_profile(profile, "testprofile1", token)

    # Assert
    assert result

    # Cleanup
    remote.remove_profile("testprofile1", token)


def test_remove_profile(
    request: "pytest.FixtureRequest",
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, str], str],
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: remove a profile object
    """
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    distro_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    profile_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    kernel_path = os.path.join(folder, fk_kernel)
    initrd_path = os.path.join(folder, fk_initrd)
    create_distro(distro_name, "x86_64", "suse", kernel_path, initrd_path)  # type: ignore
    create_profile(profile_name, distro_name, "")  # type: ignore

    # Act
    result_profile_remove = remote.remove_profile(profile_name, token)  # type: ignore

    # Assert
    assert result_profile_remove


def test_get_repo_config_for_profile(remote: CobblerXMLRPCInterface):
    """
    Test: get repository configuration of a profile
    """
    # Arrange --> There is nothing to be arranged

    # Act
    result = remote.get_repo_config_for_profile("testprofile0")  # type: ignore

    # Assert --> Let the test pass if the call is okay.
    assert True
