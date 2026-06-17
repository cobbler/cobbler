"""
Test module for verifying network configuration snippets with native kickstart networking.
"""

from typing import Any, Dict

import pytest

from cobbler.api import CobblerAPI


def test_pre_install_network_config_simple_static_ip(cobbler_api: CobblerAPI):
    """
    Test Case 1: Simple Static IP Configuration

    Verifies that basic static IP configuration renders correctly with:
    - Static IP address and netmask
    - Gateway
    - Multiple nameservers
    - Hostname
    """
    # Arrange
    expected_lines = [
        "# Start pre_install_network_config generated code",
        "#  Start eth0",
        "#   Configuring eth0 (00:11:22:33:44:55) na",
        "if mac_exists 00:11:22:33:44:55",
        "then",
        "  get_ifname 00:11:22:33:44:55",
        '  echo "network --device=00:11:22:33:44:55 --bootproto=static --ip=192.168.1.100 --netmask=255.255.255.0 --gateway=192.168.1.1 --nameserver=8.8.8.8,8.8.4.4 --hostname=test-host" >> /tmp/pre_install_network_config',
        "else",
        '  echo "network --device=eth0 --bootproto=static --ip=192.168.1.100 --netmask=255.255.255.0 --gateway=192.168.1.1 --nameserver=8.8.8.8,8.8.4.4 --hostname=test-host" >> /tmp/pre_install_network_config',
        "fi",
    ]

    target_template = cobbler_api.find_template(
        False, False, name="built-in-pre_install_network_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    meta: Dict[str, Any] = {
        "system_name": "test-static",
        "interfaces": {
            "eth0": {
                "mac_address": "00:11:22:33:44:55",
                "management": True,
                "static": True,
                "ipv4": {
                    "address": "192.168.1.100",
                    "netmask": "255.255.255.0",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "na",
                "interface_master": "",
                "bonding_opts": "",
                "bridge_opts": "",
            }
        },
        "gateway": "192.168.1.1",
        "hostname": "test-host",
        "name_servers": ["8.8.8.8", "8.8.4.4"],
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    for expected_line in expected_lines:
        assert expected_line in result, f"Expected line not found: {expected_line}"

    # Verify the network command has all required parameters
    assert "--bootproto=static" in result
    assert "--ip=192.168.1.100" in result
    assert "--netmask=255.255.255.0" in result
    assert "--gateway=192.168.1.1" in result
    assert "--nameserver=8.8.8.8,8.8.4.4" in result
    assert "--hostname=test-host" in result


def test_pre_install_network_config_bridge(cobbler_api: CobblerAPI):
    """
    Test Case 2: Bridge Configuration

    Verifies bridge configuration with slaves renders correctly:
    - Bridge interface with static IP
    - Bridge slave interface
    - Bridge options (stp=no)
    - Correct anaconda bridge commands
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-pre_install_network_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    meta: Dict[str, Any] = {
        "system_name": "test-bridge",
        "interfaces": {
            "br0": {
                "mac_address": "",
                "management": True,
                "static": True,
                "ipv4": {
                    "address": "192.168.1.100",
                    "netmask": "255.255.255.0",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "bridge",
                "interface_master": "",
                "bonding_opts": "",
                "bridge_opts": "stp=no",
            },
            "eth0": {
                "mac_address": "00:11:22:33:44:55",
                "management": False,
                "static": False,
                "ipv4": {
                    "address": "",
                    "netmask": "",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "bridge_slave",
                "interface_master": "br0",
                "bonding_opts": "",
                "bridge_opts": "",
            },
        },
        "gateway": "192.168.1.1",
        "hostname": "test-host",
        "name_servers": ["8.8.8.8"],
        "os_version": "",
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert - Bridge creation
    assert "--device=br0" in result
    assert "--bridgeslaves=eth0" in result
    assert "--bridgeopts=stp=no" in result
    assert "--onboot=on" in result

    # Verify bridge network command structure
    bridge_cmd_found = False
    for line in result.split("\n"):
        if "network" in line and "br0" in line and "--bridgeslaves" in line:
            bridge_cmd_found = True
            assert "--bootproto=static" in line
            assert "--ip=192.168.1.100" in line
            assert "--netmask=255.255.255.0" in line
            break

    assert bridge_cmd_found, "Bridge network command not found in output"

    # Verify no incorrect TYPE=Bridge appears
    assert "TYPE=Bridge" not in result


def test_pre_install_network_config_bond(cobbler_api: CobblerAPI):
    """
    Test Case 3: Bond Configuration

    Verifies bonding configuration renders correctly:
    - Bond interface with static IP
    - Multiple bond slave interfaces
    - Bond options (mode, miimon)
    - All slaves listed in bondslaves parameter
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-pre_install_network_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    meta: Dict[str, Any] = {
        "system_name": "test-bond",
        "interfaces": {
            "bond0": {
                "mac_address": "",
                "management": True,
                "static": True,
                "ipv4": {
                    "address": "192.168.1.100",
                    "netmask": "255.255.255.0",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "bond",
                "interface_master": "",
                "bonding_opts": "mode=active-backup miimon=100",
                "bridge_opts": "",
            },
            "eth0": {
                "mac_address": "00:11:22:33:44:55",
                "management": False,
                "static": False,
                "ipv4": {
                    "address": "",
                    "netmask": "",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "bond_slave",
                "interface_master": "bond0",
                "bonding_opts": "",
                "bridge_opts": "",
            },
            "eth1": {
                "mac_address": "00:11:22:33:44:66",
                "management": False,
                "static": False,
                "ipv4": {
                    "address": "",
                    "netmask": "",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "bond_slave",
                "interface_master": "bond0",
                "bonding_opts": "",
                "bridge_opts": "",
            },
        },
        "gateway": "192.168.1.1",
        "hostname": "test-host",
        "name_servers": [],
        "os_version": "",
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert - Bond creation
    assert "--device=bond0" in result
    assert "--bondopts=mode=active-backup miimon=100" in result
    assert "--onboot=on" in result

    # Verify both slaves are included (order might vary)
    assert (
        "--bondslaves=eth0,eth1" in result or "--bondslaves=eth1,eth0" in result
    ), "Bond slaves not correctly listed"

    # Verify bond network command structure
    bond_cmd_found = False
    for line in result.split("\n"):
        if "network" in line and "bond0" in line and "--bondslaves" in line:
            bond_cmd_found = True
            assert "--bootproto=static" in line
            assert "--ip=192.168.1.100" in line
            break

    assert bond_cmd_found, "Bond network command not found in output"


def test_pre_install_network_config_vlan(cobbler_api: CobblerAPI):
    """
    Test Case 4: VLAN Configuration

    Verifies VLAN configuration renders correctly:
    - VLAN interface (eth0.100)
    - VLAN ID extracted from interface name
    - --vlanid parameter included
    - Per-interface gateway handling
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-pre_install_network_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    meta: Dict[str, Any] = {
        "system_name": "test-vlan",
        "interfaces": {
            "eth0.100": {
                "mac_address": "00:11:22:33:44:55",
                "management": True,
                "static": True,
                "ipv4": {
                    "address": "192.168.100.10",
                    "netmask": "255.255.255.0",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "192.168.100.1",
                "interface_type": "na",
                "interface_master": "",
                "bonding_opts": "",
                "bridge_opts": "",
            },
        },
        "gateway": "192.168.1.1",
        "hostname": "test-vlan-host",
        "name_servers": [],
        "os_version": "",
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert - VLAN configuration
    # The template should extract "100" from "eth0.100" and generate --vlanid=100
    assert (
        "--vlanid=100" in result
    ), "VLAN ID parameter not found or not correctly expanded"
    assert "--ip=192.168.100.10" in result
    assert "--netmask=255.255.255.0" in result

    # Per-interface gateway should use --nodefroute since it differs from system gateway
    assert "--gateway=192.168.100.1" in result
    assert "--nodefroute" in result

    # Verify VLAN network command
    vlan_cmd_found = False
    for line in result.split("\n"):
        if "network" in line and "--vlanid=100" in line:
            vlan_cmd_found = True
            assert "--bootproto=static" in line
            break

    assert vlan_cmd_found, "VLAN network command not found in output"

    # Verify it's not left as a literal bash variable
    assert (
        "--vlanid=$vlan_id" not in result
    ), "VLAN ID should be expanded, not left as $vlan_id variable"


def test_pre_install_network_config_bonded_bridge_slave(cobbler_api: CobblerAPI):
    """
    Test Case 5: Bonded Bridge Slave Configuration

    Verifies bonded_bridge_slave interface type is handled correctly:
    - Bridge with a bonded interface as slave
    - Bond with physical interfaces as slaves
    - Correct hierarchy: physical → bond → bridge
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-pre_install_network_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    meta: Dict[str, Any] = {
        "system_name": "test-bonded-bridge",
        "interfaces": {
            "br0": {
                "mac_address": "",
                "management": True,
                "static": True,
                "ipv4": {
                    "address": "192.168.1.100",
                    "netmask": "255.255.255.0",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "bridge",
                "interface_master": "",
                "bonding_opts": "",
                "bridge_opts": "stp=no",
            },
            "bond0": {
                "mac_address": "",
                "management": False,
                "static": False,
                "ipv4": {
                    "address": "",
                    "netmask": "",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "bonded_bridge_slave",
                "interface_master": "br0",
                "bonding_opts": "mode=802.3ad",
                "bridge_opts": "",
            },
            "eth0": {
                "mac_address": "00:11:22:33:44:55",
                "management": False,
                "static": False,
                "ipv4": {
                    "address": "",
                    "netmask": "",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "bond_slave",
                "interface_master": "bond0",
                "bonding_opts": "",
                "bridge_opts": "",
            },
            "eth1": {
                "mac_address": "00:11:22:33:44:66",
                "management": False,
                "static": False,
                "ipv4": {
                    "address": "",
                    "netmask": "",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "bond_slave",
                "interface_master": "bond0",
                "bonding_opts": "",
                "bridge_opts": "",
            },
        },
        "gateway": "192.168.1.1",
        "hostname": "test-host",
        "name_servers": [],
        "os_version": "",
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert - Bond configuration (bonded_bridge_slave type)
    assert "--device=bond0" in result
    assert "--bondopts=mode=802.3ad" in result
    assert (
        "--bondslaves=eth0,eth1" in result or "--bondslaves=eth1,eth0" in result
    ), "Bond slaves not correctly listed"

    # Assert - Bridge configuration
    assert "--device=br0" in result
    assert "--bridgeslaves=bond0" in result
    assert "--bridgeopts=stp=no" in result

    # Verify both bond and bridge commands exist
    bond_cmd_found = False
    bridge_cmd_found = False

    for line in result.split("\n"):
        if "network" in line and "bond0" in line and "--bondslaves" in line:
            bond_cmd_found = True
        if "network" in line and "br0" in line and "--bridgeslaves" in line:
            bridge_cmd_found = True

    assert bond_cmd_found, "Bond network command not found in output"
    assert bridge_cmd_found, "Bridge network command not found in output"


def test_pre_install_network_config_static_routes(cobbler_api: CobblerAPI):
    """
    Test Case 6: Static Routes Configuration

    Verifies static route configuration:
    - Multiple static routes on an interface
    - Correct ip route add syntax
    - Route format: network/prefix:gateway
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-pre_install_network_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    meta: Dict[str, Any] = {
        "system_name": "test-routes",
        "interfaces": {
            "eth0": {
                "mac_address": "00:11:22:33:44:55",
                "management": True,
                "static": True,
                "ipv4": {
                    "address": "192.168.1.100",
                    "netmask": "255.255.255.0",
                    "static_routes": [
                        "10.0.0.0/8:192.168.1.254",
                        "172.16.0.0/12:192.168.1.253",
                    ],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "na",
                "interface_master": "",
                "bonding_opts": "",
                "bridge_opts": "",
            },
        },
        "gateway": "192.168.1.1",
        "hostname": "test-host",
        "name_servers": [],
        "os_version": "",
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert - Static routes
    assert (
        "ip route add 10.0.0.0/8 via 192.168.1.254 dev" in result
    ), "First static route not found"
    assert (
        "ip route add 172.16.0.0/12 via 192.168.1.253 dev" in result
    ), "Second static route not found"

    # Verify route commands use the correct device variable ($IFNAME or interface name)
    route_lines = [line for line in result.split("\n") if "ip route add" in line]
    assert len(route_lines) >= 2, "Expected at least 2 static route commands"

    # Each route should reference either $IFNAME (if MAC exists) or eth0
    for route_line in route_lines:
        assert (
            "dev $IFNAME" in route_line or "dev eth0" in route_line
        ), f"Route command doesn't specify device correctly: {route_line}"


def test_pre_install_network_config_rhel8_bond_slave_workaround(
    cobbler_api: CobblerAPI,
):
    """
    Test Case 7: RHEL8/9 Bond Slave Workaround

    Verifies the workaround for RHEL bug 2031385:
    - Bond/bridge slave interfaces on RHEL8/9 get special handling
    - Uses --onboot=off for slave interfaces
    - Applies to both bond_slave and bridge_slave types
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-pre_install_network_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    meta: Dict[str, Any] = {
        "system_name": "test-rhel8-bond",
        "interfaces": {
            "bond0": {
                "mac_address": "",
                "management": True,
                "static": True,
                "ipv4": {
                    "address": "192.168.1.100",
                    "netmask": "255.255.255.0",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "bond",
                "interface_master": "",
                "bonding_opts": "mode=802.3ad",
                "bridge_opts": "",
            },
            "eth0": {
                "mac_address": "00:11:22:33:44:55",
                "management": False,
                "static": False,
                "ipv4": {
                    "address": "",
                    "netmask": "",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "bond_slave",
                "interface_master": "bond0",
                "bonding_opts": "",
                "bridge_opts": "",
            },
        },
        "gateway": "192.168.1.1",
        "hostname": "test-host",
        "name_servers": [],
        "os_version": "rhel8",  # Trigger RHEL8 specific code path
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert - RHEL8 bond slave workaround
    # The slave should get special handling with --onboot=off
    assert "--onboot=off" in result, "RHEL8 bond_slave workaround not applied"

    # Verify the workaround includes MAC address check
    assert "if mac_exists" in result
    assert (
        "network --device=$IFNAME --onboot=off" in result
        or "network --device=eth0 --onboot=off" in result
    )


def test_pre_install_network_config_dhcp_interface(cobbler_api: CobblerAPI):
    """
    Test Case 8: DHCP Interface Configuration

    Verifies DHCP configuration renders correctly:
    - Interface with DHCP (static=False)
    - No IP/netmask specified
    - --bootproto=dhcp used
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-pre_install_network_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    meta: Dict[str, Any] = {
        "system_name": "test-dhcp",
        "interfaces": {
            "eth0": {
                "mac_address": "00:11:22:33:44:55",
                "management": True,
                "static": False,
                "ipv4": {
                    "address": "",
                    "netmask": "",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "",
                    "prefix": "",
                    "default_gateway": "",
                },
                "if_gateway": "",
                "interface_type": "na",
                "interface_master": "",
                "bonding_opts": "",
                "bridge_opts": "",
            },
        },
        "gateway": "",
        "hostname": "test-dhcp-host",
        "name_servers": [],
        "os_version": "",
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert - DHCP configuration
    assert "--bootproto=dhcp" in result, "DHCP bootproto not found"
    assert "--device=00:11:22:33:44:55" in result or "--device=eth0" in result
    assert "--hostname=test-dhcp-host" in result

    # Should NOT have static IP parameters
    assert "--ip=" not in result
    assert "--netmask=" not in result


def test_pre_install_network_config_ipv6(cobbler_api: CobblerAPI):
    """
    Test Case 9: IPv6 Configuration

    Verifies IPv6 configuration renders correctly:
    - Static IPv6 address with prefix
    - IPv6 gateway
    - Dual-stack (IPv4 + IPv6)
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-pre_install_network_config"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    meta: Dict[str, Any] = {
        "system_name": "test-ipv6",
        "interfaces": {
            "eth0": {
                "mac_address": "00:11:22:33:44:55",
                "management": True,
                "static": True,
                "ipv4": {
                    "address": "192.168.1.100",
                    "netmask": "255.255.255.0",
                    "static_routes": [],
                },
                "ipv6": {
                    "address": "2001:db8::100",
                    "prefix": "64",
                    "default_gateway": "2001:db8::1",
                },
                "if_gateway": "",
                "interface_type": "na",
                "interface_master": "",
                "bonding_opts": "",
                "bridge_opts": "",
            },
        },
        "gateway": "192.168.1.1",
        "hostname": "test-ipv6-host",
        "name_servers": [],
        "os_version": "",
    }

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert - IPv6 configuration
    assert "--ipv6=2001:db8::100/64" in result, "IPv6 address not found"
    assert "--ipv6gateway=2001:db8::1" in result, "IPv6 gateway not found"

    # Should also have IPv4 configuration (dual-stack)
    assert "--ip=192.168.1.100" in result
    assert "--netmask=255.255.255.0" in result
