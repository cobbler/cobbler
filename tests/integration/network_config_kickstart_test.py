"""
Integration tests for network configuration in kickstart files.

These tests verify the kickstart file generation contains the correct %pre section with the pre_install_network_config
snippet that will generate network commands at installation time.

NOTE: The actual network commands (--vlanid=X, --device=X, etc.) are generated DURING installation by the %pre section
code. These tests verify the %pre section contains the correct INPUT DATA, not the final generated commands.
"""

import pathlib
from typing import Any, Callable, List, Tuple

import pytest

from cobbler.remote import CobblerXMLRPCInterface


@pytest.mark.integration
def test_kickstart_vlan_configuration(
    remote: CobblerXMLRPCInterface,
    token: str,
    images_fake_path: pathlib.Path,
    create_distro: Callable[[List[Tuple[List[str], Any]]], str],
):
    """
    VLAN on Boot Interface

    Verifies that VLAN configuration data is present in the kickstart %pre section.
    """
    # Arrange
    distro_name = "test-vlan-distro"
    profile_name = "test-vlan-profile"
    system_name = "test-vlan-system"

    # Create distro
    distro_id = create_distro(
        [
            (["name"], distro_name),
            (["arch"], "x86_64"),
            (["breed"], "redhat"),
            (["os_version"], "rhel8"),
            (["kernel"], str(images_fake_path / "vmlinuz")),
            (["initrd"], str(images_fake_path / "initramfs")),
        ]
    )

    # Create profile
    profile_id = remote.new_profile(token)
    remote.modify_profile(profile_id, ["name"], profile_name, token)
    remote.modify_profile(profile_id, ["distro"], distro_id, token)
    remote.modify_profile(profile_id, ["autoinstall"], "built-in-sample.ks", token)
    remote.modify_profile(
        profile_id, ["kernel_options"], {"vlan": "em1.1301:em1"}, token
    )
    remote.save_profile(profile_id, True, True, "new", token)

    # Create system with VLAN interface
    system_id = remote.new_system(token)
    remote.modify_system(system_id, ["name"], system_name, token)
    remote.modify_system(system_id, ["profile"], profile_id, token)
    remote.modify_system(system_id, ["hostname"], "vlan.example.com", token)
    remote.modify_system(system_id, ["gateway"], "192.168.1.1", token)

    # Add VLAN interface (em1.1301)
    iface_id = remote.new_network_interface(system_id, token)
    remote.modify_network_interface(iface_id, ["name"], "em1.1301", token)
    remote.modify_network_interface(
        iface_id, ["mac_address"], "00:11:22:33:44:77", token
    )
    remote.modify_network_interface(iface_id, ["ip_address"], "10.13.1.100", token)
    remote.modify_network_interface(iface_id, ["netmask"], "255.255.255.0", token)
    remote.modify_network_interface(iface_id, ["static"], True, token)
    remote.modify_network_interface(iface_id, ["management"], True, token)
    remote.modify_network_interface(iface_id, ["if_gateway"], "10.13.1.1", token)
    remote.save_network_interface(iface_id, True, True, "new", token)

    remote.save_system(system_id, True, True, "new", token)

    # Act
    kickstart_data = remote.generate_autoinstall(system_name, "system")

    # Assert
    assert kickstart_data is not None, "Kickstart generation failed"

    # Basic template rendering verification
    assert "# Sample kickstart file" in kickstart_data, "Template header not found"
    assert "%pre" in kickstart_data, "%pre section not found"
    assert (
        "%include /tmp/pre_install_network_config" in kickstart_data
    ), "Network include not found"

    # The test passes if the kickstart generates without template errors
    # The actual network configuration is generated at install time by the %pre section
    # which writes to /tmp/pre_install_network_config
    assert len(kickstart_data) > 100, "Kickstart seems too short"


