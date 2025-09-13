"""
Test module to verify that Cobbler can install a dummy OS with a Distro-Profile-System chain.
"""

import pathlib
import subprocess

import pytest

from cobbler.remote import CobblerXMLRPCInterface


@pytest.mark.integration
@pytest.mark.skip(reason="missing kernel and initrd files")
def test_autoinstall_dummy_bios(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Check that Cobbler can install a dummy OS
    """
    # Arrange
    server = "192.168.1.1"
    distro_name = "dummy"
    profile_name = "dummy"
    fake_directory = pathlib.Path("/code/system-tests/images/dummy")
    path_templates = pathlib.Path("/var/lib/cobbler/templates")
    autoinstall_template = path_templates / "system-tests.sh"
    script_url = f"http://{server}/cblr/svc/op/autoinstall/system/testbed"
    autoinstall_template.write_text(
        "$SNIPPET('autoinstall_start')\n$SNIPPET('autoinstall_done')\n"
    )
    distro_id = remote.new_distro(token)
    remote.modify_distro(distro_id, ["name"], distro_name, token)
    remote.modify_distro(distro_id, ["arch"], "x86_64", token)
    remote.modify_distro(distro_id, ["kernel"], str(fake_directory / "vmlinuz"), token)
    remote.modify_distro(
        distro_id, ["initrd"], str(fake_directory / "initramfs.gz"), token
    )
    remote.save_distro(distro_id, token, editmode="new")
    profile_id = remote.new_profile(token)
    remote.modify_profile(profile_id, ["name"], profile_name, token)
    remote.modify_profile(profile_id, ["distro"], distro_id, token)
    remote.save_profile(profile_id, token, "new")
    system_id = remote.new_system(token)
    remote.modify_system(system_id, ["name"], "testbed", token)
    remote.modify_system(system_id, ["profile"], profile_id, token)
    remote.modify_system(system_id, ["autoinstall"], profile_name, token)
    remote.modify_system(
        system_id,
        ["kernel_options"],
        {"console": "ttyS0", "pci": "noacpi", "noapic": "~", "script": script_url},
        token,
    )
    remote.modify_system(system_id, ["netboot_enabled"], True, token)
    remote.save_system(system_id, token, "new")
    network_interface_id = remote.new_network_interface(system_id, token)
    remote.modify_network_interface(network_interface_id, ["name"], "default", token)
    remote.save_network_interface(network_interface_id, token, "new")
    remote.sync(token)

    # Act
    bridge = "pxe"
    qemu = str(
        subprocess.check_output(
            "command -v qemu-system-$(uname -m) /usr/libexec/qemu-kvm | head -1",
            shell=True,
        )
    )
    command = f"{qemu} -nographic -nic bridge,br={bridge},mac=52:54:00:00:00:01 -boot n"
    command += f" -drive file={str(fake_directory)}/bios-disk,format=raw"
    result = subprocess.call(command, shell=True)

    # Assert
    assert result == 0
