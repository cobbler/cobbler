"""
Test module to validate the functionallity of the Cobbler Profile item.
"""

from typing import Any, Callable, Dict, List

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.items.distro import Distro
from cobbler.items.image import Image
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
    """
    Assert that the Profile object can be successfully created.
    """
    # Arrange

    # Act
    profile = Profile(cobbler_api)

    # Arrange
    assert isinstance(profile, Profile)


def test_make_clone(cobbler_api: CobblerAPI):
    """
    Assert that a profile can be cloned and NOT have the same identity.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    result = profile.make_clone()

    # Assert
    assert result != profile


def test_to_dict(
    create_distro: Callable[[str], Distro],
    create_profile: Callable[[str, str, str], Profile],
):
    """
    Assert that the Profile can be successfully converted to a dictionary.
    """
    # Arrange
    distro: Distro = create_distro()  # type: ignore
    profile: Profile = create_profile(distro_name=distro.name)  # type: ignore

    # Act
    result = profile.to_dict()

    # Assert
    assert len(result) == 42
    assert result["distro"] == distro.name
    assert result.get("boot_loaders") == enums.VALUE_INHERITED


def test_to_dict_resolved(
    cobbler_api: CobblerAPI, create_distro: Callable[[str], Distro]
):
    """
    Assert that the Profile can be successfully converted to a dictionary with resolved values.
    """
    # Arrange
    test_distro_obj = create_distro()  # type: ignore
    test_distro_obj.kernel_options = {"test": True}
    cobbler_api.add_distro(test_distro_obj)  # type: ignore
    titem = Profile(cobbler_api)
    titem.name = "to_dict_resolved_profile"
    titem.distro = test_distro_obj.name  # type: ignore
    titem.kernel_options = {"my_value": 5}
    cobbler_api.add_profile(titem)

    # Act
    result = titem.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("kernel_options") == {"test": True, "my_value": 5}
    assert result.get("boot_loaders") == ["grub", "pxe", "ipxe"]
    assert enums.VALUE_INHERITED not in str(result)


# Properties Tests


def test_parent_empty(cobbler_api: CobblerAPI):
    """
    Assert that if a parent is removed that the getter returns None.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.parent = ""

    # Assert
    assert profile.parent is None


def test_parent_profile(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], Distro],
    create_profile: Callable[[str, str, str], Profile],
):
    """
    Assert that if the parent is set via a parent profile name the correct object is returned.
    """
    # Arrange
    test_dist = create_distro()  # type: ignore
    test_profile = create_profile(test_dist.name)  # type: ignore
    profile = Profile(cobbler_api)

    # Act
    profile.parent = test_profile.name  # type: ignore

    # Assert
    assert profile.parent is test_profile


def test_parent_other_object_type(
    cobbler_api: CobblerAPI, create_image: Callable[[str], Image]
):
    """
    Assert that if an invalid item type is set as a parent, the setter is raising a CobblerException.
    """
    # Arrange
    test_image = create_image()  # type: ignore
    profile = Profile(cobbler_api)

    # Act
    with pytest.raises(CX):
        profile.parent = test_image.name  # type: ignore


def test_parent_invalid_type(cobbler_api: CobblerAPI):
    """
    Asert that if the parent is set with a completly invalid type, the setter raises a TypeError.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act & Assert
    with pytest.raises(TypeError):
        profile.parent = 0  # type: ignore


def test_parent_self(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Profile can not set itself as a parent.
    """
    # Arrange
    profile = Profile(cobbler_api)
    profile.name = "testname"

    # Act & Assert
    with pytest.raises(CX):
        profile.parent = profile.name