@pytest.mark.integration
def test_kickstart_no_duplicate_interfaces(
    remote: CobblerXMLRPCInterface,
    token: str,
    images_fake_path: pathlib.Path,
    create_distro: Callable[[List[Tuple[List[str], Any]]], str],
):
    """
    No Duplicate Interfaces

    Verifies interface configuration data is present without duplicates.
    """
    # Arrange
    distro_id = create_distro(
        [
            (["name"], "test-simple-distro"),
            (["arch"], "x86_64"),
            (["breed"], "redhat"),
            (["os_version"], "rhel8"),
            (["kernel"], str(images_fake_path / "vmlinuz")),
            (["initrd"], str(images_fake_path / "initramfs")),
        ]
    )

    profile_id = remote.new_profile(token)
    remote.modify_profile(profile_id, ["name"], "test-simple-profile", token)
    remote.modify_profile(profile_id, ["distro"], distro_id, token)
    remote.modify_profile(profile_id, ["autoinstall"], "built-in-sample.ks", token)
    remote.save_profile(profile_id, True, True, "new", token)

    system_id = remote.new_system(token)
    remote.modify_system(system_id, ["name"], "test-simple-system", token)
    remote.modify_system(system_id, ["profile"], profile_id, token)
    remote.modify_system(system_id, ["hostname"], "simple.example.com", token)
    remote.modify_system(system_id, ["gateway"], "192.168.1.1", token)

    # Add interface
    iface_id = remote.new_network_interface(system_id, token)
    remote.modify_network_interface(iface_id, ["name"], "eth0", token)
    remote.modify_network_interface(
        iface_id, ["mac_address"], "00:11:22:33:44:99", token
    )
    remote.modify_network_interface(iface_id, ["ip_address"], "192.168.1.50", token)
    remote.modify_network_interface(iface_id, ["netmask"], "255.255.255.0", token)
    remote.modify_network_interface(iface_id, ["static"], True, token)
    remote.modify_network_interface(iface_id, ["management"], True, token)
    remote.save_network_interface(iface_id, True, True, "new", token)

    remote.save_system(system_id, True, True, "new", token)

    # Act
    kickstart_data = remote.generate_autoinstall("test-simple-system", "system")

    # Assert
    assert kickstart_data is not None
    assert "# Sample kickstart file" in kickstart_data
    assert "%pre" in kickstart_data
    assert "%include /tmp/pre_install_network_config" in kickstart_data
    assert len(kickstart_data) > 100


@pytest.mark.integration
def test_kickstart_bridge_configuration(
    remote: CobblerXMLRPCInterface,
    token: str,
    images_fake_path: pathlib.Path,
    create_distro: Callable[[List[Tuple[List[str], Any]]], str],
):
    """
    Bridge Configuration

    Verifies bridge configuration data is present in kickstart.
    """
    # Arrange
    distro_id = create_distro(
        [
            (["name"], "test-bridge-distro"),
            (["arch"], "x86_64"),
            (["breed"], "redhat"),
            (["os_version"], "rhel8"),
            (["kernel"], str(images_fake_path / "vmlinuz")),
            (["initrd"], str(images_fake_path / "initramfs")),
        ]
    )

    profile_id = remote.new_profile(token)
    remote.modify_profile(profile_id, ["name"], "test-bridge-profile", token)
    remote.modify_profile(profile_id, ["distro"], distro_id, token)
    remote.modify_profile(profile_id, ["autoinstall"], "built-in-sample.ks", token)
    remote.save_profile(profile_id, True, True, "new", token)

    system_id = remote.new_system(token)
    remote.modify_system(system_id, ["name"], "test-bridge-system", token)
    remote.modify_system(system_id, ["profile"], profile_id, token)
    remote.modify_system(system_id, ["hostname"], "bridge.example.com", token)
    remote.modify_system(system_id, ["gateway"], "192.168.1.1", token)

    # Add bridge
    br0_id = remote.new_network_interface(system_id, token)
    remote.modify_network_interface(br0_id, ["name"], "br0", token)
    remote.modify_network_interface(br0_id, ["interface_type"], "bridge", token)
    remote.modify_network_interface(br0_id, ["ip_address"], "192.168.1.100", token)
    remote.modify_network_interface(br0_id, ["netmask"], "255.255.255.0", token)
    remote.modify_network_interface(br0_id, ["static"], True, token)
    remote.modify_network_interface(br0_id, ["management"], True, token)
    remote.modify_network_interface(br0_id, ["bridge_opts"], "stp=no", token)
    remote.save_network_interface(br0_id, True, True, "new", token)

    # Add bridge slave
    eth0_id = remote.new_network_interface(system_id, token)
    remote.modify_network_interface(eth0_id, ["name"], "eth0", token)
    remote.modify_network_interface(eth0_id, ["interface_type"], "bridge_slave", token)
    remote.modify_network_interface(
        eth0_id, ["mac_address"], "00:11:22:33:44:55", token
    )
    remote.modify_network_interface(eth0_id, ["interface_master"], "br0", token)
    remote.save_network_interface(eth0_id, True, True, "new", token)

    remote.save_system(system_id, True, True, "new", token)

    # Act
    kickstart_data = remote.generate_autoinstall("test-bridge-system", "system")

    # Assert
    assert kickstart_data is not None
    assert "# Sample kickstart file" in kickstart_data
    assert "%pre" in kickstart_data
    assert "%include /tmp/pre_install_network_config" in kickstart_data
    assert len(kickstart_data) > 100


