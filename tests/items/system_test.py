"""
Test module that asserts that Cobbler System functionallity is working as expected.
"""

from typing import TYPE_CHECKING, Any, Callable, List, Optional

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.network_interface import NetworkInterface
from cobbler.items.profile import Profile
from cobbler.items.system import System
from cobbler.settings import Settings

from tests.conftest import does_not_raise

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture()
def test_settings(mocker: "MockerFixture", cobbler_api: CobblerAPI) -> Settings:
    """
    Fixture to mock the real settings with the desired values.
    """
    settings = mocker.MagicMock(
        name="profile_setting_mock", spec=cobbler_api.settings()
    )
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_object_creation(cobbler_api: CobblerAPI):
    """
    Test that verifies that the object constructor can be successfully used.
    """
    # Arrange

    # Act
    system = System(cobbler_api)

    # Arrange
    assert isinstance(system, System)


def test_make_clone(cobbler_api: CobblerAPI):
    """
    Test that verifies that cloning an object logically is working as expected.
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    result = system.make_clone()

    # Assert
    assert result != system


def test_to_dict(cobbler_api: CobblerAPI):
    """
    Test that verfies that converting the System to a dict works as expected.
    """
    # Arrange
    titem = System(cobbler_api)

    # Act
    result = titem.to_dict()

    # Assert
    assert isinstance(result, dict)
    assert result.get("autoinstall") == enums.VALUE_INHERITED


def test_to_dict_resolved_profile(
    cobbler_api: CobblerAPI, create_distro: Callable[[], Distro]
):
    """
    Test that verfies that a system which is based on a profile can be converted to a dictionary successfully.
    """
    # Arrange
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}
    cobbler_api.add_distro(test_distro)
    titem = Profile(cobbler_api)
    titem.name = "to_dict_resolved_profile"
    titem.distro = test_distro.name
    titem.kernel_options = {"my_value": 5}
    cobbler_api.add_profile(titem)
    system = System(cobbler_api)
    system.name = "to_dict_resolved_system_profile"
    system.profile = titem.name
    system.kernel_options = {"my_value": 10}
    cobbler_api.add_system(system)

    # Act
    result = system.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("kernel_options") == {"test": True, "my_value": 10}
    assert result.get("autoinstall") == "default.ks"
    assert enums.VALUE_INHERITED not in str(result)


def test_to_dict_resolved_image(
    cobbler_api: CobblerAPI, create_image: Callable[[], Image]
):
    """
    Test that verfies that a system which is based on an image can be converted to a dictionary successfully.
    """
    # Arrange
    test_image = create_image()
    test_image.kernel_options = {"test": True}
    cobbler_api.add_image(test_image)
    system = System(cobbler_api)
    system.name = "to_dict_resolved_system_image"
    system.image = test_image.name
    system.kernel_options = {"my_value": 5}
    cobbler_api.add_system(system)

    # Act
    result = system.to_dict(resolved=True)
    print(str(result))

    # Assert
    assert isinstance(result, dict)
    assert result.get("kernel_options") == {"test": True, "my_value": 5}
    assert enums.VALUE_INHERITED not in str(result)


# Properties Tests


def test_ipv6_autoconfiguration(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "ipv6_autoconfiguration".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.ipv6_autoconfiguration = False

    # Assert
    assert not system.ipv6_autoconfiguration


def test_repos_enabled(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "repos_enabled".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.repos_enabled = False

    # Assert
    assert not system.repos_enabled


def test_autoinstall(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "autoinstall".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.autoinstall = ""

    # Assert
    assert system.autoinstall == ""


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_output",
    [
        ("", does_not_raise(), []),
        ([], does_not_raise(), []),
        ("<<inherit>>", does_not_raise(), ["grub", "pxe", "ipxe"]),
        ([""], pytest.raises(CX), []),
        (["ipxe"], does_not_raise(), ["ipxe"]),
    ],
)
def test_boot_loaders(
    request: "pytest.FixtureRequest",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    input_value: Any,
    expected_exception: Any,
    expected_output: List[str],
):
    """
    Test that verfies the functionality of the property "boot_loaders".
    """
    # Arrange
    tmp_distro = create_distro()
    tmp_profile = create_profile(tmp_distro.name)
    system = System(cobbler_api)
    system.name = (
        request.node.originalname  # type: ignore
        if request.node.originalname  # type: ignore
        else request.node.name
    )
    system.profile = tmp_profile.name

    # Act
    with expected_exception:
        system.boot_loaders = input_value

        # Assert
        assert system.boot_loaders == expected_output


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, does_not_raise()),
        (0.0, pytest.raises(TypeError)),
        ("", does_not_raise()),
        (
            "<<inherit>>",
            does_not_raise(),
        ),  # FIXME: Test passes but it actually does not do the right thing
        ("Test", does_not_raise()),
        ([], pytest.raises(TypeError)),
        ({}, pytest.raises(TypeError)),
        (None, pytest.raises(TypeError)),
        (False, does_not_raise()),
        (True, does_not_raise()),
    ],
)
def test_enable_ipxe(cobbler_api: CobblerAPI, value: Any, expected: Any):
    """
    Test that verfies the functionality of the property "enable_ipxe".
    """
    # Arrange
    distro = System(cobbler_api)

    # Act
    with expected:
        distro.enable_ipxe = value

        # Assert
        assert isinstance(distro.enable_ipxe, bool)
        assert distro.enable_ipxe or not distro.enable_ipxe


def test_gateway(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "gateway".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.gateway = ""

    # Assert
    assert system.gateway == ""


def test_hostname(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "hostname".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.hostname = ""

    # Assert
    assert system.hostname == ""


def test_image(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "image".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.image = ""

    # Assert
    assert system.image == ""


def test_ipv6_default_device(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "ipv6_default_device".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.ipv6_default_device = ""

    # Assert
    assert system.ipv6_default_device == ""


def test_name_servers(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "name_servers".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.name_servers = []

    # Assert
    assert system.name_servers == []


def test_name_servers_search(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "name_servers_search".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.name_servers_search = ""

    # Assert
    assert system.name_servers_search == ""


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, does_not_raise()),
        (0.0, pytest.raises(TypeError)),
        ("", does_not_raise()),
        ("Test", does_not_raise()),
        ([], pytest.raises(TypeError)),
        ({}, pytest.raises(TypeError)),
        (None, pytest.raises(TypeError)),
        (False, does_not_raise()),
        (True, does_not_raise()),
    ],
)
def test_netboot_enabled(cobbler_api: CobblerAPI, value: Any, expected: Any):
    """
    Test that verfies the functionality of the property "netboot_enabled".
    """
    # Arrange
    distro = System(cobbler_api)

    # Act
    with expected:
        distro.netboot_enabled = value

        # Assert
        assert isinstance(distro.netboot_enabled, bool)
        assert distro.netboot_enabled or not distro.netboot_enabled


@pytest.mark.parametrize(
    "input_next_server,expected_exception,expected_result",
    [
        ("", does_not_raise(), ""),
        ("<<inherit>>", does_not_raise(), "192.168.1.1"),
        (False, pytest.raises(TypeError), ""),
    ],
)
def test_next_server_v4(
    cobbler_api: CobblerAPI,
    input_next_server: Any,
    expected_exception: Any,
    expected_result: str,
):
    """
    Test that verfies the functionality of the property "next_server_v4".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    with expected_exception:
        system.next_server_v4 = input_next_server

        # Assert
        assert system.next_server_v4 == expected_result


