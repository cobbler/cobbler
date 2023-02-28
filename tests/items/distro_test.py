import os

import pytest

from cobbler import enums
from cobbler.utils import signatures
from cobbler.items.distro import Distro
from tests.conftest import does_not_raise


def test_object_creation(cobbler_api):
    # Arrange

    # Act
    distro = Distro(cobbler_api)

    # Arrange
    assert isinstance(distro, Distro)


def test_non_equality(cobbler_api):
    # Arrange
    distro1 = Distro(cobbler_api)
    distro2 = Distro(cobbler_api)

    # Act & Assert
    assert distro1 != distro2
    assert "" != distro1


def test_equality(cobbler_api):
    # Arrange
    distro = Distro(cobbler_api)

    # Act & Assert
    assert distro == distro


def test_make_clone(cobbler_api, create_kernel_initrd, fk_kernel, fk_initrd):
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    signatures.load_signatures("/var/lib/cobbler/distro_signatures.json")
    distro = Distro(cobbler_api)
    distro.breed = "suse"
    distro.os_version = "sles15generic"
    distro.kernel = os.path.join(folder, fk_kernel)
    distro.initrd = os.path.join(folder, fk_initrd)

    # Act
    result = distro.make_clone()

    # Assert
    # TODO: When in distro.py the FIXME of this method is done then adjust this here
    assert result != distro


def test_parent(cobbler_api):
    # Arrange
    distro = Distro(cobbler_api)

    # Act & Assert
    assert distro.parent is None


def test_check_if_valid(cobbler_api):
    # Arrange
    distro = Distro(cobbler_api)
    distro.name = "testname"

    # Act
    distro.check_if_valid()

    # Assert
    assert True


def test_to_dict(cobbler_api):
    # Arrange
    titem = Distro(cobbler_api)

    # Act
    result = titem.to_dict()

    # Assert
    assert isinstance(result, dict)
    assert "autoinstall_meta" in result
    assert "ks_meta" in result
    assert result.get("boot_loaders") == enums.VALUE_INHERITED
    # TODO check more fields


def test_to_dict_resolved(cobbler_api, create_distro):
    # Arrange
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}
    cobbler_api.add_distro(test_distro)

    # Act
    result = test_distro.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("kernel_options") == {"test": True}
    assert result.get("boot_loaders") == ["grub", "pxe", "ipxe"]
    assert enums.VALUE_INHERITED not in str(result)


# Properties Tests


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, does_not_raise()),
        (0.0, does_not_raise()),
        ("", pytest.raises(TypeError)),
        ("Test", pytest.raises(TypeError)),
        ([], pytest.raises(TypeError)),
        ({}, pytest.raises(TypeError)),
        (None, pytest.raises(TypeError)),
    ],
)
def test_tree_build_time(cobbler_api, value, expected):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected:
        distro.tree_build_time = value

        # Assert
        assert distro.tree_build_time == value


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", pytest.raises(ValueError)),
        ("Test", pytest.raises(ValueError)),
        (0, pytest.raises(TypeError)),
        (0.0, pytest.raises(TypeError)),
        ([], pytest.raises(TypeError)),
        ({}, pytest.raises(TypeError)),
        (None, pytest.raises(TypeError)),
        ("x86_64", does_not_raise()),
        (enums.Archs.X86_64, does_not_raise()),
    ],
)
def test_arch(cobbler_api, value, expected):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected:
        distro.arch = value

        # Assert
        if isinstance(value, str):
            assert distro.arch.value == value
        else:
            assert distro.arch == value


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("", does_not_raise(), ""),
        ("<<inherit>>", does_not_raise(), ["grub", "pxe", "ipxe"]),
        ("Test", pytest.raises(ValueError), ""),
        (0, pytest.raises(TypeError), ""),
        (["grub"], does_not_raise(), ["grub"]),
    ],
)
def test_boot_loaders(cobbler_api, value, expected_exception, expected_result):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.boot_loaders = value

        # Assert
        if value == "":
            assert distro.boot_loaders == []
        else:
            assert distro.boot_loaders == expected_result


@pytest.mark.parametrize(
    "value,expected_exception",
    [("", does_not_raise()), (0, pytest.raises(TypeError)), ("suse", does_not_raise())],
)
def test_breed(cobbler_api, value, expected_exception):
    # Arrange
    signatures.load_signatures("/var/lib/cobbler/distro_signatures.json")
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.breed = value

        # Assert
        assert distro.breed == value


@pytest.mark.parametrize(
    "value,expected_exception",
    [
        ([], pytest.raises(TypeError)),
        (False, pytest.raises(TypeError)),
        ("", pytest.raises(ValueError)),
    ],
)
def test_initrd(cobbler_api, value, expected_exception):
    # TODO: Create fake initrd so we can set it successfully
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.initrd = value

        # Assert
        assert distro.initrd == value