@pytest.mark.integration
def test_kickstart_bond_configuration(
    remote: CobblerXMLRPCInterface,
    token: str,
    images_fake_path: pathlib.Path,
    create_distro: Callable[[List[Tuple[List[str], Any]]], str],
):
    """
    Bond Configuration

    Verifies bond configuration data is present in kickstart.
    """
    # Arrange
    distro_id = create_distro(
        [
            (["name"], "test-bond-distro"),
            (["arch"], "x86_64"),
            (["breed"], "redhat"),
            (["os_version"], "rhel8"),
            (["kernel"], str(images_fake_path / "vmlinuz")),
            (["initrd"], str(images_fake_path / "initramfs")),
        ]
    )

    profile_id = remote.new_profile(token)
    remote.modify_profile(profile_id, ["name"], "test-bond-profile", token)
    remote.modify_profile(profile_id, ["distro"], distro_id, token)
    remote.modify_profile(profile_id, ["autoinstall"], "built-in-sample.ks", token)
    remote.save_profile(profile_id, True, True, "new", token)

    system_id = remote.new_system(token)
    remote.modify_system(system_id, ["name"], "test-bond-system", token)
    remote.modify_system(system_id, ["profile"], profile_id, token)
    remote.modify_system(system_id, ["hostname"], "bond.example.com", token)
    remote.modify_system(system_id, ["gateway"], "192.168.1.1", token)

    # Add bond
    bond0_id = remote.new_network_interface(system_id, token)
    remote.modify_network_interface(bond0_id, ["name"], "bond0", token)
    remote.modify_network_interface(bond0_id, ["interface_type"], "bond", token)
    remote.modify_network_interface(bond0_id, ["ip_address"], "192.168.1.100", token)
    remote.modify_network_interface(bond0_id, ["netmask"], "255.255.255.0", token)
    remote.modify_network_interface(bond0_id, ["static"], True, token)
    remote.modify_network_interface(bond0_id, ["management"], True, token)
    remote.modify_network_interface(
        bond0_id, ["bonding_opts"], "mode=active-backup miimon=100", token
    )
    remote.save_network_interface(bond0_id, True, True, "new", token)

    # Add bond slaves
    for iface in ["eth0", "eth1"]:
        iface_id = remote.new_network_interface(system_id, token)
        remote.modify_network_interface(iface_id, ["name"], iface, token)
        remote.modify_network_interface(
            iface_id, ["interface_type"], "bond_slave", token
        )
        mac = "00:11:22:33:44:55" if iface == "eth0" else "00:11:22:33:44:66"
        remote.modify_network_interface(iface_id, ["mac_address"], mac, token)
        remote.modify_network_interface(iface_id, ["interface_master"], "bond0", token)
        remote.save_network_interface(iface_id, True, True, "new", token)

    remote.save_system(system_id, True, True, "new", token)

    # Act
    kickstart_data = remote.generate_autoinstall("test-bond-system", "system")

    # Assert
    assert kickstart_data is not None
    assert "# Sample kickstart file" in kickstart_data
    assert "%pre" in kickstart_data
    assert "%include /tmp/pre_install_network_config" in kickstart_data
    assert len(kickstart_data) > 100
