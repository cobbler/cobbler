"""
Tests that validate the functionality of the module that is responsible for providing network interface related
functionality.
"""

import logging
from ipaddress import AddressValueError
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Union

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.network_interface import NetworkInterface
from cobbler.items.profile import Profile
from cobbler.items.system import System
from cobbler.settings import Settings

from tests.conftest import does_not_raise

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="test_settings")
def fixture_test_settings(mocker: "MockerFixture", cobbler_api: CobblerAPI) -> Settings:
    """
    Fixture to provide a mock settings object for testing inheritance in NetworkInterface.
    """
    settings = mocker.MagicMock(
        name="interface_setting_mock", spec=cobbler_api.settings()
    )
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_network_interface_object_creation(cobbler_api: CobblerAPI):
    """
    Test to verify that a NetworkInterface object can be created.
    """
    # Arrange

    # Act
    interface = NetworkInterface(cobbler_api, "")

    # Assert
    assert isinstance(interface, NetworkInterface)


def test_network_interface_to_dict(cobbler_api: CobblerAPI):
    """
    Test to verify that the to_dict method of NetworkInterface works as expected.
    """
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    result = interface.to_dict()

    # Assert
    assert isinstance(result, dict)
    assert "logger" not in result
    assert "api" not in result
    assert result.get("virt_bridge") == enums.VALUE_INHERITED
    assert len(result) == 23


def test_network_interface_to_dict_resolved(cobbler_api: CobblerAPI):
    """
    Test to verify that the to_dict method of NetworkInterface works as expected when resolved is True.
    """
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    result = interface.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("virt_bridge") == "virbr0"
    assert enums.VALUE_INHERITED not in str(result)


@pytest.mark.parametrize(
    "input_dict,modified_field,expected_result,expect_logger_warning",
    [
        ({"dns_name": "host.example.com"}, "dns_name", "host.example.com", False),
        ({"not_existing": "invalid"}, "dhcp_tag", "", True),
    ],
)
def test_network_interface_from_dict(
    caplog: pytest.LogCaptureFixture,
    cobbler_api: CobblerAPI,
    input_dict: Dict[str, str],
    modified_field: str,
    expected_result: str,
    expect_logger_warning: bool,
):
    """
    Test to verify that the from_dict method of NetworkInterface works as expected.
    """
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
    """
    Test to verify that the serialize method of NetworkInterface works as expected.
    """


def test_deserialize():
    """
    Test to verify that the deserialize method of NetworkInterface works as expected.
    """


