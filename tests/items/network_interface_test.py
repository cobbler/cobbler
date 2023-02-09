import logging
from ipaddress import AddressValueError

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.system import NetworkInterface
from tests.conftest import does_not_raise


@pytest.fixture()
def test_settings(mocker, cobbler_api: CobblerAPI):
    settings = mocker.MagicMock(
        name="interface_setting_mock", spec=cobbler_api.settings()
    )
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_network_interface_object_creation(cobbler_api: CobblerAPI):
    # Arrange

    # Act
    interface = NetworkInterface(cobbler_api, "")

    # Assert
    assert isinstance(interface, NetworkInterface)


def test_network_interface_to_dict(cobbler_api: CobblerAPI):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    result = interface.to_dict()

    # Assert
    assert isinstance(result, dict)
    assert "logger" not in result
    assert "api" not in result
    assert len(result) == 23


@pytest.mark.parametrize(
    "input_dict,modified_field,expected_result,expect_logger_warning",
    [
        ({"dns_name": "host.example.com"}, "dns_name", "host.example.com", False),
        ({"not_existing": "invalid"}, "dhcp_tag", "", True),
    ],
)
def test_network_interface_from_dict(
    caplog,
    cobbler_api: CobblerAPI,
    input_dict,
    modified_field,
    expected_result,
    expect_logger_warning,
):
    # Arrange
    caplog.set_level(logging.INFO)
    interface = NetworkInterface(cobbler_api, "")

    # Act
    interface.from_dict(input_dict)

    # Assert
    assert getattr(interface, f"_{modified_field}") == expected_result
    if expect_logger_warning:
        assert "The following keys were ignored" in caplog.records[0].message
    else:
        assert len(caplog.records) == 0


def test_serialize():
    pass


def test_deserialize():
    pass


@pytest.mark.parametrize(
    "input_dhcp_tag,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        ("test", "test", does_not_raise()),
        (0, "", pytest.raises(TypeError)),
    ],
)
def test_dhcp_tag(cobbler_api: CobblerAPI, input_dhcp_tag, expected_result, expected_exception):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.dhcp_tag = input_dhcp_tag

        # Assert
        assert isinstance(interface.dhcp_tag, str)
        assert interface.dhcp_tag == expected_result


def test_cnames(cobbler_api: CobblerAPI):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    interface.cnames = []

    # Assert
    assert isinstance(interface.cnames, list)
    assert interface.cnames == []


def test_static_routes(cobbler_api: CobblerAPI):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    interface.static_routes = []

    # Assert
    assert isinstance(interface.static_routes, list)
    assert interface.static_routes == []


@pytest.mark.parametrize(
    "input_static,expected_result,expected_exception",
    [
        ("", False, does_not_raise()),
        (0, False, does_not_raise()),
        (1, True, does_not_raise()),
        ([], "", pytest.raises(TypeError)),
    ],
)
def test_static(cobbler_api: CobblerAPI, input_static, expected_result, expected_exception):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.static = input_static

        # Assert
        assert isinstance(interface.static, bool)
        assert interface.static is expected_result


@pytest.mark.parametrize(
    "input_management,expected_result,expected_exception",
    [
        ("", False, does_not_raise()),
        (0, False, does_not_raise()),
        (1, True, does_not_raise()),
        ([], "", pytest.raises(TypeError)),
    ],
)
def test_management(cobbler_api: CobblerAPI, input_management, expected_result, expected_exception):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.management = input_management

        # Assert
        assert isinstance(interface.management, bool)
        assert interface.management is expected_result


@pytest.mark.parametrize(
    "input_dns_name,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        ("host.example.org", "host.example.org", does_not_raise()),
        ("duplicate.example.org", "", pytest.raises(ValueError)),
    ],
)
def test_dns_name(
    cobbler_api: CobblerAPI,
    create_distro,
    create_profile,
    create_system,
    input_dns_name,
    expected_result,
    expected_exception,
):
    # Arrange
    distro = create_distro()
    profile = create_profile(distro.name)
    system = create_system(profile.name)
    system.interfaces["default"].dns_name = "duplicate.example.org"
    cobbler_api.add_system(system)
    interface = NetworkInterface(cobbler_api, system.name)

    # Act
    with expected_exception:
        # TODO: Test matching self
        interface.dns_name = input_dns_name

        # Assert
        assert isinstance(interface.dns_name, str)
        assert interface.dns_name == expected_result


