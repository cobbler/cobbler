import os
from typing import Dict, Any

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.package import Package
from cobbler.items.file import File
from cobbler.items.mgmtclass import Mgmtclass
from cobbler.items.repo import Repo
from cobbler.items.distro import Distro
from cobbler.items.menu import Menu
from cobbler.items.profile import Profile
from cobbler.items.item import Item

from tests.conftest import does_not_raise


@pytest.fixture()
def test_settings(mocker, cobbler_api: CobblerAPI):
    settings = mocker.MagicMock(name="item_setting_mock", spec=cobbler_api.settings())
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_item_create(cobbler_api: CobblerAPI):
    # Arrange

    # Act
    titem = Item(cobbler_api)

    # Assert
    assert isinstance(titem, Item)


def test_make_clone(cobbler_api: CobblerAPI):
    # Arrange
    titem = Item(cobbler_api)

    # Act & Assert
    with pytest.raises(NotImplementedError):
        titem.make_clone()


def test_from_dict(cobbler_api: CobblerAPI, create_kernel_initrd, fk_kernel, fk_initrd):
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


def test_uid(cobbler_api: CobblerAPI):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.uid = "uid"

    # Assert
    assert titem.uid == "uid"


def test_children(cobbler_api: CobblerAPI):
    # Arrange
    titem = Distro(cobbler_api)

    # Act

    # Assert
    assert titem.children == []


def test_tree_walk(cobbler_api: CobblerAPI):
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    result = titem.tree_walk()

    # Assert
    assert result == []


def test_item_descendants(cobbler_api: CobblerAPI):
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    result = titem.descendants

    # Assert
    assert result == []


def test_descendants(
    cobbler_api: CobblerAPI, create_distro, create_image, create_profile, create_system
):
    # Arrange
    test_package = Package(cobbler_api)
    test_package.name = "test_package"
    cobbler_api.add_package(test_package)
    test_file = File(cobbler_api)
    test_file.name = "test_file"
    test_file.path = "test path"
    test_file.owner = "test owner"
    test_file.group = "test group"
    test_file.mode = "test mode"
    test_file.is_dir = True
    cobbler_api.add_file(test_file)
    test_mgmtclass = Mgmtclass(cobbler_api)
    test_mgmtclass.name = "test_mgmtclass"
    test_mgmtclass.packages = [test_package.name]
    test_mgmtclass.files = [test_file.name]
    cobbler_api.add_mgmtclass(test_mgmtclass)
    test_repo = Repo(cobbler_api)
    test_repo.name = "test_repo"
    cobbler_api.add_repo(test_repo)
    test_menu1 = Menu(cobbler_api)
    test_menu1.name = "test_menu1"
    cobbler_api.add_menu(test_menu1)
    test_menu2 = Menu(cobbler_api)
    test_menu2.name = "test_menu2"
    test_menu2.parent = test_menu1.name
    cobbler_api.add_menu(test_menu2)
    test_distro = create_distro()
    test_distro.mgmt_classes = test_mgmtclass.name
    test_profile1 = create_profile(distro_name=test_distro.name, name="test_profile1")
    test_profile1.enable_menu = False
    test_profile1.repos = [test_repo.name]
    test_profile2 = create_profile(
        profile_name=test_profile1.name, name="test_profile2"
    )
    test_profile2.enable_menu = False
    test_profile2.menu = test_menu2.name
    test_profile3 = create_profile(
        profile_name=test_profile1.name, name="test_profile3"
    )
    test_profile3.enable_menu = False
    test_profile3.mgmt_classes = test_mgmtclass.name
    test_profile3.repos = [test_repo.name]
    test_image = create_image()
    test_image.menu = test_menu1.name
    test_system1 = create_system(profile_name=test_profile1.name, name="test_system1")
    test_system2 = create_system(image_name=test_image.name, name="test_system2")

    # Act
    cache_tests = [
        test_package.descendants,
        test_file.descendants,
        test_mgmtclass.descendants,
        test_repo.descendants,
        test_distro.descendants,
        test_image.descendants,
        test_profile1.descendants,
        test_profile2.descendants,
        test_profile3.descendants,
        test_menu1.descendants,
        test_menu2.descendants,
        test_system1.descendants,
        test_system2.descendants,
    ]
    results = [
        [
            test_mgmtclass,
            test_distro,
            test_profile1,
            test_profile2,
            test_profile3,
            test_system1,
        ],
        [
            test_mgmtclass,
            test_distro,
            test_profile1,
            test_profile2,
            test_profile3,
            test_system1,
        ],
        [test_distro, test_profile1, test_profile2, test_profile3, test_system1],
        [test_profile1, test_profile2, test_profile3, test_system1],
        [test_profile1, test_profile2, test_profile3, test_system1],
        [test_system2],
        [test_profile2, test_profile3, test_system1],
        [],
        [],
        [test_image, test_menu2, test_profile2, test_system2],
        [test_profile2],
        [],
        [],
    ]

    # Assert
    for x in range(len(cache_tests)):
        assert set(cache_tests[x]) == set(results[x])


