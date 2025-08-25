"""
TODO
"""

import pathlib
import shutil
import subprocess
from time import sleep
from typing import Any, Callable, Dict

import pytest

from cobbler.remote import CobblerXMLRPCInterface

from tests.integration.conftest import WaitTaskEndType


@pytest.mark.integration
def test_basic_buildiso(
    tmp_path: pathlib.Path,
    remote: CobblerXMLRPCInterface,
    token: str,
    wait_task_end: WaitTaskEndType,
    images_fake_path: pathlib.Path,
    create_distro: Callable[[Dict[str, Any]], str],
):
    """
    Check that Cobbler is able to build customized ISOs by the "cobbler buildiso" command
    """
    # Arrange
    distro_name = "fake"
    buildisodir = pathlib.Path("/var/cache/cobbler/buildiso")
    expected_result = b"BIOS\nUEFI\n"
    iso_path = tmp_path / "autoinst.iso"

    create_distro(
        {
            "name": distro_name,
            "arch": "x86_64",
            "kernel": str(images_fake_path / "vmlinuz"),
            "initrd": str(images_fake_path / "initramfs"),
        }
    )
    profile_id = remote.new_profile(token)
    remote.modify_profile(profile_id, "name", "fake", token)
    remote.modify_profile(profile_id, "distro", distro_name, token)
    remote.save_profile(profile_id, token, "new")
    system_id = remote.new_system(token)
    remote.modify_system(system_id, "name", "testbed", token)
    remote.modify_system(system_id, "profile", "fake", token)
    remote.save_system(system_id, token, "new")
    buildisodir.mkdir(parents=True, exist_ok=True)

    # Act
    tid = remote.background_buildiso(
        {"iso": str(iso_path), "distro": distro_name, "buildisodir": str(buildisodir)},
        token,
    )
    wait_task_end(tid, remote)

    # Assert
    # Check ISO exists
    assert iso_path.exists()
    # Check ISO is bootable
    # pylint: disable-next=line-too-long
    result = subprocess.check_output(
        f"xorriso -indev {str(iso_path)} -report_el_torito 2>/dev/null | awk '/^El Torito boot img[[:space:]]+:[[:space:]]+[0-9]+[[:space:]]+[a-zA-Z]+[[:space:]]+y/{{print $7}}'",
        shell=True,
    )
    assert result == expected_result


@pytest.mark.integration
def test_basic_distro_add_remove(
    remote: CobblerXMLRPCInterface, token: str, images_fake_path: pathlib.Path
):
    """
    Check that Cobbler can add and remove distros
    """
    # Arrange
    distro_names = ["fake-1", "fake-2"]

    # Act
    # 1. Create Distro's
    for name in distro_names:
        distro_id = remote.new_distro(token)
        remote.modify_distro(distro_id, "name", name, token)
        remote.modify_distro(distro_id, "arch", "x86_64", token)
        remote.modify_distro(
            distro_id, "kernel", str(images_fake_path / "vmlinuz"), token
        )
        remote.modify_distro(
            distro_id, "initrd", str(images_fake_path / "initramfs"), token
        )
        remote.save_distro(distro_id, token, "new")
    # 2. Assert distros are present
    assert len(remote.get_item_names("distro")) == len(distro_names)
    # 3. Remove distros
    for name in distro_names:
        remote.remove_distro(name, token)

    # Assert
    assert len(remote.get_item_names("distro")) == 0


