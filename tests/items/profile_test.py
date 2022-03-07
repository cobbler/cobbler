import pytest

from cobbler import enums
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from tests.conftest import does_not_raise


def test_object_creation(cobbler_api):
    # Arrange

    # Act
    profile = Profile(cobbler_api)

    # Arrange
    assert isinstance(profile, Profile)


def test_make_clone(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    result = profile.make_clone()

    # Assert
    assert result != profile


@pytest.fixture(autouse=True)
def cleanup_to_dict(cobbler_api):
    yield
    cobbler_api.remove_distro("test_to_dict_distro")


def test_to_dict(cobbler_api, cleanup_to_dict):
    # Arrange
    distro = Distro(cobbler_api)
    distro.name = "test_to_dict_distro"
    cobbler_api.add_distro(distro, save=False)
    profile = Profile(cobbler_api)
    profile.name = "testprofile"
    profile.distro = distro.name

    # Act
    result = profile.to_dict()

    # Assert
    assert len(result) == 44
    assert result["distro"] == "test_to_dict_distro"


# Properties Tests


def test_parent(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.parent = ""

    # Assert
    assert profile.parent is None


def test_distro(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.distro = ""

    # Assert
    assert profile.distro is None


def test_name_servers(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.name_servers = []

    # Assert
    assert profile.name_servers == []


def test_name_servers_search(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.name_servers_search = ""

    # Assert
    assert profile.name_servers_search == ""


def test_proxy(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.proxy = ""

    # Assert
    assert profile.proxy == ""


@pytest.mark.parametrize("value,expected_exception", [
    (False, does_not_raise())
])
def test_enable_ipxe(cobbler_api, value, expected_exception):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.enable_ipxe = value

        # Assert
        assert profile.enable_ipxe is value


@pytest.mark.parametrize("value,expected_exception", [
    (True, does_not_raise()),
    (False, does_not_raise()),
    ("", does_not_raise()),
    (0, does_not_raise())
])
def test_enable_menu(cobbler_api, value, expected_exception):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.enable_menu = value

        # Assert
        assert isinstance(profile.enable_menu, bool)
        assert profile.enable_menu or not profile.enable_menu


def test_dhcp_tag(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.dhcp_tag = ""

    # Assert
    assert profile.dhcp_tag == ""


def test_server(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.server = ""

    # Assert
    assert profile.server == "<<inherit>>"


def test_next_server_v4(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.next_server_v4 = ""

    # Assert
    assert profile.next_server_v4 == ""


def test_next_server_v6(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.next_server_v6 = ""

    # Assert
    assert profile.next_server_v6 == ""


def test_filename(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.filename = "<<inherit>>"

    # Assert
    assert profile.filename == "<<inherit>>"


def test_autoinstall(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.autoinstall = ""

    # Assert
    assert profile.autoinstall == ""


@pytest.mark.parametrize("value,expected_exception", [
    ("", does_not_raise()),
    (False, does_not_raise()),
    (True, does_not_raise())
])
def test_virt_auto_boot(cobbler_api, value, expected_exception):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_auto_boot = value

        # Assert
        assert isinstance(profile.virt_auto_boot, bool)
        assert profile.virt_auto_boot or not profile.virt_auto_boot


@pytest.mark.parametrize("value,expected_exception, expected_result", [
    ("", does_not_raise(), 0),
    # FIXME: (False, pytest.raises(TypeError)), --> does not raise
    (-5, pytest.raises(ValueError), -5),
    (0, does_not_raise(), 0),
    (5, does_not_raise(), 5)
])
def test_virt_cpus(cobbler_api, value, expected_exception, expected_result):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_cpus = value

        # Assert
        assert profile.virt_cpus == expected_result


@pytest.mark.parametrize("value,expected_exception", [
    ("5", does_not_raise()),
    # FIXME: (False, pytest.raises(TypeError)), --> does not raise
    (-5, pytest.raises(ValueError)),
    (0, does_not_raise()),
    (5, does_not_raise())
])
def test_virt_file_size(cobbler_api, value, expected_exception):
    # Arrange
    profile = Profile(cobbler_api)

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
def test_virt_disk_driver(cobbler_api, value, expected_exception):
    # Arrange
    profile = Profile(cobbler_api)

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
    (0.0, pytest.raises(TypeError))
])
def test_virt_ram(cobbler_api, value, expected_exception):
    # Arrange
    profile = Profile(cobbler_api)

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
def test_virt_type(cobbler_api, value, expected_exception):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_type = value

        # Assert
        if isinstance(value, str):
            assert profile.virt_type.value == value
        else:
            assert profile.virt_type == value


def test_virt_bridge(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.virt_bridge = ""

    # Assert
    # This is the default from the settings
    assert profile.virt_bridge == "xenbr0"


def test_virt_path(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.virt_path = ""

    # Assert
    assert profile.virt_path == ""


def test_repos(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.repos = ""

    # Assert
    assert profile.repos == []


def test_redhat_management_key(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.redhat_management_key = ""

    # Assert
    assert profile.redhat_management_key == ""


def test_boot_loaders(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.boot_loaders = ""

    # Assert
    assert profile.boot_loaders == []


def test_menu(cobbler_api):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.menu = ""

    # Assert
    assert profile.menu == ""
