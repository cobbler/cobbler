"""
Test module that asserts that Cobbler System functionality is working as expected.
"""

from typing import TYPE_CHECKING, Any, Callable, List, Optional

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.profile import Profile
from cobbler.items.system import System
from cobbler.settings import Settings

from tests.conftest import does_not_raise

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="test_settings")
def fixture_test_settings(mocker: "MockerFixture", cobbler_api: CobblerAPI) -> Settings:
    """
    Fixture to reset the settings for system related unit-tests.
    """
    settings = mocker.MagicMock(
        name="profile_setting_mock",
        spec=Settings,
        autospec=True,
    )
    orig = cobbler_api.settings()
    settings.to_dict = orig.to_dict
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
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test that verfies that a system which is based on a profile can be converted to a dictionary successfully.
    """
    # Arrange
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}
    cobbler_api.add_distro(test_distro)
    titem = create_profile(test_distro.uid)
    titem.kernel_options = {"my_value": 5}
    cobbler_api.add_profile(titem)
    system = System(cobbler_api)
    system.name = "to_dict_resolved_system_profile"
    system.profile = titem.uid
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
    test_image_obj = create_image()
    test_image_obj.kernel_options = {"test": True}
    cobbler_api.add_image(test_image_obj)
    system = System(cobbler_api)
    system.name = "to_dict_resolved_system_image"
    system.image = test_image_obj.uid
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
        (
            "<<inherit>>",
            does_not_raise(),
            [enums.BootLoader.GRUB, enums.BootLoader.PXE, enums.BootLoader.IPXE],
        ),
        ([""], pytest.raises(ValueError), []),
        (["ipxe"], does_not_raise(), [enums.BootLoader.IPXE]),
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
    tmp_profile = create_profile(tmp_distro.uid)
    system = System(cobbler_api)
    system.name = (
        request.node.originalname  # type: ignore
        if request.node.originalname  # type: ignore
        else request.node.name  # type: ignore
    )
    system.profile = tmp_profile.uid

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
    system.dns.name_servers = []

    # Assert
    assert system.dns.name_servers == []


def test_name_servers_direct_inheritance(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test that verifies the functionality of the inherited property "name_servers".
    """
    # Arrange
    test_distro = create_distro()
    test_profile_obj = create_profile(test_distro.uid)
    test_system = System(cobbler_api, profile=test_profile_obj.uid)
    test_profile_obj.dns.name_servers = ["8.8.4.4"]

    # Act
    test_system.dns.name_servers = ["8.8.8.8"]

    # Assert
    assert set(test_system.dns.name_servers) == {"8.8.4.4", "8.8.8.8"}


def test_name_servers_indirect_inheritance(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test that verifies the functionality of the inherited property "name_servers".
    """
    # Arrange
    test_distro = create_distro()
    test_profile_obj_lvl0 = create_profile(test_distro.uid)
    test_profile_obj_lvl1 = create_profile(  # type: ignore
        profile_uid=test_profile_obj_lvl0.uid, name="subprofile"  # type: ignore
    )
    test_system = System(cobbler_api, profile=test_profile_obj_lvl1.uid)  # type: ignore
    test_profile_obj_lvl0.dns.name_servers = ["8.8.4.4"]  # type: ignore

    # Act
    test_system.dns.name_servers = ["8.8.8.8"]

    # Assert
    assert set(test_system.dns.name_servers) == {"8.8.4.4", "8.8.8.8"}


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
        system.tftp.next_server_v4 = input_next_server

        # Assert
        assert system.tftp.next_server_v4 == expected_result


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
        system.tftp.next_server_v6 = input_next_server

        # Assert
        assert system.tftp.next_server_v6 == expected_result


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
    test_profile_obj = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile_obj.uid)  # type: ignore

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
    system.power.address = ""

    # Assert
    assert system.power.address == ""


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
    system.power_type = "redfish"

    # Assert
    assert system.power_type == "redfish"


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
        system.virt.auto_boot = value

        # Assert
        assert system.virt.auto_boot is expected_result


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
        system.virt.cpus = value

        # Assert
        assert system.virt.cpus == expected_result


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
        system.virt.disk_driver = value

        # Assert
        assert system.virt.disk_driver == expected_result


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
        system.virt.file_size = input_virt_file_size

        # Assert
        assert system.virt.file_size == expected_result


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
    tmp_profile = create_profile(tmp_distro.uid)
    system = System(cobbler_api)
    system.profile = tmp_profile.uid

    # Act
    with expected_exception:
        system.virt.path = input_path

        # Assert
        assert system.virt.path == expected_result


def test_virt_pxe_boot(cobbler_api: CobblerAPI):
    """
    Test that verfies the functionality of the property "virt_pxe_boot".
    """
    # Arrange
    system = System(cobbler_api)

    # Act
    system.virt.pxe_boot = False

    # Assert
    assert not system.virt.pxe_boot


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
    profile = create_profile(distro.uid)
    system = System(cobbler_api)
    system.profile = profile.uid

    # Act
    with expected_exception:
        system.virt.ram = value

        # Assert
        assert system.virt.ram == expected_result


@pytest.mark.parametrize(
    "value,expected_exception, expected_result",
    [
        ("<<inherit>>", does_not_raise(), enums.VirtType.KVM),
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
        system.virt.type = value

        # Assert
        assert system.virt.type == expected_result


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
    test_network_interface = cobbler_api.new_network_interface(
        system_uid=system.uid,
        name="default",
    )
    cobbler_api.add_network_interface(test_network_interface)
    sys_dict = system.to_dict()

    # Act
    system.from_dict(sys_dict)

    # Assert
    assert "default" in system.interfaces


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
    test_network_interface = cobbler_api.new_network_interface(
        system_uid=system.uid,
        name="default",
        ipv4={"address": input_ipv4},
        ipv6={"address": input_ipv6},
        mac_address=input_mac,
    )
    cobbler_api.add_network_interface(test_network_interface)

    # Act
    result = system.is_management_supported()

    # Assert
    assert result is expected_result


def test_interfaces(cobbler_api: CobblerAPI):
    """
    Test that verifies the ``interfaces`` property works as expected.
    """
    # Arrange
    system = System(cobbler_api)
    test_network_interface = cobbler_api.new_network_interface(
        system_uid=system.uid,
        name="default",
    )
    cobbler_api.add_network_interface(test_network_interface)

    # Act & Assert
    assert "default" in system.interfaces


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
    profile = api.new_profile(name="test_profile_inherit", distro=distro.uid)
    api.add_profile(profile)
    system = api.new_system(profile=profile.uid)

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
                parent_obj = distro  # type: ignore
            else:
                if new_key == "owners":
                    settings_name = "default_ownership"
                elif new_key == "proxy":
                    settings_name = "proxy_url_int"

                if hasattr(test_settings, f"default_{settings_name}"):
                    settings_name = f"default_{settings_name}"
                if hasattr(test_settings, settings_name):
                    parent_obj = test_settings  # type: ignore

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
    system.image = image.uid

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
                    parent_obj = test_settings  # type: ignore

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