@pytest.mark.integration
def test_basic_distro_rename(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[Dict[str, Any]], str],
    images_fake_path: pathlib.Path,
):
    """
    Check that Cobbler can rename distros
    """
    # Arrange
    collections_path = pathlib.Path("/var/lib/cobbler/collections")
    distro_name = "fake"
    did = create_distro(
        {
            "name": distro_name,
            "arch": "x86_64",
            "kernel": str(images_fake_path / "vmlinuz"),
            "initrd": str(images_fake_path / "initramfs"),
        }
    )
    pid = remote.new_profile(token)
    remote.modify_profile(pid, "name", "fake", token)
    remote.modify_profile(pid, "distro", "fake", token)
    remote.save_profile(pid, token, "new")

    # Act
    remote.rename_distro(did, "fake-renamed", token)

    # Assert
    distro_result = remote.get_distro("fake-renamed", False, False, token)
    distro_uuid: str = distro_result.get("uid")  # type: ignore
    assert not (collections_path / "distros" / "fake.json").exists()
    assert (collections_path / "distros" / "fake-renamed.json").exists()
    dump_vars_result = remote.dump_vars(distro_uuid)  # type: ignore
    assert dump_vars_result.get("distro_name") == "fake-renamed"  # type: ignore


@pytest.mark.integration
def test_basic_inheritance(
    create_distro: Callable[[Dict[str, Any]], str],
    create_profile: Callable[[Dict[str, Any]], str],
    create_system: Callable[[Dict[str, Any]], str],
    images_fake_path: pathlib.Path,
    remote: CobblerXMLRPCInterface,
):
    """
    Check that Cobbler can properly inherit template variables
    """
    # Arrange
    test_template = pathlib.Path("/var/lib/cobbler/templates/system-tests.sh")
    test_template.write_text(
        "${name_servers} ${server} ${kernel_options}\n", encoding="UTF-8"
    )
    distro_name = "fake"
    profile_name_level_0 = "fake-0"
    profile_name_level_1 = "fake-1"
    profile_name_level_2 = "fake-2"
    profile_name_level_3 = "fake-3"
    profile_name_level_4 = "fake-4"

    # Act
    create_distro(
        {
            "name": distro_name,
            "arch": "x86_64",
            "kernel": str(images_fake_path / "vmlinuz"),
            "initrd": str(images_fake_path / "initramfs"),
        }
    )

    # The following part is kinda complex. The idea is to check how Cobbler treats
    # all three kinds of variables: scalar, list and dict.
    create_profile(
        {
            "name": profile_name_level_0,
            "distro": "fake",
            "autoinstall": str(test_template.name),
            "server": "10.0.0.1",
            "name_servers": "8.8.4.4",
        }
    )

    # Then we start adding descendants. The first one, fake-1, inherits from fake-0
    # and adds key 'foo' to the kernel-options dictionary. Then it's child fake-2
    # adds 'bar' and 'not-wanted'. The next offspring removes 'not-wanted' and
    # finally its own child fake-4 overrides 'bar'.

    create_profile(
        {
            "name": profile_name_level_1,
            "parent": profile_name_level_0,
            "kernel_options": "foo=1",
        }
    )
    create_profile(
        {
            "name": profile_name_level_2,
            "parent": profile_name_level_1,
            "kernel_options": "bar=3 not-wanted",
        }
    )
    create_profile(
        {
            "name": profile_name_level_3,
            "parent": profile_name_level_2,
            "kernel_options": "!not-wanted",
        }
    )
    create_profile(
        {
            "name": profile_name_level_4,
            "parent": profile_name_level_3,
            "kernel_options": "bar=2",
        }
    )

    # Now we create two systems: testbed-1 and testbed-2.
    #
    # The first system inherits from fake-2 and shall not see any modifications
    # done to the kernel-options by fake-3 and fake-4. It also adds an additional
    # server to the name-servers list.
    #
    # The second one should see all the modifications and have a single name
    # server.

    create_system(
        {
            "name": "testbed-1",
            "profile": profile_name_level_2,
            "name_servers": "8.8.8.8",
        }
    )
    create_system(
        {
            "name": "testbed-2",
            "profile": profile_name_level_4,
            "kernel_options": "baz=3",
        }
    )

    # Assert
    expected_result_testbed_1 = (
        "['8.8.4.4', '8.8.8.8'] 10.0.0.1 foo=1 bar=3 not-wanted \n"
    )
    expected_result_testbed_2 = "['8.8.4.4'] 10.0.0.1 foo=1 bar=2 baz=3 \n"

    result_testbed_1 = remote.generate_autoinstall("", "testbed-1")
    result_testbed_2 = remote.generate_autoinstall("", "testbed-2")
    assert result_testbed_1 == expected_result_testbed_1
    assert result_testbed_2 == expected_result_testbed_2