def test_get_conceptual_parent(request, cobbler_api: CobblerAPI, create_distro, create_profile):
    # Arrange
    tmp_distro = create_distro()
    tmp_profile = create_profile(tmp_distro.name)
    titem = Profile(cobbler_api)
    titem.name = "subprofile_%s" % (
            request.node.originalname
            if request.node.originalname
            else request.node.name
        )
    titem.parent = tmp_profile.name

    # Act
    result = titem.get_conceptual_parent()

    # Assert
    assert result.name == tmp_distro.name


def test_name(cobbler_api: CobblerAPI):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.name = "testname"

    # Assert
    assert titem.name == "testname"


def test_comment(cobbler_api: CobblerAPI):
    # Arrange
    titem = Item(cobbler_api)

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
def test_owners(cobbler_api: CobblerAPI, input_owners, expected_exception, expected_result):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    with expected_exception:
        titem.owners = input_owners

        # Assert
        assert titem.owners == expected_result


@pytest.mark.parametrize(
    "input_kernel_options,expected_exception,expected_result",
    [
        ("", does_not_raise(), {}),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_kernel_options(
    cobbler_api: CobblerAPI, input_kernel_options, expected_exception, expected_result
):
    # Arrange
    titem = Item(cobbler_api)

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
    cobbler_api: CobblerAPI, input_kernel_options, expected_exception, expected_result
):
    # Arrange
    titem = Item(cobbler_api)

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
    cobbler_api: CobblerAPI, input_autoinstall_meta, expected_exception, expected_result
):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    with expected_exception:
        titem.autoinstall_meta = input_autoinstall_meta

        # Assert
        assert titem.autoinstall_meta == expected_result


