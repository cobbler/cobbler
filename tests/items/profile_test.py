from typing import Callable, Dict, Any

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from tests.conftest import does_not_raise


@pytest.fixture()
def test_settings(mocker, cobbler_api: CobblerAPI):
    settings = mocker.MagicMock(
        name="profile_setting_mock", spec=cobbler_api.settings()
    )
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_object_creation(cobbler_api: CobblerAPI):
    # Arrange

    # Act
    profile = Profile(cobbler_api)

    # Arrange
    assert isinstance(profile, Profile)


def test_make_clone(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    result = profile.make_clone()

    # Assert
    assert result != profile


@pytest.fixture(autouse=True)
def cleanup_to_dict(cobbler_api: CobblerAPI):
    yield
    cobbler_api.remove_distro("test_to_dict_distro")


def test_to_dict(cobbler_api: CobblerAPI, cleanup_to_dict):
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
    assert len(result) == 43
    assert result["distro"] == "test_to_dict_distro"


# Properties Tests


def test_parent_empty(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.parent = ""

    # Assert
    assert profile.parent is None


def test_parent_profile(cobbler_api: CobblerAPI, create_distro, create_profile):
    # Arrange
    test_dist = create_distro()
    test_profile = create_profile(test_dist.name)
    profile = Profile(cobbler_api)

    # Act
    profile.parent = test_profile.name

    # Assert
    assert profile.parent is test_profile


def test_parent_other_object_type(cobbler_api: CobblerAPI, create_image):
    # Arrange
    test_image = create_image()
    profile = Profile(cobbler_api)

    # Act
    with pytest.raises(CX):
        profile.parent = test_image.name


def test_parent_invalid_type(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act & Assert
    with pytest.raises(TypeError):
        profile.parent = 0


def test_parent_self(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)
    profile.name = "testname"

    # Act & Assert
    with pytest.raises(CX):
        profile.parent = profile.name


def test_distro(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.distro = ""

    # Assert
    assert profile.distro is None


def test_name_servers(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.name_servers = []

    # Assert
    assert profile.name_servers == []


def test_name_servers_search(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.name_servers_search = ""

    # Assert
    assert profile.name_servers_search == ""


def test_proxy(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.proxy = ""

    # Assert
    assert profile.proxy == ""


@pytest.mark.parametrize("value,expected_exception", [(False, does_not_raise())])
def test_enable_ipxe(cobbler_api: CobblerAPI, value, expected_exception):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.enable_ipxe = value

        # Assert
        assert profile.enable_ipxe is value


@pytest.mark.parametrize(
    "value,expected_exception",
    [
        (True, does_not_raise()),
        (False, does_not_raise()),
        ("", does_not_raise()),
        (0, does_not_raise()),
    ],
)
def test_enable_menu(cobbler_api: CobblerAPI, value, expected_exception):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.enable_menu = value

        # Assert
        assert isinstance(profile.enable_menu, bool)
        assert profile.enable_menu or not profile.enable_menu


def test_dhcp_tag(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.dhcp_tag = ""

    # Assert
    assert profile.dhcp_tag == ""


@pytest.mark.parametrize(
    "input_server,expected_exception,expected_result",
    [
        ("", does_not_raise(), ""),
        ("<<inherit>>", does_not_raise(), "192.168.1.1"),
        (False, pytest.raises(TypeError), ""),
    ],
)
def test_server(cobbler_api: CobblerAPI, input_server, expected_exception, expected_result):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.server = input_server

        # Assert
        assert profile.server == expected_result


def test_next_server_v4(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.next_server_v4 = ""

    # Assert
    assert profile.next_server_v4 == ""


def test_next_server_v6(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.next_server_v6 = ""

    # Assert
    assert profile.next_server_v6 == ""


@pytest.mark.parametrize(
    "input_filename,expected_result,is_subitem,expected_exception",
    [
        ("", "", False, does_not_raise()),
        ("", "", True, does_not_raise()),
        ("<<inherit>>", "", False, does_not_raise()),
        ("<<inherit>>", "", True, does_not_raise()),
        ("test", "test", False, does_not_raise()),
        ("test", "test", True, does_not_raise()),
        (0, "", True, pytest.raises(TypeError)),
    ],
)
def test_filename(
    cobbler_api: CobblerAPI,
    create_distro,
    create_profile,
    input_filename,
    expected_result,
    is_subitem,
    expected_exception,
):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the filename property correctly.
    """
    # Arrange
    test_dist = create_distro()  # type: ignore
    profile = Profile(cobbler_api)
    profile.name = "filename_test_profile"
    if is_subitem:
        test_profile = create_profile(test_dist.name)  # type: ignore
        profile.parent = test_profile.name  # type: ignore
    profile.distro = test_dist.name  # type: ignore

    # Act
    with expected_exception:
        profile.filename = input_filename

        # Assert
        assert profile.filename == expected_result


@pytest.mark.parametrize(
    "input_filename,expected_result,is_subitem,expected_exception",
    [
        ("", "", False, does_not_raise()),
        ("", "", True, does_not_raise()),
        ("<<inherit>>", "", False, does_not_raise()),
        ("<<inherit>>", "", True, does_not_raise()),
        ("test", "test", False, does_not_raise()),
        ("test", "test", True, does_not_raise()),
        (0, "", True, pytest.raises(TypeError)),
    ],
)
def test_filename(
    cobbler_api: CobblerAPI,
    create_distro,
    create_profile,
    input_filename,
    expected_result,
    is_subitem,
    expected_exception,
):
    # Arrange
    test_dist = create_distro()
    profile = Profile(cobbler_api)
    profile.name = "filename_test_profile"
    if is_subitem:
        test_profile = create_profile(test_dist.name)
        profile.parent = test_profile.name
    profile.distro = test_dist.name

    # Act
    with expected_exception:
        profile.filename = input_filename

        # Assert
        assert profile.filename == expected_result


def test_autoinstall(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.autoinstall = ""

    # Assert
    assert profile.autoinstall == ""


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("", does_not_raise(), False),
        ("<<inherit>>", does_not_raise(), True),
        (False, does_not_raise(), False),
        (True, does_not_raise(), True),
    ],
)
def test_virt_auto_boot(cobbler_api: CobblerAPI, value, expected_exception, expected_result):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_auto_boot = value

        # Assert
        assert isinstance(profile.virt_auto_boot, bool)
        assert profile.virt_auto_boot is expected_result


@pytest.mark.parametrize(
    "value,expected_exception, expected_result",
    [
        ("", does_not_raise(), 0),
        # FIXME: (False, pytest.raises(TypeError)), --> does not raise
        (-5, pytest.raises(ValueError), -5),
        (0, does_not_raise(), 0),
        (5, does_not_raise(), 5),
    ],
)
def test_virt_cpus(cobbler_api: CobblerAPI, value, expected_exception, expected_result):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_cpus = value

        # Assert
        assert profile.virt_cpus == expected_result


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("5", does_not_raise(), 5.0),
        ("<<inherit>>", does_not_raise(), 5.0),
        # FIXME: (False, pytest.raises(TypeError)), --> does not raise
        (-5, pytest.raises(ValueError), 0),
        (0, does_not_raise(), 0.0),
        (5, does_not_raise(), 5.0),
    ],
)
def test_virt_file_size(cobbler_api: CobblerAPI, value, expected_exception, expected_result):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_file_size = value

        # Assert
        assert profile.virt_file_size == expected_result


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
def test_virt_disk_driver(cobbler_api: CobblerAPI, value, expected_exception, expected_result):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_disk_driver = value

        # Assert
        assert profile.virt_disk_driver == expected_result


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("", does_not_raise(), 0),
        ("<<inherit>>", does_not_raise(), 512),
        (0, does_not_raise(), 0),
        (0.0, pytest.raises(TypeError), 0),
    ],
)
def test_virt_ram(cobbler_api: CobblerAPI, value, expected_exception, expected_result):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_ram = value

        # Assert
        assert profile.virt_ram == expected_result


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("<<inherit>>", does_not_raise(), enums.VirtType.XENPV),
        ("qemu", does_not_raise(), enums.VirtType.QEMU),
        (enums.VirtType.QEMU, does_not_raise(), enums.VirtType.QEMU),
        ("", pytest.raises(ValueError), None),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_virt_type(cobbler_api: CobblerAPI, value, expected_exception, expected_result):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_type = value

        # Assert
        assert profile.virt_type == expected_result


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("<<inherit>>", does_not_raise(), "xenbr0"),
        ("random-bridge", does_not_raise(), "random-bridge"),
        ("", does_not_raise(), "xenbr0"),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_virt_bridge(cobbler_api: CobblerAPI, value, expected_exception, expected_result):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.virt_bridge = ""

    # Assert
    # This is the default from the settings
    assert profile.virt_bridge == "xenbr0"


def test_virt_path(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.virt_path = ""

    # Assert
    assert profile.virt_path == ""


def test_repos(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.repos = ""

    # Assert
    assert profile.repos == []


def test_redhat_management_key(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.redhat_management_key = ""

    # Assert
    assert profile.redhat_management_key == ""


def test_boot_loaders(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.boot_loaders = ""

    # Assert
    assert profile.boot_loaders == []


def test_menu(cobbler_api: CobblerAPI):
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.menu = ""

    # Assert
    assert profile.menu == ""


@pytest.mark.parametrize(
    "data_keys, check_key, check_value, expect_match",
    [
        ({"uid": "test-uid"}, "uid", "test-uid", True),
        ({"menu": "testmenu0"}, "menu", "testmenu0", True),
        ({"uid": "test", "name": "test-name"}, "uid", "test", True),
        ({"uid": "test"}, "arch", "x86_64", True),
        ({"uid": "test"}, "arch", "aarch64", False),
        ({"depth": "1"}, "name", "test", False),
        ({"uid": "test", "name": "test-name"}, "menu", "testmenu0", False),
    ],
)
def test_find_match_single_key(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    data_keys: Dict[str, Any],
    check_key: str,
    check_value: Any,
    expect_match: bool,
):
    """
    Assert that a single given key and value match the object or not.
    """
    # Arrange
    test_distro_obj = create_distro()
    test_distro_obj.arch = enums.Archs.X86_64
    profile = Profile(cobbler_api)
    profile.distro = test_distro_obj.name

    # Act
    result = profile.find_match_single_key(data_keys, check_key, check_value)

    # Assert
    assert expect_match == result


def test_distro_inherit(mocker, test_settings, create_distro: Callable[[], Distro]):
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
    profile.distro = distro.name

    # Act
    for key, key_value in profile.__dict__.items():
        if key_value == enums.VALUE_INHERITED:
            new_key = key[1:].lower()
            new_value = getattr(profile, new_key)
            settings_name = new_key
            parent_obj = None
            if hasattr(distro, settings_name):
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
                if isinstance(setting, str):
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
                    if new_key == "boot_loaders":
                        new_value = ["grub"]
                    else:
                        new_value = ["test_inheritance"]
                setattr(parent_obj, settings_name, new_value)

            prev_value = getattr(profile, new_key)
            setattr(profile, new_key, enums.VALUE_INHERITED)

            # Assert
            assert prev_value == new_value
            assert prev_value == getattr(profile, new_key)
