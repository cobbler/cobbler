"""
Test module that contains all tests that are related to XML-RPC methods that perform actions with a Cobbler
network interface.
"""

import os
from typing import Callable

from cobbler.remote import CobblerXMLRPCInterface


def test_modify_existing_network_interface_with_duplicate_prone_fields_set(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    A classic (non-transaction) edit session against an already-saved network interface whose
    mac_address/ipv4.address/ipv6.address/dns.name are all set must succeed, not raise a false
    "duplicate" against the interface's own, still-live pre-edit state.
    """
    # Arrange
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    distro = remote.new_distro(token)
    remote.modify_distro(distro, ["name"], "testdistro_netif_classic_edit", token)
    remote.modify_distro(distro, ["arch"], "x86_64", token)
    remote.modify_distro(distro, ["breed"], "suse", token)
    remote.modify_distro(distro, ["kernel"], os.path.join(basepath, fk_kernel), token)
    remote.modify_distro(distro, ["initrd"], os.path.join(basepath, fk_initrd), token)
    remote.save_distro(distro, True, True, "bypass", token)

    profile = remote.new_profile(token)
    remote.modify_profile(profile, ["name"], "testprofile_netif_classic_edit", token)
    remote.modify_profile(profile, ["distro"], distro, token)
    remote.save_profile(profile, True, True, "bypass", token)

    system = remote.new_system(token)
    remote.modify_system(system, ["name"], "testsystem_netif_classic_edit", token)
    remote.modify_system(system, ["profile"], profile, token)
    remote.save_system(system, True, True, "bypass", token)

    interface = remote.new_network_interface(system, token)
    remote.modify_network_interface(interface, ["name"], "eth0", token)
    remote.modify_network_interface(
        interface, ["mac_address"], "aa:bb:cc:dd:ee:ff", token
    )
    remote.modify_network_interface(interface, ["ipv4", "address"], "1.2.3.4", token)
    remote.modify_network_interface(
        interface, ["ipv6", "address"], "2001:db8::4", token
    )
    remote.modify_network_interface(
        interface, ["dns", "name"], "host.example.org", token
    )
    remote.save_network_interface(interface, True, True, "new", token)

    # Act
    interface_handle = remote.get_item_handle("network_interface", "eth0", token)
    remote.modify_network_interface(
        interface_handle, ["ipv4", "address"], "1.2.3.5", token
    )
    remote.modify_network_interface(
        interface_handle, ["dns", "name"], "host2.example.org", token
    )
    result = remote.save_network_interface(
        interface_handle, True, True, "bypass", token
    )

    # Assert
    assert result
    saved_interface = remote.get_network_interface(interface_handle, token=token)
    assert isinstance(saved_interface, dict)
    assert saved_interface["ipv4"]["address"] == "1.2.3.5"
    assert saved_interface["dns"]["name"] == "host2.example.org"
