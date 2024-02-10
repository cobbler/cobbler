"""
TODO
"""

import os
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.abstract.base_item import BaseItem
from cobbler.items.distro import Distro

from tests.conftest import does_not_raise

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture()
def test_settings(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    TODO
    """
    settings = mocker.MagicMock(name="item_setting_mock", spec=cobbler_api.settings())
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_item_create(cobbler_api: CobblerAPI):
    """
    Assert that an abstract Cobbler Item can be successfully created.
    """
    # Arrange

    # Act
    titem = BaseItem(cobbler_api)

    # Assert
    assert isinstance(titem, BaseItem)


def test_make_clone(cobbler_api: CobblerAPI):
    """
    Assert that an abstract Cobbler Item cannot be cloned and raises the expected NotImplementedError.
    """
    # Arrange
    titem = BaseItem(cobbler_api)

    # Act & Assert
    with pytest.raises(NotImplementedError):
        titem.make_clone()


def test_uid(cobbler_api: CobblerAPI):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the uid property correctly.
    """
    # Arrange
    titem = BaseItem(cobbler_api)

    # Act
    titem.uid = "uid"

    # Assert
    assert titem.uid == "uid"


def test_name(cobbler_api: CobblerAPI):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the name property correctly.
    """
    # Arrange
    titem = BaseItem(cobbler_api)

    # Act
    titem.name = "testname"

    # Assert
    assert titem.name == "testname"


def test_comment(cobbler_api: CobblerAPI):
    """
    Assert that an abstract Cobbler BaseItem can use the Getter and Setter of the comment property correctly.
    """
    # Arrange
    titem = BaseItem(cobbler_api)

    # Act
    titem.comment = "my comment"

    # Assert
    assert titem.comment == "my comment"


@pytest.mark.parametrize(
    "input_owners,expected_exception,expected_result",
    [
        ("", does_not_raise(), []),
        (enums.VALUE_INHERITED, does_not_raise(), ["admin"]),
        ("Test1 Test2", does_not_raise(), ["Test1", "Test2"]),
        (["Test1", "Test2"], does_not_raise(), ["Test1", "Test2"]),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_owners(
    cobbler_api: CobblerAPI,
    input_owners: Any,
    expected_exception: Any,
    expected_result: Optional[List[str]],
):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the owners property correctly.
    """
    # Arrange
    titem = BaseItem(cobbler_api)

    # Act
    with expected_exception:
        titem.owners = input_owners

        # Assert
        assert titem.owners == expected_result


@pytest.mark.parametrize(
    "input_ctime,expected_exception,expected_result",
    [("", pytest.raises(TypeError), None), (0.0, does_not_raise(), 0.0)],
)
def test_ctime(
    cobbler_api: CobblerAPI,
    input_ctime: Any,
    expected_exception: Any,
    expected_result: float,
):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the ctime property correctly.
    """
    # Arrange
    titem = BaseItem(cobbler_api)

    # Act
    with expected_exception:
        titem.ctime = input_ctime

        # Assert
        assert titem.ctime == expected_result


@pytest.mark.parametrize(
    "value,expected_exception",
    [
        (0.0, does_not_raise()),
        (0, pytest.raises(TypeError)),
        ("", pytest.raises(TypeError)),
    ],
)
def test_mtime(cobbler_api: CobblerAPI, value: Any, expected_exception: Any):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the mtime property correctly.
    """
    # Arrange
    titem = BaseItem(cobbler_api)

    # Act
    with expected_exception:
        titem.mtime = value

        # Assert
        assert titem.mtime == value


def test_grab_tree(cobbler_api: CobblerAPI):
    """
    Assert that grabbing the item tree is containing the settings.
    """
    # Arrange
    object_to_check = Distro(cobbler_api)
    # TODO: Create some objects and give them some inheritance.

    # Act
    result = object_to_check.grab_tree()

    # Assert
    assert isinstance(result, list)
    # pylint: disable-next=no-member
    assert result[-1].server == "192.168.1.1"  # type: ignore


def test_check_if_valid(request: "pytest.FixtureRequest", cobbler_api: CobblerAPI):
    """
    Asserts that the check for a valid item is performed successfuly.
    """
    # Arrange
    titem = BaseItem(cobbler_api)
    titem.name = (
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )

    # Act
    titem.check_if_valid()

    # Assert
    assert True  # This test passes if there is no exception raised


def test_from_dict(
    cobbler_api: CobblerAPI,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    Assert that an abstract Cobbler Item can be loaded from dict.
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


def test_to_dict(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler Item can be converted to a dictionary.
    """
    # Arrange
    titem = BaseItem(cobbler_api)

    # Act
    result = titem.to_dict()

    # Assert
    assert isinstance(result, dict)
    assert result.get("owners") == enums.VALUE_INHERITED


def test_to_dict_resolved(cobbler_api: CobblerAPI):
    """
    Assert that a Cobbler BaseItem can be converted to a dictionary with resolved values.
    """
    # Arrange
    titem = BaseItem(cobbler_api)

    # Act
    result = titem.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("owners") == ["admin"]
    assert enums.VALUE_INHERITED not in str(result)


def test_serialize(cobbler_api: CobblerAPI):
    """
    Assert that a given Cobbler Item can be serialized.
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


def test_sort_key(request: "pytest.FixtureRequest", cobbler_api: CobblerAPI):
    """
    Assert that the exported dict contains only the fields given in the argument.
    """
    # Arrange
    titem = BaseItem(cobbler_api)
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
    titem = BaseItem(cobbler_api, **in_keys)

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
    titem = BaseItem(cobbler_api)

    # Act
    result = titem.find_match_single_key(data_keys, check_key, check_value)

    # Assert
    assert expect_match == result


def test_dump_vars(cobbler_api: CobblerAPI):
    """
    Assert that you can dump all variables of an item.
    """
    # Arrange
    titem = BaseItem(cobbler_api)

    # Act
    result = titem.dump_vars(formatted_output=False)

    # Assert
    print(result)
    assert "default_ownership" in result
    assert "owners" in result
    assert len(result) == 151


def test_inheritance(mocker: "MockerFixture", cobbler_api: CobblerAPI, test_settings):
    """
    Checking that inherited properties are correctly inherited from settings and
    that the <<inherit>> value can be set for them.
    """
    # Arrange
    mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
    item = BaseItem(cobbler_api)

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
