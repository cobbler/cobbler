import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from tests.conftest import does_not_raise


def test_object_creation():
    # Arrange
    test_api = CobblerAPI()

    # Act
    profile = Profile(test_api)

    # Arrange
    assert isinstance(profile, Profile)


def test_make_clone():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    result = profile.make_clone()

    # Assert
    assert result != profile


def test_to_dict():
    # Arrange
    test_api = CobblerAPI()
    distro = Distro(test_api)
    distro.name = "testdistro"
    test_api.add_distro(distro, save=False)
    profile = Profile(test_api)
    profile.name = "testprofile"
    profile.distro = distro.name

    # Act
    result = profile.to_dict()

    # Assert
    assert len(result) == 44
    assert result["distro"] == "testdistro"


# Properties Tests


def test_parent():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.parent = ""

    # Assert
    assert profile.parent is None


def test_distro():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.distro = ""

    # Assert
    assert profile.distro is None


def test_name_servers():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.name_servers = ""

    # Assert
    assert profile.name_servers == ""


def test_name_servers_search():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.name_servers_search = ""

    # Assert
    assert profile.name_servers_search == ""


def test_proxy():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.proxy = ""

    # Assert
    assert profile.proxy == ""


@pytest.mark.parametrize("value,expected_exception", [
    (False, does_not_raise())
])
def test_enable_ipxe(value, expected_exception):
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    with expected_exception:
        profile.enable_ipxe = value

        # Assert
        assert profile.enable_ipxe is value


@pytest.mark.parametrize("value,expected_exception", [
    (True, does_not_raise()),
    (False, does_not_raise()),
    ("", pytest.raises(TypeError)),
    (0, pytest.raises(TypeError))
])
def test_enable_menu(value, expected_exception):
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    with expected_exception:
        profile.enable_menu = value

        # Assert
        assert profile.enable_menu == value


def test_dhcp_tag():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.dhcp_tag = ""

    # Assert
    assert profile.dhcp_tag == ""


def test_server():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.server = ""

    # Assert
    assert profile.server == "<<inherit>>"


def test_next_server_v4():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.next_server_v4 = ""

    # Assert
    assert profile.next_server_v4 == ""


def test_next_server_v6():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.next_server_v6 = ""

    # Assert
    assert profile.next_server_v6 == ""


def test_filename():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.filename = ""

    # Assert
    assert profile.filename == "<<inherit>>"


def test_autoinstall():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.autoinstall = ""

    # Assert
    assert profile.autoinstall == ""


@pytest.mark.parametrize("value,expected_exception", [
    ("", pytest.raises(TypeError)),
    (False, does_not_raise()),
    (True, does_not_raise())
])
def test_virt_auto_boot(value, expected_exception):
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    with expected_exception:
        profile.virt_auto_boot = value

        # Assert
        assert profile.virt_auto_boot == value


@pytest.mark.parametrize("value,expected_exception", [
    ("", pytest.raises(TypeError)),
    # FIXME: (False, pytest.raises(TypeError)), --> does not raise
    (-5, pytest.raises(ValueError)),
    (0, does_not_raise()),
    (5, does_not_raise())
])
def test_virt_cpus(value, expected_exception):
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    with expected_exception:
        profile.virt_cpus = value

        # Assert
        assert profile.virt_cpus == value


@pytest.mark.parametrize("value,expected_exception", [
    ("5", does_not_raise()),
    # FIXME: (False, pytest.raises(TypeError)), --> does not raise
    (-5, pytest.raises(ValueError)),
    (0, does_not_raise()),
    (5, does_not_raise())
])
def test_virt_file_size(value, expected_exception):
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    with expected_exception:
        profile.virt_file_size = value

        # Assert
        assert profile.virt_file_size == int(value)


@pytest.mark.parametrize("value,expected_exception", [
    ("qcow2", does_not_raise()),
    (enums.VirtDiskDrivers.QCOW2, does_not_raise()),
    (False, pytest.raises(TypeError)),
    ("", pytest.raises(ValueError))
])
def test_virt_disk_driver(value, expected_exception):
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    with expected_exception:
        profile.virt_disk_driver = value

        # Assert
        if isinstance(value, str):
            assert profile.virt_disk_driver.value == value
        else:
            assert profile.virt_disk_driver == value


@pytest.mark.parametrize("value,expected_exception", [
    ("", pytest.raises(ValueError)),
    (0, does_not_raise()),
    (0.0, does_not_raise())
])
def test_virt_ram(value, expected_exception):
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    with expected_exception:
        profile.virt_ram = value

        # Assert
        assert profile.virt_ram == int(value)


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
    profile = Profile(test_api)

    # Act
    with expected_exception:
        profile.virt_type = value

        # Assert
        if isinstance(value, str):
            assert profile.virt_type.value == value
        else:
            assert profile.virt_type == value


def test_virt_bridge():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.virt_bridge = ""

    # Assert
    # This is the default from the settings
    assert profile.virt_bridge == "xenbr0"


def test_virt_path():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.virt_path = ""

    # Assert
    assert profile.virt_path == ""


def test_repos():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.repos = ""

    # Assert
    assert profile.repos == []


def test_redhat_management_key():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.redhat_management_key = ""

    # Assert
    assert profile.redhat_management_key == ""


def test_boot_loaders():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.boot_loaders = ""

    # Assert
    assert profile.boot_loaders == []


def test_menu():
    # Arrange
    test_api = CobblerAPI()
    profile = Profile(test_api)

    # Act
    profile.menu = ""

    # Assert
    assert profile.menu == ""