@pytest.mark.parametrize(
    "input_dhcp_tag,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        ("test", "test", does_not_raise()),
        (0, "", pytest.raises(TypeError)),
    ],
)
def test_dhcp_tag(
    cobbler_api: CobblerAPI,
    input_dhcp_tag: Any,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test to verify that the dhcp_tag property of NetworkInterface works as expected.
    """
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.dhcp_tag = input_dhcp_tag

        # Assert
        assert isinstance(interface.dhcp_tag, str)
        assert interface.dhcp_tag == expected_result


def test_cnames(cobbler_api: CobblerAPI):
    """
    Test to verify that the cnames property of NetworkInterface works as expected.
    """
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    interface.cnames = []

    # Assert
    assert isinstance(interface.cnames, list)
    assert interface.cnames == []


def test_static_routes(cobbler_api: CobblerAPI):
    """
    Test to verify that the static_routes property of NetworkInterface works as expected.
    """
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
def test_static(
    cobbler_api: CobblerAPI,
    input_static: Union[int, List[int], str],
    expected_result: Union[bool, str],
    expected_exception: Any,
):
    """
    Test to verify that the static property of NetworkInterface works as expected.
    """
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.static = input_static  # type: ignore

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
def test_management(
    cobbler_api: CobblerAPI,
    input_management: Any,
    expected_result: Union[bool, str],
    expected_exception: Any,
):
    """
    Test to verify that the management property of NetworkInterface works as expected.
    """
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
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str], System],
    input_dns_name: str,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test to verify that the dns_name property of NetworkInterface works as expected.
    """
    # Arrange
    distro = create_distro()
    profile = create_profile(distro.uid)
    system = create_system(profile.uid)
    system.interfaces["default"].dns_name = "duplicate.example.org"
    cobbler_api.add_system(system)
    interface = NetworkInterface(cobbler_api, "")

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
        (
            "80:00:0a:43:fe:80:00:00:00:00:00:00:0e:fa:aa:bb:cc:dd:ee:ff",
            "80:00:0a:43:fe:80:00:00:00:00:00:00:0e:fa:aa:bb:cc:dd:ee:ff",
            does_not_raise(),
        ),
        ("AA:AA:AA:AA:AA:AA", "", pytest.raises(ValueError)),
    ],
)
def test_mac_address(
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
    input_mac: str,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test to verify that the mac_address property of NetworkInterface works as expected.
    """
    # Arrange
    distro = create_distro()
    profile = create_profile(distro.uid)
    system: System = create_system(profile.uid)
    system.interfaces["default"].mac_address = "AA:AA:AA:AA:AA:AA"
    cobbler_api.add_system(system)
    system2: System = create_system(profile_uid=profile.uid, name="test_system2")
    system2.interfaces["default"].mac_address = "random"
    cobbler_api.add_system(system2)
    mocker.patch("cobbler.utils.get_random_mac", return_value="AA:BB:CC:DD:EE:FF")
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        # TODO: match self
        interface.mac_address = input_mac

        # Assert
        assert isinstance(interface.mac_address, str)
        assert interface.mac_address == expected_result


def test_netmask(cobbler_api: CobblerAPI):
    """
    Test to verify that the netmask property of NetworkInterface works as expected.
    """
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    interface.netmask = ""

    # Assert
    assert isinstance(interface.netmask, str)
    assert interface.netmask == ""


def test_if_gateway(cobbler_api: CobblerAPI):
    """
    Test to verify that the if_gateway property of NetworkInterface works as expected.
    """
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
        ("", "virbr0", does_not_raise()),
        ("<<inherit>>", "virbr0", does_not_raise()),
        ("test", "test", does_not_raise()),
        (0, "", pytest.raises(TypeError)),
    ],
)
def test_virt_bridge(
    cobbler_api: CobblerAPI,
    input_virt_bridge: Union[str, int],
    expected_result: str,
    expected_exception: Any,
):
    """
    Test to verify that the virt_bridge property of NetworkInterface works as expected.
    """
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.virt_bridge = input_virt_bridge  # type: ignore

        # Assert
        assert isinstance(interface.virt_bridge, str)
        assert interface.virt_bridge == expected_result


@pytest.mark.parametrize(
    "input_interface_type,expected_result,expected_exception",
    [
        ([], enums.NetworkInterfaceType.NA, pytest.raises(TypeError)),
        (0, enums.NetworkInterfaceType.NA, does_not_raise()),
        (100, enums.NetworkInterfaceType.NA, pytest.raises(ValueError)),
        ("INVALID", enums.NetworkInterfaceType.NA, pytest.raises(ValueError)),
        # TODO: Create test for last ValueError
        ("NA", enums.NetworkInterfaceType.NA, does_not_raise()),
        ("na", enums.NetworkInterfaceType.NA, does_not_raise()),
    ],
)
def test_interface_type(
    cobbler_api: CobblerAPI,
    input_interface_type: Any,
    expected_result: enums.NetworkInterfaceType,
    expected_exception: Any,
):
    """
    Test to verify that the interface_type property of NetworkInterface works as expected.
    """
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.interface_type = input_interface_type

        # Assert
        assert isinstance(interface.interface_type, enums.NetworkInterfaceType)
        assert interface.interface_type == expected_result


@pytest.mark.parametrize(
    "input_interface_master,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        (0, "", pytest.raises(TypeError)),
    ],
)
def test_interface_master(
    cobbler_api: CobblerAPI,
    input_interface_master: Any,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test to verify that the interface_master property of NetworkInterface works as expected.
    """
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
    cobbler_api: CobblerAPI,
    input_bonding_opts: Any,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test to verify that the bonding_opts property of NetworkInterface works as expected.
    """
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
    cobbler_api: CobblerAPI,
    input_bridge_opts: Any,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test to verify that the bridge_opts property of NetworkInterface works as expected.
    """
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
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str], System],
    input_ip_address: str,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test to verify that the ip_address property of NetworkInterface works as expected.
    """
    # Arrange
    distro = create_distro()
    profile = create_profile(distro.uid)
    system = create_system(profile.uid)
    system.interfaces["default"].ip_address = "172.30.0.2"
    cobbler_api.add_system(system)
    interface = NetworkInterface(cobbler_api, "")

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
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str], System],
    input_address: str,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test to verify that the ipv6_address property of NetworkInterface works as expected.
    """
    # Arrange
    distro = create_distro()
    profile = create_profile(distro.uid)
    system = create_system(profile.uid)
    system.interfaces["default"].ipv6_address = "2001:db8:3c4d::2"
    cobbler_api.add_system(system)
    interface = NetworkInterface(cobbler_api, "")

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
    cobbler_api: CobblerAPI,
    input_ipv6_prefix: Any,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test to verify that the ipv6_prefix property of NetworkInterface works as expected.
    """
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
    cobbler_api: CobblerAPI,
    input_secondaries: Any,
    expected_result: List[str],
    expected_exception: Any,
):
    """
    Test to verify that the ipv6_secondaries property of NetworkInterface works as expected.
    """
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.ipv6_secondaries = input_secondaries

        # Assert
        assert isinstance(interface.ipv6_secondaries, list)
        assert interface.ipv6_secondaries == expected_result  # type: ignore


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
    cobbler_api: CobblerAPI,
    input_address: Any,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test to verify that the ipv6_default_gateway property of NetworkInterface works as expected.
    """
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.ipv6_default_gateway = input_address

        # Assert
        assert isinstance(interface.ipv6_default_gateway, str)
        assert interface.ipv6_default_gateway == expected_result


def test_ipv6_static_routes(cobbler_api: CobblerAPI):
    """
    Test to verify that the ipv6_static_routes property of NetworkInterface works as expected.
    """
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
def test_ipv6_mtu(
    cobbler_api: CobblerAPI,
    input_ipv6_mtu: Any,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test to verify that the ipv6_mtu property of NetworkInterface works as expected.
    """
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
def test_mtu(
    cobbler_api: CobblerAPI,
    input_mtu: Any,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test to verify that the mtu property of NetworkInterface works as expected.
    """
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
    cobbler_api: CobblerAPI,
    input_connected_mode: Any,
    expected_result: Any,
    expected_exception: Any,
):
    """
    Test to verify that the connected_mode property of NetworkInterface works as expected.
    """
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
    input_modify_interface: Dict[str, str],
    expected_modified_field: str,
    expected_value: str,
    expected_exception: Any,
):
    """
    Test to verify that the modify_interface method of NetworkInterface works as expected.
    """
    # Arrange
    interface = NetworkInterface(cobbler_api, "")

    # Act
    with expected_exception:
        interface.modify_interface(input_modify_interface)

        # Assert
        assert getattr(interface, expected_modified_field) == expected_value


def test_inheritance(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, test_settings: Settings
):
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
