import os

import pytest

from cobbler import enums
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.item import Item
from tests.conftest import does_not_raise


def test_item_create(cobbler_api):
    # Arrange

    # Act
    titem = Item(cobbler_api)

    # Assert
    assert isinstance(titem, Item)


def test_make_clone(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act & Assert
    with pytest.raises(NotImplementedError):
        titem.make_clone()


def test_from_dict(cobbler_api, create_kernel_initrd, fk_kernel, fk_initrd):
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


def test_uid(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.uid = "uid"

    # Assert
    assert titem.uid == "uid"


def test_children(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.children = []

    # Assert
    assert titem.children == []


def test_get_children(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    result = titem.get_children()

    # Assert
    assert result == []


def test_descendants(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    result = titem.descendants

    # Assert
    assert result == []


def test_get_conceptual_parent(request, cobbler_api, create_distro, create_profile):
    # Arrange
    tmp_distro = create_distro()
    tmp_profile = create_profile(tmp_distro.name)
    titem = Profile(cobbler_api)
    titem.name = "subprofile_%s" % request.node.originalname
    titem.parent = tmp_profile.name

    # Act
    result = titem.get_conceptual_parent()

    # Assert
    assert result.name == tmp_distro.name


def test_name(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.name = "testname"

    # Assert
    assert titem.name == "testname"


def test_comment(cobbler_api):
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
def test_owners(cobbler_api, input_owners, expected_exception, expected_result):
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
    cobbler_api, input_kernel_options, expected_exception, expected_result
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
    cobbler_api, input_kernel_options, expected_exception, expected_result
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
    cobbler_api, input_autoinstall_meta, expected_exception, expected_result
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
    cobbler_api, input_mgmt_parameters, expected_exception, expected_result
):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    with expected_exception:
        titem.mgmt_parameters = input_mgmt_parameters

        # Assert
        assert titem.mgmt_parameters == expected_result


def test_template_files(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.template_files = {}

    # Assert
    assert titem.template_files == {}


def test_boot_files(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.boot_files = {}

    # Assert
    assert titem.boot_files == {}


def test_fetchable_files(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.fetchable_files = {}

    # Assert
    assert titem.fetchable_files == {}


def test_sort_key(request, cobbler_api):
    # Arrange
    titem = Item(cobbler_api)
    titem.name = request.node.originalname

    # Act
    result = titem.sort_key(sort_fields=["name"])

    # Assert
    assert result == [request.node.originalname]


@pytest.mark.skip("Test not yet implemented")
def test_find_match(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.find_match()

    # Assert
    assert False


@pytest.mark.skip("Test not yet implemented")
def test_find_match_single_key(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.find_match_single_key()

    # Assert
    assert False


def test_dump_vars(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    result = titem.dump_vars(formatted_output=False)

    # Assert
    print(result)
    assert "default_ownership" in result
    assert "owners" in result
    assert len(result) == 149


@pytest.mark.parametrize(
    "input_depth,expected_exception,expected_result",
    [
        ("", pytest.raises(TypeError), None),
        (5, does_not_raise(), 5),
    ],
)
def test_depth(cobbler_api, input_depth, expected_exception, expected_result):
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
def test_ctime(cobbler_api, input_ctime, expected_exception, expected_result):
    # Arrange
    titem = Item(cobbler_api)

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
def test_mtime(cobbler_api, value, expected_exception):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    with expected_exception:
        titem.mtime = value

        # Assert
        assert titem.mtime == value


def test_parent(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    titem.parent = ""

    # Assert
    assert titem.parent is None


def test_check_if_valid(request, cobbler_api):
    # Arrange
    titem = Item(cobbler_api)
    titem.name = request.node.originalname

    # Act
    titem.check_if_valid()

    # Assert
    assert True  # This test passes if there is no exception raised


def test_to_dict(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    result = titem.to_dict()

    # Assert
    assert isinstance(result, dict)
    assert result.get("owners") == enums.VALUE_INHERITED


def test_to_dict_resolved(cobbler_api):
    # Arrange
    titem = Item(cobbler_api)

    # Act
    result = titem.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("owners") == ["admin"]


def test_to_dict_resolved_dict(cobbler_api, create_distro):
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


def test_serialize(cobbler_api):
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


def test_grab_tree(cobbler_api):
    # Arrange
    object_to_check = Distro(cobbler_api)
    # TODO: Create some objects and give them some inheritance.

    # Act
    result = object_to_check.grab_tree()

    # Assert
    assert isinstance(result, list)
    assert result[-1].server == "192.168.1.1"