@pytest.mark.parametrize(
    "input_mac,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        ("AA:BB", "", pytest.raises(ValueError)),
        (0, "", pytest.raises(TypeError)),
        ("random", "AA:BB:CC:DD:EE:FF", does_not_raise()),
        ("AA:AA:AA:AA:AA:AA", "", pytest.raises(ValueError)),
    ],
)
def test_mac_address(
    mocker,
    cobbler_api: CobblerAPI,
    create_distro,
    create_profile,
    create_system,
    input_mac,
    expected_result,
    expected_exception,
):
    # Arrange
    distro = create_distro()
    profile = create_profile(distro.name)
    system = create_system(profile.name)
    system.interfaces["default"].mac_address = "AA:AA:AA:AA:AA:AA"
    cobbler_api.add_system(system)
    system2 = create_system(profile_name=profile.name, name="test_system2")
    system2.interfaces["default"].mac_address = "random"
    cobbler_api.add_system(system2)
    mocker.patch("cobbler.utils.get_random_mac", return_value="AA:BB:CC:DD:EE:FF")
    interface = NetworkInterface(cobbler_api, system.name)

    # Act
    with expected_exception:
        # TODO: match self
        interface.mac_address = input_mac

        # Assert
        assert isinstance(interface.mac_address, str)
        assert interface.mac_address == expected_result


def test_netmask(cobbler_api: CobblerAPI):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    interface.netmask = ""

    # Assert
    assert isinstance(interface.netmask, str)
    assert interface.netmask == ""


def test_if_gateway(cobbler_api: CobblerAPI):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    interface.if_gateway = ""

    # Assert
    assert isinstance(interface.if_gateway, str)
    assert interface.if_gateway == ""


@pytest.mark.parametrize(
    "input_virt_bridge,expected_result,expected_exception",
    [
        ("", "xenbr0", does_not_raise()),
        ("<<inherit>>", "xenbr0", does_not_raise()),
        ("test", "test", does_not_raise()),
        (0, "", pytest.raises(TypeError)),
    ],
)
def test_virt_bridge(
    cobbler_api: CobblerAPI, input_virt_bridge, expected_result, expected_exception
):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.virt_bridge = input_virt_bridge

        # Assert
        assert isinstance(interface.virt_bridge, str)
        assert interface.virt_bridge == expected_result


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("foobar_not_existing", pytest.raises(ValueError), None),
        ("", does_not_raise(), enums.NetworkInterfaceType.NA),
        ("na", does_not_raise(), enums.NetworkInterfaceType.NA),
        ("bond", does_not_raise(), enums.NetworkInterfaceType.BOND),
        ("bond_slave", does_not_raise(), enums.NetworkInterfaceType.BOND_SLAVE),
        ("bridge", does_not_raise(), enums.NetworkInterfaceType.BRIDGE),
        ("bridge_slave", does_not_raise(), enums.NetworkInterfaceType.BRIDGE_SLAVE),
        (
            "bonded_bridge_slave",
            does_not_raise(),
            enums.NetworkInterfaceType.BONDED_BRIDGE_SLAVE,
        ),
        ("bmc", does_not_raise(), enums.NetworkInterfaceType.BMC),
        ("infiniband", does_not_raise(), enums.NetworkInterfaceType.INFINIBAND),
        (0, does_not_raise(), enums.NetworkInterfaceType.NA),
        (1, does_not_raise(), enums.NetworkInterfaceType.BOND),
        (2, does_not_raise(), enums.NetworkInterfaceType.BOND_SLAVE),
        (3, does_not_raise(), enums.NetworkInterfaceType.BRIDGE),
        (4, does_not_raise(), enums.NetworkInterfaceType.BRIDGE_SLAVE),
        (5, does_not_raise(), enums.NetworkInterfaceType.BONDED_BRIDGE_SLAVE),
        (6, does_not_raise(), enums.NetworkInterfaceType.BMC),
        (7, does_not_raise(), enums.NetworkInterfaceType.INFINIBAND),
    ],
)
def test_network_interface_type(
    cobbler_api, value, expected_exception, expected_result
):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.interface_type = value

        # Assert
        assert interface.interface_type == expected_result