@pytest.mark.integration
def test_basic_mkloaders(
    remote: CobblerXMLRPCInterface,
    token: str,
    wait_task_end: WaitTaskEndType,
):
    """
    Check that Cobbler can make bootloaders
    """
    # Arrange
    # Delete mkloaders directory content completely if present
    mkloaders_directory = pathlib.Path("/var/lib/cobbler/mkloaders")
    shutil.rmtree(mkloaders_directory, ignore_errors=True)
    mkloaders_directory.mkdir()

    # Act
    tid = remote.background_mkloaders({}, token)
    wait_task_end(tid, remote)

    # Assert
    # Check all expected files are present
    assert pathlib.Path("/var/lib/cobbler/loaders/grub").exists()
    # All other files in the GRUB dir are dependant on the installed GRUBs. We check only shim.
    assert pathlib.Path("/var/lib/cobbler/loaders/grub/shim.efi").exists()
    assert pathlib.Path("/var/lib/cobbler/loaders/memdisk").exists()
    assert pathlib.Path("/var/lib/cobbler/loaders/menu.c32").exists()
    assert pathlib.Path("/var/lib/cobbler/loaders/pxelinux.0").exists()
    assert pathlib.Path("/var/lib/cobbler/loaders/undionly.pxe").exists()


@pytest.mark.integration
def test_basic_profile_add_remove(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[Dict[str, Any]], str],
    create_profile: Callable[[Dict[str, Any]], str],
    images_fake_path: pathlib.Path,
):
    """
    Check that Cobbler can add and remove profiles
    """
    # Arrange
    create_distro(
        {
            "name": "fake",
            "arch": "x86_64",
            "kernel": str(images_fake_path / "vmlinuz"),
            "initrd": str(images_fake_path / "initramfs"),
        }
    )

    # Act - Create Profiles
    for i in range(1, 3):
        top_profile_name = f"fake-{i}"
        create_profile({"name": top_profile_name, "distro": "fake"})
        for k in range(1, 3):
            middle_profile_name = f"fake-{i}-child-{k}"
            create_profile({"name": middle_profile_name, "parent": top_profile_name})
            for j in range(1, 3):
                bottom_profile_name = f"fake-{i}-grandchild-{k}-{j}"
                create_profile(
                    {"name": bottom_profile_name, "parent": middle_profile_name}
                )

    # Assert - Assert Profiles created
    profile_names = remote.get_item_names("profile")
    assert len(profile_names) == 14
    del profile_names

    # Act - Remove Profiles
    for i in range(1, 3):
        remote.remove_profile(f"fake-{i}", token, True)

    # Assert - Assert Profiles deleted
    profile_names = remote.get_item_names("profile")
    assert len(profile_names) == 0


@pytest.mark.integration
def test_basic_profile_rename(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[Dict[str, Any]], str],
    create_profile: Callable[[Dict[str, Any]], str],
    images_fake_path: pathlib.Path,
):
    """
    Check that Cobbler can rename profiles
    """
    # Arrange
    expected_result = "fake-renamed"
    profiles_collection_folder = pathlib.Path("/var/lib/cobbler/collections/profiles")
    distro_name = "fake"
    profile_name = "fake"
    profile_child_name = "fake-child"
    create_distro(
        {
            "name": distro_name,
            "arch": "x86_64",
            "kernel": str(images_fake_path / "vmlinuz"),
            "initrd": str(images_fake_path / "initramfs"),
        }
    )
    pid = create_profile(
        {
            "name": profile_name,
            "distro": distro_name,
        }
    )
    create_profile(
        {
            "name": profile_child_name,
            "parent": profile_name,
        }
    )
    child_uuid: str = remote.get_profile(profile_child_name).get("uid")  # type: ignore

    # Act
    remote.rename_profile(pid, expected_result, token)

    # Assert
    assert not (profiles_collection_folder / f"{profile_name}.json").exists()
    assert (profiles_collection_folder / f"{expected_result}.json").exists()

    result = remote.dump_vars(child_uuid)
    assert expected_result == result.get("parent")  # type: ignore


