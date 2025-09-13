"""
Tests that validate the functionality of the module that is responsible for providing image related functionality.
"""

from typing import TYPE_CHECKING, Any, Callable

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.image import Image
from cobbler.settings import Settings
from cobbler.utils import signatures

from tests.conftest import does_not_raise

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="test_settings")
def fixture_test_settings(mocker: "MockerFixture", cobbler_api: CobblerAPI) -> Settings:
    """
    TODO
    """
    settings = mocker.MagicMock(name="image_setting_mock", spec=cobbler_api.settings())
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_object_creation(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange

    # Act
    image = Image(cobbler_api)

    # Arrange
    assert isinstance(image, Image)


def test_make_clone(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    result = image.make_clone()

    # Assert
    assert image != result


def test_arch(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.arch = "x86_64"  # type: ignore[method-assign]

    # Assert
    assert image.arch == enums.Archs.X86_64


def test_autoinstall(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.autoinstall = ""  # type: ignore[method-assign]

    # Assert
    assert image.autoinstall == ""


def test_file(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.file = "/tmp/test"  # type: ignore[method-assign]

    # Assert
    assert image.file == "/tmp/test"


def test_os_version(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    signatures.load_signatures("/var/lib/cobbler/distro_signatures.json")
    image = Image(cobbler_api)
    image.breed = "suse"  # type: ignore[method-assign]

    # Act
    image.os_version = "sles15generic"  # type: ignore[method-assign]

    # Assert
    assert image.os_version == "sles15generic"


def test_breed(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    signatures.load_signatures("/var/lib/cobbler/distro_signatures.json")
    image = Image(cobbler_api)

    # Act
    image.breed = "suse"  # type: ignore[method-assign]

    # Assert
    assert image.breed == "suse"


def test_image_type(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.image_type = enums.ImageTypes.DIRECT  # type: ignore[method-assign]

    # Assert
    assert image.image_type == enums.ImageTypes.DIRECT


def test_virt_cpus(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.virt_cpus = 5  # type: ignore[method-assign]

    # Assert
    assert image.virt_cpus == 5


def test_network_count(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.network_count = 2  # type: ignore[method-assign]

    # Assert
    assert image.network_count == 2


def test_virt_auto_boot(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.virt_auto_boot = False  # type: ignore[method-assign]

    # Assert
    assert not image.virt_auto_boot


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
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    with expected_exception:
        image.virt_file_size = input_virt_file_size  # type: ignore[method-assign]

        # Assert
        assert image.virt_file_size == expected_result


def test_virt_disk_driver(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.virt_disk_driver = enums.VirtDiskDrivers.RAW  # type: ignore[method-assign]

    # Assert
    assert image.virt_disk_driver == enums.VirtDiskDrivers.RAW


def test_virt_ram(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.virt_ram = 5  # type: ignore[method-assign]

    # Assert
    assert image.virt_ram == 5


def test_virt_type(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.virt_type = enums.VirtType.AUTO  # type: ignore[method-assign]

    # Assert
    assert image.virt_type == enums.VirtType.AUTO


def test_virt_bridge(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.virt_bridge = "testbridge"  # type: ignore[method-assign]

    # Assert
    assert image.virt_bridge == "testbridge"


def test_virt_path(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.virt_path = ""  # type: ignore[method-assign]

    # Assert
    assert image.virt_path == ""


def test_menu(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.menu = ""  # type: ignore[method-assign]

    # Assert
    assert image.menu == ""


def test_display_name(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.display_name = ""  # type: ignore[method-assign]

    # Assert
    assert image.display_name == ""


def test_supported_boot_loaders(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act & Assert
    assert image.supported_boot_loaders == [
        enums.BootLoader.GRUB,
        enums.BootLoader.PXE,
        enums.BootLoader.IPXE,
    ]


def test_boot_loaders(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    image = Image(cobbler_api)

    # Act
    image.boot_loaders = ""  # type: ignore[method-assign]

    # Assert
    assert image.boot_loaders == []


def test_to_dict(create_image: Callable[[], Image]):
    """
    TODO
    """
    # Arrange
    test_image = create_image()

    # Act
    result = test_image.to_dict(resolved=False)

    # Assert
    assert isinstance(result, dict)
    assert result.get("autoinstall") == enums.VALUE_INHERITED


def test_to_dict_resolved(create_image: Callable[[], Image]):
    """
    TODO
    """
    # Arrange
    test_image = create_image()

    # Act
    result = test_image.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("autoinstall") == "default.ks"
    assert enums.VALUE_INHERITED not in str(result)


def test_inheritance(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, test_settings: Settings
):
    """
    Checking that inherited properties are correctly inherited from settings and
    that the <<inherit>> value can be set for them.
    """
    # Arrange
    mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
    image = Image(cobbler_api)

    # Act
    for key, key_value in image.__dict__.items():
        if key_value == enums.VALUE_INHERITED:
            new_key = key[1:].lower()
            new_value = getattr(image, new_key)
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

            prev_value = getattr(image, new_key)
            setattr(image, new_key, enums.VALUE_INHERITED)

            # Assert
            assert prev_value == new_value
            assert prev_value == getattr(image, new_key)