@pytest.mark.parametrize(
    "input_interface_master,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        (0, "", pytest.raises(TypeError)),
    ],
)
def test_interface_master(
    cobbler_api: CobblerAPI, input_interface_master, expected_result, expected_exception
):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.interface_master = input_interface_master

        # Assert
        assert isinstance(interface.interface_master, str)
        assert interface.interface_master == expected_result


@pytest.mark.parametrize(
    "input_bonding_opts,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        (0, "", pytest.raises(TypeError)),
    ],
)
def test_bonding_opts(
    cobbler_api: CobblerAPI, input_bonding_opts, expected_result, expected_exception
):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.bonding_opts = input_bonding_opts

        # Assert
        assert isinstance(interface.bonding_opts, str)
        assert interface.bonding_opts == expected_result


@pytest.mark.parametrize(
    "input_bridge_opts,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        (0, "", pytest.raises(TypeError)),
    ],
)
def test_bridge_opts(
    cobbler_api: CobblerAPI, input_bridge_opts, expected_result, expected_exception
):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.bridge_opts = input_bridge_opts

        # Assert
        assert isinstance(interface.bridge_opts, str)
        assert interface.bridge_opts == expected_result


@pytest.mark.parametrize(
    "input_ip_address,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        ("172.30.0.1", "172.30.0.1", does_not_raise()),
        ("172.30.0.2", "", pytest.raises(ValueError)),
    ],
)
def test_ip_address(
    cobbler_api: CobblerAPI,
    create_distro,
    create_profile,
    create_system,
    input_ip_address,
    expected_result,
    expected_exception,
):
    # Arrange
    distro = create_distro()
    profile = create_profile(distro.name)
    system = create_system(profile.name)
    system.interfaces["default"].ip_address = "172.30.0.2"
    cobbler_api.add_system(system)
    interface = NetworkInterface(cobbler_api, system.name)

    # Act
    with expected_exception:
        # TODO: Match self in loop
        interface.ip_address = input_ip_address

        # Assert
        assert isinstance(interface.ip_address, str)
        assert interface.ip_address == expected_result


@pytest.mark.parametrize(
    "input_address,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        ("2001:db8:3c4d::1", "2001:db8:3c4d::1", does_not_raise()),
        ("2001:db8:3c4d::2", "", pytest.raises(ValueError)),
    ],
)
def test_ipv6_address(
    cobbler_api: CobblerAPI,
    create_distro,
    create_profile,
    create_system,
    input_address,
    expected_result,
    expected_exception,
):
    # Arrange
    distro = create_distro()
    profile = create_profile(distro.name)
    system = create_system(profile.name)
    system.interfaces["default"].ipv6_address = "2001:db8:3c4d::2"
    cobbler_api.add_system(system)
    interface = NetworkInterface(cobbler_api, system.name)

    # Act
    with expected_exception:
        # TODO: match self
        interface.ipv6_address = input_address

        # Assert
        assert isinstance(interface.ipv6_address, str)
        assert interface.ipv6_address == expected_result


@pytest.mark.parametrize(
    "input_ipv6_prefix,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        (0, "", pytest.raises(TypeError)),
    ],
)
def test_ipv6_prefix(
    cobbler_api: CobblerAPI, input_ipv6_prefix, expected_result, expected_exception
):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.ipv6_prefix = input_ipv6_prefix

        # Assert
        assert isinstance(interface.ipv6_prefix, str)
        assert interface.ipv6_prefix == expected_result


@pytest.mark.parametrize(
    "input_secondaries,expected_result,expected_exception",
    [
        ([""], [""], does_not_raise()),
        (["::1"], ["::1"], does_not_raise()),
        ("invalid", [], pytest.raises(AddressValueError)),
    ],
)
def test_ipv6_secondaries(
    cobbler_api: CobblerAPI, input_secondaries, expected_result, expected_exception
):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.ipv6_secondaries = input_secondaries

        # Assert
        assert isinstance(interface.ipv6_secondaries, list)
        assert interface.ipv6_secondaries == expected_result