@pytest.mark.parametrize(
    "value,expected_exception",
    [
        ([], pytest.raises(TypeError)),
        (False, pytest.raises(TypeError)),
        ("", pytest.raises(ValueError)),
    ],
)
def test_kernel(cobbler_api, value, expected_exception):
    # TODO: Create fake kernel so we can set it successfully
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.kernel = value

        # Assert
        assert distro.kernel == value


@pytest.mark.parametrize("value", [[""], ["Test"]])
def test_mgmt_classes(cobbler_api, value):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    distro.mgmt_classes = value

    # Assert
    assert distro.mgmt_classes == value


@pytest.mark.parametrize(
    "value,expected_exception",
    [([""], pytest.raises(TypeError)), (False, pytest.raises(TypeError))],
)
def test_os_version(cobbler_api, value, expected_exception):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.os_version = value

        # Assert
        assert distro.os_version == value


@pytest.mark.parametrize("value", [[""], ["Test"]])
def test_owners(cobbler_api, value):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    distro.owners = value

    # Assert
    assert distro.owners == value


@pytest.mark.parametrize(
    "value,expected_exception,expected_result",
    [
        ("", does_not_raise(), ""),
        (["Test"], pytest.raises(TypeError), ""),
        ("<<inherit>>", does_not_raise(), ""),
    ],
)
def test_redhat_management_key(cobbler_api, value, expected_exception, expected_result):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.redhat_management_key = value

        # Assert
        assert distro.redhat_management_key == expected_result


@pytest.mark.parametrize("value", [[""], ["Test"]])
def test_source_repos(cobbler_api, value):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    distro.source_repos = value

    # Assert
    assert distro.source_repos == value


@pytest.mark.parametrize(
    "value,expected_exception",
    [
        ([""], pytest.raises(TypeError)),
        # ("test=test test1 test2=0", does_not_raise()), --> Fix this. It works but we can't compare
        ({"test": "test", "test2": 0}, does_not_raise()),
    ],
)
def test_fetchable_files(cobbler_api, value, expected_exception):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.fetchable_files = value

        # Assert
        assert distro.fetchable_files == value


@pytest.mark.parametrize(
    "value,expected_exception",
    [
        ([""], pytest.raises(TypeError)),
        ("", does_not_raise()),
    ],
)
def test_remote_boot_kernel(cobbler_api, value, expected_exception):
    # Arrange
    # TODO: Create fake kernel so we can test positive paths
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.remote_boot_kernel = value

        # Assert
        assert distro.remote_boot_kernel == value


@pytest.mark.parametrize(
    "value,expected_exception",
    [
        ([""], pytest.raises(TypeError)),
        (["Test"], pytest.raises(TypeError)),
        ("", does_not_raise()),
    ],
)
def test_remote_grub_kernel(cobbler_api, value, expected_exception):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.remote_boot_kernel = value

        # Assert
        assert distro.remote_grub_kernel == value


@pytest.mark.parametrize(
    "value,expected_exception",
    [([""], pytest.raises(TypeError)), ("", does_not_raise())],
)
def test_remote_boot_initrd(cobbler_api, value, expected_exception):
    # TODO: Create fake initrd to have a real test
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.remote_boot_initrd = value

        # Assert
        assert distro.remote_boot_initrd == value


@pytest.mark.parametrize(
    "value,expected_exception",
    [([""], pytest.raises(TypeError)), ("", does_not_raise())],
)
def test_remote_grub_initrd(cobbler_api, value, expected_exception):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.remote_boot_initrd = value

        # Assert
        assert distro.remote_grub_initrd == value


def test_supported_boot_loaders(cobbler_api):
    # Arrange
    distro = Distro(cobbler_api)

    # Assert
    assert isinstance(distro.supported_boot_loaders, list)
    assert distro.supported_boot_loaders == ["grub", "pxe", "ipxe"]


@pytest.mark.skip(
    "This is hard to test as we are creating a symlink in the method. For now we skip it."
)
def test_link_distro(cobbler_api):
    # Arrange
    test_distro = Distro(cobbler_api)

    # Act
    test_distro.link_distro()

    # Assert
    assert False


def test_find_distro_path(cobbler_api, create_testfile, tmp_path):
    # Arrange
    fk_kernel = "vmlinuz1"
    create_testfile(fk_kernel)
    test_distro = Distro(cobbler_api)
    test_distro.kernel = os.path.join(tmp_path, fk_kernel)

    # Act
    result = test_distro.find_distro_path()

    # Assert
    assert result == tmp_path.as_posix()
