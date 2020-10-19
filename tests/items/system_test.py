import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.system import System
from tests.conftest import does_not_raise


def test_object_creation():
    # Arrange
    test_api = CobblerAPI()

    # Act
    system = System(test_api)

    # Arrange
    assert isinstance(system, System)


def test_make_clone():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    result = system.make_clone()

    # Assert
    assert result != system


# Properties Tests


def test_ipv6_autoconfiguration():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.ipv6_autoconfiguration = False

    # Assert
    assert not system.ipv6_autoconfiguration


def test_repos_enabled():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.repos_enabled = False

    # Assert
    assert not system.repos_enabled


def test_autoinstall():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.autoinstall = ""

    # Assert
    assert system.autoinstall == ""


def test_boot_loaders():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.boot_loaders = []

    # Assert
    assert system.boot_loaders == []


@pytest.mark.parametrize("value,expected", [
    (0, pytest.raises(TypeError)),
    (0.0, pytest.raises(TypeError)),
    ("", pytest.raises(TypeError)),
    ("Test", pytest.raises(TypeError)),
    ([], pytest.raises(TypeError)),
    ({}, pytest.raises(TypeError)),
    (None, pytest.raises(TypeError)),
    (False, does_not_raise()),
    (True, does_not_raise())
])
def test_enable_ipxe(value, expected):
    # Arrange
    test_api = CobblerAPI()
    distro = System(test_api)

    # Act
    with expected:
        distro.enable_ipxe = value

        # Assert
        assert distro.enable_ipxe == value


def test_gateway():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.gateway = ""

    # Assert
    assert system.gateway == ""


def test_hostname():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.hostname = ""

    # Assert
    assert system.hostname == ""


def test_image():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.image = ""

    # Assert
    assert system.image == ""


def test_ipv6_default_device():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.ipv6_default_device = ""

    # Assert
    assert system.ipv6_default_device == ""


def test_name_servers():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.name_servers = []

    # Assert
    assert system.name_servers == []


def test_name_servers_search():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.name_servers_search = []

    # Assert
    assert system.name_servers_search == []


@pytest.mark.parametrize("value,expected", [
    (0, pytest.raises(TypeError)),
    (0.0, pytest.raises(TypeError)),
    ("", pytest.raises(TypeError)),
    ("Test", pytest.raises(TypeError)),
    ([], pytest.raises(TypeError)),
    ({}, pytest.raises(TypeError)),
    (None, pytest.raises(TypeError)),
    (False, does_not_raise()),
    (True, does_not_raise())
])
def test_netboot_enabled(value, expected):
    # Arrange
    test_api = CobblerAPI()
    distro = System(test_api)

    # Act
    with expected:
        distro.netboot_enabled = value

        # Assert
        assert distro.netboot_enabled == value


def test_next_server_v4():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.next_server_v4 = ""

    # Assert
    assert system.next_server_v4 == ""


def test_next_server_v6():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.next_server_v6 = ""

    # Assert
    assert system.next_server_v6 == ""


def test_filename():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.filename = ""

    # Assert
    assert system.filename == "<<inherit>>"


def test_power_address():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.power_address = ""

    # Assert
    assert system.power_address == ""


def test_power_id():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.power_id = ""

    # Assert
    assert system.power_id == ""


def test_power_pass():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.power_pass = ""

    # Assert
    assert system.power_pass == ""


def test_power_type():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.power_type = "docker"

    # Assert
    assert system.power_type == "docker"


def test_power_user():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.power_user = ""

    # Assert
    assert system.power_user == ""


def test_power_options():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.power_options = ""

    # Assert
    assert system.power_options == ""


def test_power_identity_file():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.power_identity_file = ""

    # Assert
    assert system.power_identity_file == ""


def test_profile():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.profile = ""

    # Assert
    assert system.profile == ""


def test_proxy():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.proxy = ""

    # Assert
    assert system.proxy == "<<inherit>>"


def test_redhat_management_key():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.redhat_management_key = ""

    # Assert
    assert system.redhat_management_key == ""


def test_server():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.server = ""

    # Assert
    assert system.server == "<<inherit>>"


def test_status():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.status = ""

    # Assert
    assert system.status == ""


def test_virt_auto_boot():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.virt_auto_boot = False

    # Assert
    assert not system.virt_auto_boot


def test_virt_cpus():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

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
def test_virt_disk_driver(value, expected_exception):
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    with expected_exception:
        system.virt_disk_driver = value

        # Assert
        if isinstance(value, str):
            assert system.virt_disk_driver.value == value
        else:
            assert system.virt_disk_driver == value


def test_virt_file_size():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.virt_file_size = 1.0

    # Assert
    assert system.virt_file_size == 1.0


def test_virt_path():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.virt_path = ""

    # Assert
    assert system.virt_path == "<<inherit>>"


def test_virt_pxe_boot():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.virt_pxe_boot = False

    # Assert
    assert not system.virt_pxe_boot


def test_virt_ram():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

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
def test_virt_type(value, expected_exception):
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    with expected_exception:
        system.virt_type = value

        # Assert
        if isinstance(value, str):
            assert system.virt_type.value == value
        else:
            assert system.virt_type == value


def test_serial_device():
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    system.serial_device = 5

    # Assert
    assert system.serial_device == 5


@pytest.mark.parametrize("value,expected_exception", [
    (enums.BaudRates.B110, does_not_raise()),
    (110, does_not_raise()),
    # FIXME: (False, pytest.raises(TypeError)) --> This does not raise a TypeError but instead a value Error.
])
def test_serial_baud_rate(value, expected_exception):
    # Arrange
    test_api = CobblerAPI()
    system = System(test_api)

    # Act
    with expected_exception:
        system.serial_baud_rate = value

        # Assert
        if isinstance(value, int):
            assert system.serial_baud_rate.value == value
        else:
            assert system.serial_baud_rate == value