@pytest.mark.integration
def test_basic_system_add_remove(
    create_distro: Callable[[Dict[str, Any]], str],
    create_profile: Callable[[Dict[str, Any]], str],
    create_system: Callable[[Dict[str, Any]], str],
    images_fake_path: pathlib.Path,
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Check that Cobbler can add and remove systems
    """
    # Arrange
    distro_name = "fake"
    create_distro(
        {
            "name": distro_name,
            "arch": "x86_64",
            "kernel": str(images_fake_path / "vmlinuz"),
            "initrd": str(images_fake_path / "initramfs"),
        }
    )
    create_profile(
        {
            "name": "fake",
            "distro": distro_name,
        }
    )

    # Act - Create Systems
    for i in range(1, 4):
        create_system({"name": f"testbed-{i}", "profile": "fake"})

    # Assert - Check systems created
    assert len(remote.get_item_names("system")) == 3

    # Act - Remove systems
    for i in range(1, 4):
        remote.remove_system(f"testbed-{i}", token)

    # Assert - No systems present
    assert len(remote.get_item_names("system")) == 0


@pytest.mark.integration
def test_basic_system_ipxe_dhpd_conf_update(
    create_distro: Callable[[Dict[str, Any]], str],
    create_profile: Callable[[Dict[str, Any]], str],
    create_system: Callable[[Dict[str, Any]], str],
    images_fake_path: pathlib.Path,
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Check that Cobbler can add and remove systems
    """
    # Arrange
    distro_name = "fake"
    create_distro(
        {
            "name": distro_name,
            "arch": "x86_64",
            "kernel": str(images_fake_path / "vmlinuz"),
            "initrd": str(images_fake_path / "initramfs"),
        }
    )
    create_profile(
        {
            "name": "fake",
            "distro": distro_name,
        }
    )
    sid = create_system(
        {
            "name": "testbed",
            "profile": "fake",
            "modify_interface": {"mac_address-default": "aa:bb:cc:dd:ee:ff"},
        }
    )

    # Act
    remote.modify_system(sid, "netboot_enabled", True, token)
    remote.modify_system(sid, "enable_ipxe", True, token)
    remote.save_system(sid, token)

    # Assert
    # We assume that the existence of a single http URL is a successful iPXE group creation.
    # See dhcp.template for reference how we generate this.
    dhcpd_conf_locations = ("/etc/dhcpd.conf", "/etc/dhcp/dhcpd.conf")
    for loc in dhcpd_conf_locations:
        loc_obj = pathlib.Path(loc)
        if loc_obj.exists():
            assert 'filename "http://' in loc_obj.read_text(encoding="UTF-8")


@pytest.mark.integration
def test_basic_system_parent_image(
    remote: CobblerXMLRPCInterface,
    token: str,
    restart_cobbler: Callable[[], None],
):
    """
    Check that Cobbler can add a system based on an image and afterwards can restart
    """
    # Arrange
    iid = remote.new_image(token)
    remote.modify_image(iid, "name", "fake", token)
    remote.save_image(iid, token, "new")

    # Act
    sid = remote.new_system(token)
    remote.modify_system(sid, "name", "testbed", token)
    remote.modify_system(sid, "image", "fake", token)
    remote.modify_system(
        sid, "modify_interface", {"mac_address-default": "aa:bb:cc:dd:ee:ff"}, token
    )
    remote.save_system(sid, token)
    restart_cobbler()

    # Assert - If cobblerd is successfully restarted we should get the image and system loaded successfully.
    image_names = remote.get_item_names("image")
    system_names = remote.get_item_names("system")
    assert "fake" in image_names
    assert "testbed" in system_names


@pytest.mark.integration
def test_basic_system_rename(
    create_distro: Callable[[Dict[str, Any]], str],
    create_profile: Callable[[Dict[str, Any]], str],
    create_system: Callable[[Dict[str, Any]], str],
    remote: CobblerXMLRPCInterface,
    token: str,
    images_fake_path: pathlib.Path,
):
    """
    Check that Cobbler can rename systems
    """
    # Arrange
    distro_name = "fake"
    create_distro(
        {
            "name": distro_name,
            "arch": "x86_64",
            "kernel": str(images_fake_path / "vmlinuz"),
            "initrd": str(images_fake_path / "initramfs"),
        }
    )
    create_profile(
        {
            "name": "fake",
            "distro": distro_name,
        }
    )
    sid = create_system({"name": "testbed", "profile": "fake"})

    # Act
    remote.rename_system(sid, "testbed-renamed", token)
    # cobbler system rename --name testbed --newname testbed-renamed

    # Assert
    system_collections_path = pathlib.Path("/var/lib/cobbler/collections/systems")
    assert not (system_collections_path / "testbed.json").exists()
    assert (system_collections_path / "testbed-renamed.json").exists()


@pytest.mark.integration
def test_basic_system_serial(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[Dict[str, Any]], str],
    create_profile: Callable[[Dict[str, Any]], str],
    create_system: Callable[[Dict[str, Any]], str],
    wait_task_end: WaitTaskEndType,
    images_fake_path: pathlib.Path,
):
    """
    Check that Cobbler can configure serial console
    """
    # Arrange
    distro_name = "fake"
    create_distro(
        {
            "name": distro_name,
            "arch": "x86_64",
            "kernel": str(images_fake_path / "vmlinuz"),
            "initrd": str(images_fake_path / "initramfs"),
        }
    )
    create_profile(
        {
            "name": "fake",
            "distro": distro_name,
        }
    )

    # Create three systems per bootloader:
    #
    #   1. With the serial device set to 0
    #   2. With the serial baud rate set to 115200
    #   3. With disabled serial console
    #
    # Cases #1 and #2 shall be equal w.r.t. the serial console configuration as
    # Cobbler defaults to 0 and 115200 for device and baud rate respectively.
    for loader in ["grub", "pxe"]:
        create_system(
            {
                "name": f"testbed-1-{loader}",
                "profile": "fake",
                "boot_loader": loader,
                "modify_interface": {"mac_address-default": "random"},
                "serial_device": 0,
            }
        )
        create_system(
            {
                "name": f"testbed-2-{loader}",
                "profile": "fake",
                "boot_loader": loader,
                "modify_interface": {"mac_address-default": "random"},
                "serial_baud_rate": 115200,
            }
        )
        create_system(
            {
                "name": f"testbed-3-{loader}",
                "profile": "fake",
                "boot_loader": loader,
                "modify_interface": {"mac_address-default": "random"},
            }
        )

    # Act
    sleep(5)  # sleep for 5 seconds to prevent supervisord backoff errors
    tid = remote.background_sync({}, token)
    wait_task_end(tid, remote)

    # Assert
    # Let's check. There shall be two systems with identical serial console
    # configurations. The third shall not have any serial console parameters set.
    expected_result_pxelinux = "    serial 0 115200\n"
    expected_result_pxelinux += "    serial 0 115200\n"
    expected_result_grub = "    set serial_baud=115200\n"
    expected_result_grub += "    set serial_baud=115200\n"
    expected_result_grub += "    set serial_baud=0\n"
    expected_result_grub += "    set serial_baud=0\n"
    tftproot = pathlib.Path("/srv/tftpboot/")
    result = ""
    for file in (tftproot / "pxelinux.cfg").iterdir():
        file_content = file.read_text(encoding="UTF-8").split()
        for line in file_content:
            if "serial" in line:
                result += line
    for file in (tftproot / "grub" / "system").iterdir():
        file_content = file.read_text(encoding="UTF-8").split()
        for line in file_content:
            if "serial" in line:
                result += line
