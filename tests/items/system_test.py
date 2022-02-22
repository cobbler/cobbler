import pytest

from cobbler import enums
from cobbler.items.system import NetworkInterface, System
from tests.conftest import does_not_raise


def test_object_creation(cobbler_api):
    # Arrange

    # Act
    system = System(cobbler_api)

    # Arrange
    assert isinstance(system, System)


def test_make_clone(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    result = system.make_clone()

    # Assert
    assert result != system


# Properties Tests


def test_ipv6_autoconfiguration(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.ipv6_autoconfiguration = False

    # Assert
    assert not system.ipv6_autoconfiguration


def test_repos_enabled(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.repos_enabled = False

    # Assert
    assert not system.repos_enabled


def test_autoinstall(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.autoinstall = ""

    # Assert
    assert system.autoinstall == ""


def test_boot_loaders(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.boot_loaders = []

    # Assert
    assert system.boot_loaders == []


@pytest.mark.parametrize("value,expected", [
    (0, does_not_raise()),
    (0.0, pytest.raises(TypeError)),
    ("", does_not_raise()),
    ("Test", does_not_raise()),
    ([], pytest.raises(TypeError)),
    ({}, pytest.raises(TypeError)),
    (None, pytest.raises(TypeError)),
    (False, does_not_raise()),
    (True, does_not_raise())
])
def test_enable_ipxe(cobbler_api, value, expected):
    # Arrange
    distro = System(cobbler_api)

    # Act
    with expected:
        distro.enable_ipxe = value

        # Assert
        assert isinstance(distro.enable_ipxe, bool)
        assert distro.enable_ipxe or not distro.enable_ipxe


def test_gateway(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.gateway = ""

    # Assert
    assert system.gateway == ""


def test_hostname(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.hostname = ""

    # Assert
    assert system.hostname == ""


def test_image(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.image = ""

    # Assert
    assert system.image == ""


def test_ipv6_default_device(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.ipv6_default_device = ""

    # Assert
    assert system.ipv6_default_device == ""


def test_name_servers(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.name_servers = []

    # Assert
    assert system.name_servers == []


def test_name_servers_search(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.name_servers_search = ""

    # Assert
    assert system.name_servers_search == ""


@pytest.mark.parametrize("value,expected", [
    (0, does_not_raise()),
    (0.0, pytest.raises(TypeError)),
    ("", does_not_raise()),
    ("Test", does_not_raise()),
    ([], pytest.raises(TypeError)),
    ({}, pytest.raises(TypeError)),
    (None, pytest.raises(TypeError)),
    (False, does_not_raise()),
    (True, does_not_raise())
])
def test_netboot_enabled(cobbler_api, value, expected):
    # Arrange
    distro = System(cobbler_api)

    # Act
    with expected:
        distro.netboot_enabled = value

        # Assert
        assert isinstance(distro.netboot_enabled, bool)
        assert distro.netboot_enabled or not distro.netboot_enabled


def test_next_server_v4(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.next_server_v4 = ""

    # Assert
    assert system.next_server_v4 == ""


def test_next_server_v6(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.next_server_v6 = ""

    # Assert
    assert system.next_server_v6 == ""


def test_filename(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.filename = "<<inherit>>"

    # Assert
    assert system.filename == "<<inherit>>"


def test_power_address(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_address = ""

    # Assert
    assert system.power_address == ""


def test_power_id(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_id = ""

    # Assert
    assert system.power_id == ""


def test_power_pass(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_pass = ""

    # Assert
    assert system.power_pass == ""


def test_power_type(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_type = "docker"

    # Assert
    assert system.power_type == "docker"


def test_power_user(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_user = ""

    # Assert
    assert system.power_user == ""


def test_power_options(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_options = ""

    # Assert
    assert system.power_options == ""


def test_power_identity_file(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_identity_file = ""

    # Assert
    assert system.power_identity_file == ""


def test_profile(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.profile = ""

    # Assert
    assert system.profile == ""


def test_proxy(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.proxy = ""

    # Assert
    assert system.proxy == ""


def test_redhat_management_key(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.redhat_management_key = ""

    # Assert
    assert system.redhat_management_key == ""


def test_server(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.server = ""

    # Assert
    assert system.server == "<<inherit>>"


def test_status(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.status = ""

    # Assert
    assert system.status == ""


def test_virt_auto_boot(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.virt_auto_boot = False

    # Assert
    assert not system.virt_auto_boot


def test_virt_cpus(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.virt_cpus = 5

    # Assert
    assert system.virt_cpus == 5


@pytest.mark.parametrize("value,expected_exception", [
    ("qcow2", does_not_raise()),
    (enums.VirtDiskDrivers.QCOW2, does_not_raise()),
    (False, pytest.raises(TypeError)),
    ("", pytest.raises(ValueError))
])
def test_virt_disk_driver(cobbler_api, value, expected_exception):
    # Arrange
    system = System(cobbler_api)

    # Act
    with expected_exception:
        system.virt_disk_driver = value

        # Assert
        if isinstance(value, str):
            assert system.virt_disk_driver.value == value
        else:
            assert system.virt_disk_driver == value


def test_virt_file_size(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.virt_file_size = 1.0

    # Assert
    assert system.virt_file_size == 1.0


def test_virt_path(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.virt_path = ""

    # Assert
    assert system.virt_path == "<<inherit>>"


def test_virt_pxe_boot(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.virt_pxe_boot = False

    # Assert
    assert not system.virt_pxe_boot


def test_virt_ram(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.virt_ram = 5

    # Assert
    assert system.virt_ram == 5


@pytest.mark.parametrize("value,expected_exception", [
    # ("<<inherit>>", does_not_raise()),
    ("qemu", does_not_raise()),
    (enums.VirtType.QEMU, does_not_raise()),
    ("", pytest.raises(ValueError)),
    (False, pytest.raises(TypeError))
])
def test_virt_type(cobbler_api, value, expected_exception):
    # Arrange
    system = System(cobbler_api)

    # Act
    with expected_exception:
        system.virt_type = value

        # Assert
        if isinstance(value, str):
            assert system.virt_type.value == value
        else:
            assert system.virt_type == value


def test_serial_device(cobbler_api):
    # Arrange
    system = System(cobbler_api)

    # Act
    system.serial_device = 5

    # Assert
    assert system.serial_device == 5


@pytest.mark.parametrize("value,expected_exception", [
    (enums.BaudRates.B110, does_not_raise()),
    (110, does_not_raise()),
    # FIXME: (False, pytest.raises(TypeError)) --> This does not raise a TypeError but instead a value Error.
])
def test_serial_baud_rate(cobbler_api, value, expected_exception):
    # Arrange
    system = System(cobbler_api)

    # Act
    with expected_exception:
        system.serial_baud_rate = value

        # Assert
        if isinstance(value, int):
            assert system.serial_baud_rate.value == value
        else:
            assert system.serial_baud_rate == value


def test_from_dict_with_network_interface(cobbler_api):
    # Arrange
    system = System(cobbler_api)
    sys_dict = system.to_dict()

    # Act
    system.from_dict(sys_dict)

    # Assert
    assert "default" in system.interfaces


@pytest.mark.parametrize("input_mac,input_ipv4,input_ipv6,expected_result", [
    ("AA:BB:CC:DD:EE:FF", "192.168.1.2", "::1", True),
    ("", "192.168.1.2", "", True),
    ("", "", "::1", True),
    ("AA:BB:CC:DD:EE:FF", "", "", True),
    ("", "", "", False),
])
def test_is_management_supported(cobbler_api, input_mac, input_ipv4, input_ipv6, expected_result):
    # Arrange
    system = System(cobbler_api)
    system.interfaces["default"].mac_address = input_mac
    system.interfaces["default"].ip_address = input_ipv4
    system.interfaces["default"].ipv6_address = input_ipv6

    # Act
    result = system.is_management_supported()

    # Assert
    assert result is expected_result


############################################################################################


def test_network_interface_object_creation(cobbler_api):
    # Arrange

    # Act
    interface = NetworkInterface(cobbler_api)

    # Assert
    assert isinstance(interface, NetworkInterface)


def test_network_interface_to_dict(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    result = interface.to_dict()

    # Assert
    assert isinstance(result, dict)
    assert "logger" not in result
    assert "api" not in result
    assert len(result) == 23


def test_network_interface_from_dict(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)
    intf_dict = interface.to_dict()

    # Act
    interface.from_dict(intf_dict)

    # Assert
    assert True


def test_dhcp_tag(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.dhcp_tag = ""

    # Assert
    assert isinstance(interface.dhcp_tag, str)
    assert interface.dhcp_tag == ""


def test_cnames(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.cnames = []

    # Assert
    assert isinstance(interface.cnames, list)
    assert interface.cnames == []


def test_static_routes(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.static_routes = []

    # Assert
    assert isinstance(interface.static_routes, list)
    assert interface.static_routes == []


def test_static(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.static = True

    # Assert
    assert isinstance(interface.static, bool)
    assert interface.static is True


def test_management(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.management = True

    # Assert
    assert isinstance(interface.management, bool)
    assert interface.management is True


def test_dns_name(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.dns_name = ""

    # Assert
    assert isinstance(interface.dns_name, str)
    assert interface.dns_name == ""


def test_mac_address(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.mac_address = ""

    # Assert
    assert isinstance(interface.mac_address, str)
    assert interface.mac_address == ""


def test_netmask(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.netmask = ""

    # Assert
    assert isinstance(interface.netmask, str)
    assert interface.netmask == ""


def test_if_gateway(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.if_gateway = ""

    # Assert
    assert isinstance(interface.if_gateway, str)
    assert interface.if_gateway == ""


def test_virt_bridge(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.virt_bridge = ""

    # Assert
    assert isinstance(interface.virt_bridge, str)
    assert interface.virt_bridge == "xenbr0"


def test_interface_type(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.interface_type = enums.NetworkInterfaceType.NA

    # Assert
    assert isinstance(interface.interface_type, enums.NetworkInterfaceType)
    assert interface.interface_type == enums.NetworkInterfaceType.NA


def test_interface_master(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.interface_master = ""

    # Assert
    assert isinstance(interface.interface_master, str)
    assert interface.interface_master == ""


def test_bonding_opts(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.bonding_opts = ""

    # Assert
    assert isinstance(interface.bonding_opts, str)
    assert interface.bonding_opts == ""


def test_bridge_opts(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.bridge_opts = ""

    # Assert
    assert isinstance(interface.bridge_opts, str)
    assert interface.bridge_opts == ""


def test_ipv6_address(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.ipv6_address = ""

    # Assert
    assert isinstance(interface.ipv6_address, str)
    assert interface.ipv6_address == ""


def test_ipv6_prefix(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.ipv6_prefix = ""

    # Assert
    assert isinstance(interface.ipv6_prefix, str)
    assert interface.ipv6_prefix == ""


def test_ipv6_secondaries(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.ipv6_secondaries = []

    # Assert
    assert isinstance(interface.ipv6_secondaries, list)
    assert interface.ipv6_secondaries == []


def test_ipv6_default_gateway(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.ipv6_default_gateway = ""

    # Assert
    assert isinstance(interface.ipv6_default_gateway, str)
    assert interface.ipv6_default_gateway == ""


def test_ipv6_static_routes(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.ipv6_static_routes = []

    # Assert
    assert isinstance(interface.ipv6_static_routes, list)
    assert interface.ipv6_static_routes == []


def test_ipv6_mtu(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.ipv6_mtu = ""

    # Assert
    assert isinstance(interface.ipv6_mtu, str)
    assert interface.ipv6_mtu == ""


def test_mtu(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.mtu = ""

    # Assert
    assert isinstance(interface.mtu, str)
    assert interface.mtu == ""


def test_connected_mode(cobbler_api):
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    interface.connected_mode = True

    # Assert
    assert isinstance(interface.connected_mode, bool)
    assert interface.connected_mode is True