@pytest.mark.parametrize(
    "input_mgmt_classes,expected_exception,expected_result",
    [
        ("", does_not_raise(), []),
        ("<<inherit>>", does_not_raise(), []),
        ("Test1 Test2", does_not_raise(), ["Test1", "Test2"]),
        (True, pytest.raises(TypeError), None),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_mgmt_classes(
    create_distro, input_mgmt_classes, expected_exception, expected_result
):
    # Arrange
    tmp_distro = create_distro()
    tmp_distro.mgmt_classes = ["Test0"]

    # Act
    with expected_exception:
        tmp_distro.mgmt_classes = input_mgmt_classes

        # Assert
        assert tmp_distro.mgmt_classes == expected_result


@pytest.mark.parametrize(
    "input_mgmt_parameters,expected_exception,expected_result",
    [
        ("", does_not_raise(), {"from_cobbler": 1}),
        ("a: 5", does_not_raise(), {"from_cobbler": 1, "a": 5}),
        ("<<inherit>>", does_not_raise(), {"from_cobbler": 1}),
        ({}, does_not_raise(), {"from_cobbler": 1}),
        ({"a": 5}, does_not_raise(), {"from_cobbler": 1, "a": 5}),
    ],
)
def test_mgmt_parameters(
    cobbler_api: CobblerAPI, input_mgmt_parameters, expected_exception, expected_result
):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    with expected_exception:
        titem.mgmt_parameters = input_mgmt_parameters

        # Assert
        assert titem.mgmt_parameters == expected_result


def test_template_files(cobbler_api: CobblerAPI):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.template_files = {}

    # Assert
    assert titem.template_files == {}


def test_boot_files(cobbler_api: CobblerAPI):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.boot_files = {}

    # Assert
    assert titem.boot_files == {}


def test_fetchable_files(cobbler_api: CobblerAPI):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.fetchable_files = {}

    # Assert
    assert titem.fetchable_files == {}


def test_sort_key(request, cobbler_api):
    # Arrange
    item_name = (
        request.node.originalname
        if request.node.originalname
        else request.node.name
    )
    titem = Item(cobbler_api)
    titem.name = item_name

    # Act
    result = titem.sort_key(sort_fields=["name"])

    # Assert
    assert result == [item_name]


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
    titem = Item(cobbler_api, **in_keys)

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
    titem = Item(cobbler_api)

    # Act
    result = titem.find_match_single_key(data_keys, check_key, check_value)

    # Assert
    assert expect_match == result


def test_dump_vars(cobbler_api: CobblerAPI):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    result = titem.dump_vars(formatted_output=False)

    # Assert
    assert "default_ownership" in result
    assert "owners" in result
    assert len(result) == 151


@pytest.mark.parametrize(
    "input_depth,expected_exception,expected_result",
    [
        ("", pytest.raises(TypeError), None),
        (5, does_not_raise(), 5),
    ],
)
def test_depth(cobbler_api: CobblerAPI, input_depth, expected_exception, expected_result):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    with expected_exception:
        titem.depth = input_depth

        # Assert
        assert titem.depth == expected_result


@pytest.mark.parametrize(
    "input_ctime,expected_exception,expected_result",
    [("", pytest.raises(TypeError), None), (0.0, does_not_raise(), 0.0)],
)
def test_ctime(cobbler_api: CobblerAPI, input_ctime, expected_exception, expected_result):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    with expected_exception:
        titem.ctime = input_ctime

        # Assert
        assert titem.ctime == expected_result


@pytest.mark.parametrize("value,expected_exception", [
    (0.0, does_not_raise()),
    (0, pytest.raises(TypeError)),
    ("", pytest.raises(TypeError))
])
def test_mtime(cobbler_api: CobblerAPI, value, expected_exception):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    with expected_exception:
        titem.mtime = value

        # Assert
        assert titem.mtime == value


def test_parent(cobbler_api: CobblerAPI):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.parent = ""

    # Assert
    assert titem.parent is None


def test_check_if_valid(request, cobbler_api):
    # Arrange
    titem = Item(cobbler_api)
    titem.name = (
            request.node.originalname
            if request.node.originalname
            else request.node.name
        )

    # Act
    titem.check_if_valid()

    # Assert
    assert True  # This test passes if there is no exception raised


def test_to_dict(cobbler_api: CobblerAPI):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    result = titem.to_dict()

    # Assert
    assert isinstance(result, dict)
    assert result.get("owners") == enums.VALUE_INHERITED


def test_to_dict_resolved(cobbler_api: CobblerAPI):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    result = titem.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("owners") == ["admin"]


def test_to_dict_resolved_dict(cobbler_api: CobblerAPI, create_distro):
    # Arrange
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}
    cobbler_api.add_distro(test_distro)
    titem = Profile(cobbler_api)
    titem.name = "to_dict_resolved_profile"
    titem.distro = test_distro.name
    titem.kernel_options = {"my_value": 5}
    cobbler_api.add_profile(titem)

    # Act
    result = titem.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("kernel_options") == {"test": True, "my_value": 5}


def test_serialize(cobbler_api: CobblerAPI):
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


def test_grab_tree(cobbler_api: CobblerAPI):
    # Arrange
    object_to_check = Distro(cobbler_api)
    # TODO: Create some objects and give them some inheritance.

    # Act
    result = object_to_check.grab_tree()

    # Assert
    assert isinstance(result, list)
    assert result[-1].server == "192.168.1.1"


def test_inheritance(mocker, cobbler_api: CobblerAPI, test_settings):
    """
    Checking that inherited properties are correctly inherited from settings and
    that the <<inherit>> value can be set for them.
    """
    # Arrange
    mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
    item = Item(cobbler_api)

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
