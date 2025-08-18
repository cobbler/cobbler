"""
Test module that asserts that generic Cobbler BootableItem functionality is working as expected.
"""

import os
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.abstract.bootable_item import BootableItem
from cobbler.items.distro import Distro
from cobbler.settings import Settings

from tests.conftest import does_not_raise

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="test_settings")
def fixture_test_settings(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test fixture that mocks the settings for the bootable items.
    """
    settings = mocker.MagicMock(name="item_setting_mock", spec=cobbler_api.settings())
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_item_create(cobbler_api: CobblerAPI):
    """
    Assert that an abstract Cobbler BootableItem can be successfully created.
    """
    # Arrange

    # Act
    titem = Distro(cobbler_api)

    # Assert
    assert isinstance(titem, BootableItem)


def test_from_dict(
    cobbler_api: CobblerAPI,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    Assert that an abstract Cobbler BootableItem can be loaded from dict.
    """
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    name = "test_from_dict"
    kernel_path = os.path.join(folder, fk_kernel)
    initrd_path = os.path.join(folder, fk_initrd)
    titem = Distro(cobbler_api)

    # Act
    titem.from_dict({"name": name, "kernel": kernel_path, "initrd": initrd_path})

    # Assert
    titem.check_if_valid()  # This raises an exception if something is not right.
    assert titem.name == name
    assert titem.kernel == kernel_path
    assert titem.initrd == initrd_path


@pytest.mark.parametrize(
    "input_kernel_options,expected_exception,expected_result",
    [
        ("", does_not_raise(), {}),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_kernel_options(
    cobbler_api: CobblerAPI,
    input_kernel_options: Any,
    expected_exception: Any,
    expected_result: Optional[Dict[Any, Any]],
):
    """
    Assert that an abstract Cobbler BootableItem can use the Getter and Setter of the kernel_options property correctly.
    """
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    with expected_exception:
        titem.kernel_options = input_kernel_options

        # Assert
        assert titem.kernel_options == expected_result


@pytest.mark.parametrize(
    "input_kernel_options,expected_exception,expected_result",
    [
        ("", does_not_raise(), {}),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_kernel_options_post(
    cobbler_api: CobblerAPI,
    input_kernel_options: Any,
    expected_exception: Any,
    expected_result: Optional[Dict[Any, Any]],
):
    """
    Assert that an abstract Cobbler BootableItem can use the Getter and Setter of the kernel_options_post property
    correctly.
    """
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    with expected_exception:
        titem.kernel_options_post = input_kernel_options

        # Assert
        assert titem.kernel_options_post == expected_result


@pytest.mark.parametrize(
    "input_autoinstall_meta,expected_exception,expected_result",
    [
        ("", does_not_raise(), {}),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_autoinstall_meta(
    cobbler_api: CobblerAPI,
    input_autoinstall_meta: Any,
    expected_exception: Any,
    expected_result: Optional[Dict[Any, Any]],
):
    """
    Assert that an abstract Cobbler BootableItem can use the Getter and Setter of the autoinstall_meta property
    correctly.
    """
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    with expected_exception:
        titem.autoinstall_meta = input_autoinstall_meta

        # Assert
        assert titem.autoinstall_meta == expected_result


def test_template_files(cobbler_api: CobblerAPI):
    """
    Assert that an abstract Cobbler BootableItem can use the Getter and Setter of the template_files property correctly.
    """
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    titem.template_files = {}

    # Assert
    assert titem.template_files == {}


def test_sort_key(request: "pytest.FixtureRequest", cobbler_api: CobblerAPI):
    """
    Assert that the exported dict contains only the fields given in the argument.
    """
    # Arrange
    titem = Distro(cobbler_api)
    titem.name = (
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )

    # Act
    result = titem.sort_key(sort_fields=["name"])

    # Assert
    assert result == [
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    ]


@pytest.mark.parametrize(
    "in_keys, check_keys, expect_match",
    [
        ({"uid": "test-uid"}, {"uid": "test-uid"}, True),
        ({"name": "test-object"}, {"name": "test-object"}, True),
        ({"comment": "test-comment"}, {"comment": "test-comment"}, True),
        ({"uid": "test-uid"}, {"uid": ""}, False),
    ],
)
def test_find_match(
    cobbler_api: CobblerAPI,
    in_keys: Dict[str, Any],
    check_keys: Dict[str, Any],
    expect_match: bool,
):
    """
    Assert that given a desired amount of key-value pairs is matching the item or not.
    """
    # Arrange
    titem = Distro(cobbler_api, **in_keys)

    # Act
    result = titem.find_match(check_keys)

    # Assert
    assert expect_match == result


@pytest.mark.parametrize(
    "data_keys, check_key, check_value, expect_match",
    [
        ({"uid": "test-uid"}, "uid", "test-uid", True),
        ({"menu": "testmenu0"}, "menu", "testmenu0", True),
        ({"uid": "test", "name": "test-name"}, "uid", "test", True),
        ({"depth": "1"}, "name", "test", False),
        ({"uid": "test", "name": "test-name"}, "menu", "testmenu0", False),
    ],
)
def test_find_match_single_key(
    cobbler_api: CobblerAPI,
    data_keys: Dict[str, Any],
    check_key: str,
    check_value: Any,
    expect_match: bool,
):
    """
    Assert that a single given key and value match the object or not.
    """
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    result = titem.find_match_single_key(data_keys, check_key, check_value)

    # Assert
    assert expect_match == result


def test_dump_vars(cobbler_api: CobblerAPI):
    """
    Assert that you can dump all variables of an item.
    """
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    result = titem.dump_vars(formatted_output=False)

    # Assert
    print(result)
    assert "default_ownership" in result
    assert "owners" in result
    assert len(result) == 173


def test_to_dict(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler BootableItem can be converted to a dictionary.
    """
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    result = titem.to_dict()

    # Assert
    assert isinstance(result, dict)
    assert result.get("owners") == enums.VALUE_INHERITED


def test_to_dict_resolved(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler BootableItem can be converted to a dictionary with resolved values.
    """
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    result = titem.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("owners") == ["admin"]
    assert enums.VALUE_INHERITED not in str(result)


def test_serialize(cobbler_api: CobblerAPI):
    """
    Assert that a given Cobbler BootableItem can be serialized.
    """
    # Arrange
    kernel_url = "http://10.0.0.1/custom-kernels-are-awesome"
    titem = Distro(cobbler_api)
    titem.remote_boot_kernel = kernel_url

    # Act
    result = titem.serialize()

    # Assert
    assert titem.remote_boot_kernel == kernel_url
    assert titem.remote_grub_kernel.startswith("(http,")
    assert "remote_grub_kernel" not in result


def test_inheritance(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, test_settings: Settings
):
    """
    Checking that inherited properties are correctly inherited from settings and
    that the <<inherit>> value can be set for them.
    """
    # Arrange
    mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
    item = Distro(cobbler_api)

    # Act
    for key, key_value in item.__dict__.items():
        if key_value == enums.VALUE_INHERITED:
            new_key = key[1:].lower()
            new_value = getattr(item, new_key)
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

            prev_value = getattr(item, new_key)
            setattr(item, new_key, enums.VALUE_INHERITED)

            # Assert
            assert prev_value == new_value
            assert prev_value == getattr(item, new_key)