def test_distro(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the distro property correctly.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.distro = ""

    # Assert
    assert profile.distro is None


def test_name_servers(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the name_servers property correctly.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.name_servers = []

    # Assert
    assert profile.name_servers == []


def test_name_servers_search(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the name_servers_search property correctly.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.name_servers_search = ""  # type: ignore

    # Assert
    assert profile.name_servers_search == ""


def test_proxy(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the proxy property correctly.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.proxy = ""

    # Assert
    assert profile.proxy == ""


@pytest.mark.parametrize("value,expected_exception", [(False, does_not_raise())])
def test_enable_ipxe(cobbler_api: CobblerAPI, value: Any, expected_exception: Any):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the enable_ipxe property correctly.
    """
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
def test_enable_menu(cobbler_api: CobblerAPI, value: Any, expected_exception: Any):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the enable_menu property correctly.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.enable_menu = value

        # Assert
        assert isinstance(profile.enable_menu, bool)
        assert profile.enable_menu or not profile.enable_menu


def test_dhcp_tag(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the dhcp_tag property correctly.
    """
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
def test_server(
    cobbler_api: CobblerAPI,
    input_server: Any,
    expected_exception: Any,
    expected_result: str,
):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the server property correctly.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.server = input_server

        # Assert
        assert profile.server == expected_result


def test_next_server_v4(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the next_server_v4 property correctly.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.next_server_v4 = ""

    # Assert
    assert profile.next_server_v4 == ""


def test_next_server_v6(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the next_server_v6 property correctly.
    """
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
    create_distro: Callable[[str], Distro],
    create_profile: Callable[[str, str, str], Profile],
    input_filename: Any,
    expected_result: str,
    is_subitem: bool,
    expected_exception: Any,
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


def test_autoinstall(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the autoinstall property correctly.
    """
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
def test_virt_auto_boot(
    cobbler_api: CobblerAPI, value: Any, expected_exception: Any, expected_result: bool
):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the virt_auto_boot property correctly.
    """
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
def test_virt_cpus(
    cobbler_api: CobblerAPI, value: Any, expected_exception: Any, expected_result: int
):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the virt_cpus property correctly.
    """
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
def test_virt_file_size(
    cobbler_api: CobblerAPI, value: Any, expected_exception: Any, expected_result: Any
):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the virt_file_size property correctly.
    """
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
def test_virt_disk_driver(
    cobbler_api: CobblerAPI, value: Any, expected_exception: Any, expected_result: Any
):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the virt_disk_driver property correctly.
    """
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
def test_virt_ram(
    cobbler_api: CobblerAPI, value: Any, expected_exception: Any, expected_result: Any
):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the virt_ram property correctly.
    """
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
def test_virt_type(
    cobbler_api: CobblerAPI,
    value: Any,
    expected_exception: Any,
    expected_result: Any,
):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the virt_type property correctly.
    """
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
def test_virt_bridge(
    cobbler_api: CobblerAPI,
    value: Any,
    expected_exception: Any,
    expected_result: Any,
):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the virt_bridge property correctly.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    with expected_exception:
        profile.virt_bridge = value

        # Assert
        # This is the default from the settings
        assert profile.virt_bridge == expected_result


def test_virt_path(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the virt_path property correctly.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.virt_path = ""

    # Assert
    assert profile.virt_path == ""


def test_repos(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the repos property correctly.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.repos = ""

    # Assert
    assert profile.repos == []


def test_redhat_management_key(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Profile can use the Getter and Setter of the redhat_management_key property correctly.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.redhat_management_key = ""

    # Assert
    assert profile.redhat_management_key == ""


@pytest.mark.parametrize(
    "input_boot_loaders,expected_result,expected_exception",
    [
        ("", [], does_not_raise()),
        ("grub", ["grub"], does_not_raise()),
        ("grub ipxe", ["grub", "ipxe"], does_not_raise()),
        ("<<inherit>>", ["grub", "pxe", "ipxe"], does_not_raise()),
        ([], [], does_not_raise()),
    ],
)
def test_boot_loaders(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], Distro],
    input_boot_loaders: Any,
    expected_result: List[str],
    expected_exception: Any,
):
    """
    Assert that a Cobbler Profile can resolve the boot loaders it has available successfully.
    """
    # Arrange
    distro: Distro = create_distro()  # type: ignore[reportGeneralTypeIssues]
    profile = Profile(cobbler_api)
    profile.distro = distro.name

    # Act
    with expected_exception:
        profile.boot_loaders = input_boot_loaders

        # Assert
        assert profile.boot_loaders == expected_result


def test_menu(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Profile can be attached to a Cobbler Menu successfully.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.menu = ""

    # Assert
    assert profile.menu == ""


def test_display_name(cobbler_api: CobblerAPI):
    """
    Assert that the display name of a Cobbler Profile can be set successfully.
    """
    # Arrange
    profile = Profile(cobbler_api)

    # Act
    profile.display_name = ""

    # Assert
    assert profile.display_name == ""


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