@pytest.mark.parametrize(
    "input_next_server,expected_exception,expected_result",
    [
        ("", does_not_raise(), ""),
        ("<<inherit>>", does_not_raise(), "::1"),
        (False, pytest.raises(TypeError), ""),
    ],
)
def test_next_server_v6(
    cobbler_api: CobblerAPI,
    input_next_server: Any,
    expected_exception: Any,
    expected_result: str,
):
    """
    Test that verfies the functionality of the property "next_server_v6".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    with expected_exception:
        system.next_server_v6 = input_next_server

        # Assert
        assert system.next_server_v6 == expected_result


def test_filename(
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str, str, str], System],
):
    """
    Test that verfies the functionality of the property "filename".
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    test_system: System = create_system(profile_name=test_profile.name)  # type: ignore

    # Act
    test_system.filename = "<<inherit>>"

    # Assert
    assert test_system.filename == ""


def test_power_address(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "power_address".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_address = ""

    # Assert
    assert system.power_address == ""


def test_power_id(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "power_id".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_id = ""

    # Assert
    assert system.power_id == ""


def test_power_pass(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "power_pass".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_pass = ""

    # Assert
    assert system.power_pass == ""


def test_power_type(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "power_type".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_type = "docker"

    # Assert
    assert system.power_type == "docker"


def test_power_user(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "power_user".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_user = ""

    # Assert
    assert system.power_user == ""


def test_power_options(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "power_options".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_options = ""

    # Assert
    assert system.power_options == ""


def test_power_identity_file(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "power_identity_file".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.power_identity_file = ""

    # Assert
    assert system.power_identity_file == ""


def test_profile(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "profile".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.profile = ""

    # Assert
    assert system.profile == ""


@pytest.mark.parametrize(
    "input_proxy,expected_exception,expected_result",
    [
        ("", does_not_raise(), ""),
        ("<<inherit>>", does_not_raise(), ""),
        (False, pytest.raises(TypeError), ""),
    ],
)
def test_proxy(
    cobbler_api: CobblerAPI,
    input_proxy: Any,
    expected_exception: Any,
    expected_result: str,
):
    """
    Test that verfies the functionality of the property "proxy".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    with expected_exception:
        system.proxy = input_proxy

        # Assert
        assert system.proxy == expected_result


@pytest.mark.parametrize(
    "input_redhat_management_key,expected_exception,expected_result",
    [
        ("", does_not_raise(), ""),
        ("<<inherit>>", does_not_raise(), ""),
        (False, pytest.raises(TypeError), ""),
    ],
)
def test_redhat_management_key(
    cobbler_api: CobblerAPI,
    input_redhat_management_key: Any,
    expected_exception: Any,
    expected_result: str,
):
    """
    Test that verfies the functionality of the property "redhat_management_key".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    with expected_exception:
        system.redhat_management_key = input_redhat_management_key

        # Assert
        assert system.redhat_management_key == expected_result


@pytest.mark.parametrize(
    "input_server,expected_exception,expected_result",
    [
        ("", does_not_raise(), "192.168.1.1"),
        ("<<inherit>>", does_not_raise(), "192.168.1.1"),
        ("1.1.1.1", does_not_raise(), "1.1.1.1"),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_server(
    cobbler_api: CobblerAPI,
    input_server: Any,
    expected_exception: Any,
    expected_result: Optional[str],
):
    """
    Test that verfies the functionality of the property "server".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    with expected_exception:
        system.server = input_server

        # Assert
        assert system.server == expected_result


def test_status(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "status".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.status = ""

    # Assert
    assert system.status == ""


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        (False, does_not_raise(), False),
        (True, does_not_raise(), True),
        ("True", does_not_raise(), True),
        ("1", does_not_raise(), True),
        ("", does_not_raise(), False),
        ("<<inherit>>", does_not_raise(), True),
    ],
)
def test_virt_auto_boot(
    cobbler_api: CobblerAPI, value: Any, expected_exception: Any, expected_result: bool
):
    """
    Test that verfies the functionality of the property "virt_auto_boot".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    with expected_exception:
        system.virt_auto_boot = value

        # Assert
        assert system.virt_auto_boot is expected_result


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("", does_not_raise(), 0),
        # FIXME: (False, pytest.raises(TypeError)), --> does not raise
        (-5, pytest.raises(ValueError), -5),
        (0, does_not_raise(), 0),
        (5, does_not_raise(), 5),
    ],
)
def test_virt_cpus(
    cobbler_api: CobblerAPI, value: Any, expected_exception: Any, expected_result: int
):
    """
    Test that verfies the functionality of the property "virt_cpus".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    with expected_exception:
        system.virt_cpus = value

        # Assert
        assert system.virt_cpus == expected_result


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("qcow2", does_not_raise(), enums.VirtDiskDrivers.QCOW2),
        ("<<inherit>>", does_not_raise(), enums.VirtDiskDrivers.RAW),
        (enums.VirtDiskDrivers.QCOW2, does_not_raise(), enums.VirtDiskDrivers.QCOW2),
        (False, pytest.raises(TypeError), None),
        ("", pytest.raises(ValueError), None),
    ],
)
def test_virt_disk_driver(
    cobbler_api: CobblerAPI,
    value: Any,
    expected_exception: Any,
    expected_result: Optional[enums.VirtDiskDrivers],
):
    """
    Test that verfies the functionality of the property "virt_disk_driver".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    with expected_exception:
        system.virt_disk_driver = value

        # Assert
        assert system.virt_disk_driver == expected_result


@pytest.mark.parametrize(
    "input_virt_file_size,expected_exception,expected_result",
    [
        (15.0, does_not_raise(), 15.0),
        (15, does_not_raise(), 15.0),
        ("<<inherit>>", does_not_raise(), 5.0),
    ],
)
def test_virt_file_size(
    cobbler_api: CobblerAPI,
    input_virt_file_size: Any,
    expected_exception: Any,
    expected_result: float,
):
    """
    Test that verfies the functionality of the property "virt_file_size".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    with expected_exception:
        system.virt_file_size = input_virt_file_size

        # Assert
        assert system.virt_file_size == expected_result


@pytest.mark.parametrize(
    "input_path,expected_exception,expected_result",
    [
        ("", does_not_raise(), ""),
        ("<<inherit>>", does_not_raise(), ""),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_virt_path(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    input_path: Any,
    expected_exception: Any,
    expected_result: Optional[str],
):
    """
    Test that verfies the functionality of the property "virt_path".
    """
    # Arrange
    tmp_distro = create_distro()
    tmp_profile = create_profile(tmp_distro.name)
    system = System(cobbler_api)
    system.profile = tmp_profile.name

    # Act
    with expected_exception:
        system.virt_path = input_path

        # Assert
        assert system.virt_path == expected_result


def test_virt_pxe_boot(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "virt_pxe_boot".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.virt_pxe_boot = False

    # Assert
    assert not system.virt_pxe_boot


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("", does_not_raise(), 0),
        ("<<inherit>>", does_not_raise(), 512),
        (0, does_not_raise(), 0),
        (0.0, pytest.raises(TypeError), 0),
    ],
)
def test_virt_ram(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    value: Any,
    expected_exception: Any,
    expected_result: int,
):
    """
    Test that verfies the functionality of the property "virt_ram".
    """
    # Arrange
    distro = create_distro()
    profile = create_profile(distro.name)
    system = System(cobbler_api)
    system.profile = profile.name

    # Act
    with expected_exception:
        system.virt_ram = value

        # Assert
        assert system.virt_ram == expected_result


@pytest.mark.parametrize(
    "value,expected_exception, expected_result",
    [
        ("<<inherit>>", does_not_raise(), enums.VirtType.XENPV),
        ("qemu", does_not_raise(), enums.VirtType.QEMU),
        (enums.VirtType.QEMU, does_not_raise(), enums.VirtType.QEMU),
        ("", pytest.raises(ValueError), None),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_virt_type(
    cobbler_api: CobblerAPI,
    value: Any,
    expected_exception: Any,
    expected_result: Optional[enums.VirtType],
):
    """
    Test that verfies the functionality of the property "virt_type".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    with expected_exception:
        system.virt_type = value

        # Assert
        assert system.virt_type == expected_result


def test_serial_device(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "serial_device".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.serial_device = 5

    # Assert
    assert system.serial_device == 5


@pytest.mark.parametrize(
    "value,expected_exception",
    [
        (enums.BaudRates.B110, does_not_raise()),
        (110, does_not_raise()),
        # FIXME: (False, pytest.raises(TypeError)) --> This does not raise a TypeError but instead a value Error.
    ],
)
def test_serial_baud_rate(cobbler_api: CobblerAPI, value: Any, expected_exception: Any):
    """
    Test that verfies the functionality of the property "serial_baud_rate".
    """
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


def test_from_dict_with_network_interface(cobbler_api: CobblerAPI):
    """
    Test that verifies that the ``to_dict`` method works with network interfaces.
    """
    # Arrange
    system = System(cobbler_api)
    system.interfaces = {"default": NetworkInterface(cobbler_api)}
    sys_dict = system.to_dict()

    # Act
    system.from_dict(sys_dict)

    # Assert
    assert "default" in system.interfaces


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("foobar_not_existing", pytest.raises(ValueError), None),
        ("", pytest.raises(ValueError), None),
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
    cobbler_api: CobblerAPI,
    value: Any,
    expected_exception: Any,
    expected_result: Optional[enums.NetworkInterfaceType],
):
    """
    Test that verifies that the ``NetworkInterface.interface_type`` works as expected.
    """
    # Arrange
    interface = NetworkInterface(cobbler_api)

    # Act
    with expected_exception:
        interface.interface_type = value

        # Assert
        assert interface.interface_type == expected_result


@pytest.mark.parametrize(
    "input_mac,input_ipv4,input_ipv6,expected_result",
    [
        ("AA:BB:CC:DD:EE:FF", "192.168.1.2", "::1", True),
        ("", "192.168.1.2", "", True),
        ("", "", "::1", True),
        ("AA:BB:CC:DD:EE:FF", "", "", True),
        ("", "", "", False),
    ],
)
def test_is_management_supported(
    cobbler_api: CobblerAPI,
    input_mac: str,
    input_ipv4: str,
    input_ipv6: str,
    expected_result: bool,
):
    """
    Test that verifies that the ``is_management_supported()`` works as expected.
    """
    # Arrange
    system = System(cobbler_api)
    system.interfaces = {"default": NetworkInterface(cobbler_api)}
    system.interfaces["default"].mac_address = input_mac
    system.interfaces["default"].ip_address = input_ipv4
    system.interfaces["default"].ipv6_address = input_ipv6

    # Act
    result = system.is_management_supported()

    # Assert
    assert result is expected_result


def test_display_name(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "display_name".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.display_name = ""

    # Assert
    assert system.display_name == ""


def test_profile_inherit(
    mocker: "MockerFixture",
    test_settings: Settings,
    create_distro: Callable[[], Distro],
):
    """
    Checking that inherited properties are correctly inherited from settings and
    that the <<inherit>> value can be set for them.
    """
    # Arrange
    distro = create_distro()
    api = distro.api
    mocker.patch.object(api, "settings", return_value=test_settings)
    distro.arch = enums.Archs.X86_64
    profile = Profile(api)
    profile.name = "test_profile_inherit"
    profile.distro = distro.name
    api.add_profile(profile)
    system = System(api)
    system.profile = profile.name

    # Act
    for key, key_value in system.__dict__.items():
        if key_value == enums.VALUE_INHERITED:
            new_key = key[1:].lower()
            new_value = getattr(system, new_key)
            settings_name = new_key
            parent_obj = None
            if hasattr(profile, settings_name):
                parent_obj = profile
            elif hasattr(distro, settings_name):
                parent_obj = distro
            else:
                if new_key == "owners":
                    settings_name = "default_ownership"
                elif new_key == "proxy":
                    settings_name = "proxy_url_int"

                if hasattr(test_settings, f"default_{settings_name}"):
                    settings_name = f"default_{settings_name}"
                if hasattr(test_settings, settings_name):
                    parent_obj = test_settings

            if parent_obj is not None:
                setting = getattr(parent_obj, settings_name)
                if new_key == "autoinstall":
                    new_value = "default.ks"
                elif new_key == "boot_loaders":
                    new_value = ["grub"]
                elif new_key == "next_server_v4":
                    new_value = "10.10.10.10"
                elif new_key == "next_server_v6":
                    new_value = "fd00::"
                elif isinstance(setting, str):
                    new_value = "test_inheritance"
                elif isinstance(setting, bool):
                    new_value = True
                elif isinstance(setting, int):
                    new_value = 1
                elif isinstance(setting, float):
                    new_value = 1.0
                elif isinstance(setting, dict):
                    new_value.update({"test_inheritance": "test_inheritance"})
                elif isinstance(setting, list):
                    new_value = ["test_inheritance"]
                setattr(parent_obj, settings_name, new_value)

            prev_value = getattr(system, new_key)
            setattr(system, new_key, enums.VALUE_INHERITED)

            # Assert
            assert prev_value == new_value
            assert prev_value == getattr(system, new_key)


def test_image_inherit(
    mocker: "MockerFixture", test_settings: Settings, create_image: Callable[[], Image]
):
    """
    Checking that inherited properties are correctly inherited from settings and
    that the <<inherit>> value can be set for them.
    """
    # Arrange
    image = create_image()
    api = image.api
    mocker.patch.object(api, "settings", return_value=test_settings)
    system = System(api)
    system.image = image.name

    # Act
    for key, key_value in system.__dict__.items():
        if key_value == enums.VALUE_INHERITED:
            new_key = key[1:].lower()
            new_value = getattr(system, new_key)
            settings_name = new_key
            parent_obj = None
            if hasattr(image, settings_name):
                parent_obj = image
            else:
                if new_key == "owners":
                    settings_name = "default_ownership"
                elif new_key == "proxy":
                    settings_name = "proxy_url_int"

                if hasattr(test_settings, f"default_{settings_name}"):
                    settings_name = f"default_{settings_name}"
                if hasattr(test_settings, settings_name):
                    parent_obj = test_settings

            if parent_obj is not None:
                setting = getattr(parent_obj, settings_name)
                if new_key == "autoinstall":
                    new_value = "default.ks"
                elif new_key == "boot_loaders":
                    new_value = ["grub"]
                elif new_key == "next_server_v4":
                    new_value = "10.10.10.10"
                elif new_key == "next_server_v6":
                    new_value = "fd00::"
                elif isinstance(setting, str):
                    new_value = "test_inheritance"
                elif isinstance(setting, bool):
                    new_value = True
                elif isinstance(setting, int):
                    new_value = 1
                elif isinstance(setting, float):
                    new_value = 1.0
                elif isinstance(setting, dict):
                    new_value.update({"test_inheritance": "test_inheritance"})
                elif isinstance(setting, list):
                    new_value = ["test_inheritance"]
                setattr(parent_obj, settings_name, new_value)

            prev_value = getattr(system, new_key)
            setattr(system, new_key, enums.VALUE_INHERITED)

            # Assert
            assert prev_value == new_value
            assert prev_value == getattr(system, new_key)