@pytest.mark.parametrize(
    "input_address,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        ("::1", "::1", does_not_raise()),
        (None, "", pytest.raises(TypeError)),
        ("invalid", "", pytest.raises(AddressValueError)),
    ],
)
def test_ipv6_default_gateway(
    cobbler_api: CobblerAPI, input_address, expected_result, expected_exception
):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.ipv6_default_gateway = input_address

        # Assert
        assert isinstance(interface.ipv6_default_gateway, str)
        assert interface.ipv6_default_gateway == expected_result


def test_ipv6_static_routes(cobbler_api: CobblerAPI):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    interface.ipv6_static_routes = []

    # Assert
    assert isinstance(interface.ipv6_static_routes, list)
    assert interface.ipv6_static_routes == []


@pytest.mark.parametrize(
    "input_ipv6_mtu,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        (0, "", pytest.raises(TypeError)),
    ],
)
def test_ipv6_mtu(cobbler_api: CobblerAPI, input_ipv6_mtu, expected_result, expected_exception):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.ipv6_mtu = input_ipv6_mtu

        # Assert
        assert isinstance(interface.ipv6_mtu, str)
        assert interface.ipv6_mtu == expected_result


@pytest.mark.parametrize(
    "input_mtu,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        (0, "", pytest.raises(TypeError)),
    ],
)
def test_mtu(cobbler_api: CobblerAPI, input_mtu, expected_result, expected_exception):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.mtu = input_mtu

        # Assert
        assert isinstance(interface.mtu, str)
        assert interface.mtu == expected_result


@pytest.mark.parametrize(
    "input_connected_mode,expected_result,expected_exception",
    [
        ("", False, does_not_raise()),
        (0, False, does_not_raise()),
        (1, True, does_not_raise()),
        ([], "", pytest.raises(TypeError)),
    ],
)
def test_connected_mode(
    cobbler_api: CobblerAPI, input_connected_mode, expected_result, expected_exception
):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.connected_mode = input_connected_mode

        # Assert
        assert isinstance(interface.connected_mode, bool)
        assert interface.connected_mode is expected_result


@pytest.mark.parametrize(
    "input_modify_interface,expected_modified_field,expected_value,expected_exception",
    [
        ({}, "mtu", "", does_not_raise()),
        ({"mtu-eth0": "test"}, "mtu", "test", does_not_raise()),
    ],
)
def test_modify_interface(
    cobbler_api: CobblerAPI,
    input_modify_interface,
    expected_modified_field,
    expected_value,
    expected_exception,
):
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.modify_interface(input_modify_interface)

        # Assert
        assert getattr(interface, expected_modified_field) == expected_value


def test_inheritance(mocker, cobbler_api: CobblerAPI, test_settings):
    """
    Checking that inherited properties are correctly inherited from settings and
    that the <<inherit>> value can be set for them.
    """
    # Arrange
    mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
    interface = NetworkInterface(cobbler_api, "")

    # Act
    for key, key_value in interface.__dict__.items():
        if key_value == enums.VALUE_INHERITED:
            new_key = key[1:].lower()
            new_value = getattr(interface, new_key)
            settings_name = new_key
            if new_key == "owners":
                settings_name = "default_ownership"
            if hasattr(test_settings, f"default_{settings_name}"):
                settings_name = f"default_{settings_name}"
            if hasattr(test_settings, settings_name):
                setting = getattr(test_settings, settings_name)
                if isinstance(setting, str):
                    new_value = "test_inheritance"
                elif isinstance(setting, bool):
                    new_value = True
                elif isinstance(setting, int):
                    new_value = 1
                elif isinstance(setting, float):
                    new_value = 1.0
                elif isinstance(setting, dict):
                    new_value = {"test_inheritance": "test_inheritance"}
                elif isinstance(setting, list):
                    new_value = ["test_inheritance"]
                setattr(test_settings, settings_name, new_value)

            prev_value = getattr(interface, new_key)
            setattr(interface, new_key, enums.VALUE_INHERITED)

            # Assert
            assert prev_value == new_value
            assert prev_value == getattr(interface, new_key)
