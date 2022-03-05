import os

import pytest

from cobbler import enums, utils
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
    utils.load_signatures("/var/lib/cobbler/distro_signatures.json")
    distro = Distro(cobbler_api)
    distro.breed = "suse"
    distro.os_version = "sles15generic"
    distro.kernel = os.path.join(folder, "vmlinuz1")
    distro.initrd = os.path.join(folder, "initrd1.img")

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
    # TODO check more fields


# Properties Tests

@pytest.mark.parametrize("value,expected", [
    (0, does_not_raise()),
    (0.0, does_not_raise()),
    ("", pytest.raises(TypeError)),
    ("Test", pytest.raises(TypeError)),
    ([], pytest.raises(TypeError)),
    ({}, pytest.raises(TypeError)),
    (None, pytest.raises(TypeError))
])
def test_tree_build_time(cobbler_api, value, expected):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected:
        distro.tree_build_time = value

        # Assert
        assert distro.tree_build_time == value


@pytest.mark.parametrize("value,expected", [
    ("", pytest.raises(ValueError)),
    ("Test", pytest.raises(ValueError)),
    (0, pytest.raises(TypeError)),
    (0.0, pytest.raises(TypeError)),
    ([], pytest.raises(TypeError)),
    ({}, pytest.raises(TypeError)),
    (None, pytest.raises(TypeError)),
    ("x86_64", does_not_raise()),
    (enums.Archs.X86_64, does_not_raise())
])
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


@pytest.mark.parametrize("value,expected_exception", [
    ("", does_not_raise()),
    ("Test", pytest.raises(ValueError)),
    (0, pytest.raises(TypeError)),
    (["grub"], does_not_raise())
])
def test_boot_loaders(cobbler_api, value, expected_exception):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.boot_loaders = value

        # Assert
        if value == "":
            assert distro.boot_loaders == []
        else:
            assert distro.boot_loaders == value


@pytest.mark.parametrize("value,expected_exception", [
    ("", does_not_raise()),
    (0, pytest.raises(TypeError)),
    ("suse", does_not_raise())
])
def test_breed(cobbler_api, value, expected_exception):
    # Arrange
    utils.load_signatures("/var/lib/cobbler/distro_signatures.json")
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.breed = value

        # Assert
        assert distro.breed == value


@pytest.mark.parametrize("value,expected_exception", [
    ([], pytest.raises(TypeError)),
    (False, pytest.raises(TypeError)),
    ("", pytest.raises(ValueError))
])
def test_initrd(cobbler_api, value, expected_exception):
    # TODO: Create fake initrd so we can set it successfully
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.initrd = value

        # Assert
        assert distro.initrd == value


@pytest.mark.parametrize("value,expected_exception", [
    ([], pytest.raises(TypeError)),
    (False, pytest.raises(TypeError)),
    ("", pytest.raises(ValueError))
])
def test_kernel(cobbler_api, value, expected_exception):
    # TODO: Create fake kernel so we can set it successfully
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.kernel = value

        # Assert
        assert distro.kernel == value


@pytest.mark.parametrize("value", [
    [""],
    ["Test"]
])
def test_mgmt_classes(cobbler_api, value):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    distro.mgmt_classes = value

    # Assert
    assert distro.mgmt_classes == value


@pytest.mark.parametrize("value,expected_exception", [
    ([""], pytest.raises(TypeError)),
    (False, pytest.raises(TypeError))
])
def test_os_version(cobbler_api, value, expected_exception):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.os_version = value

        # Assert
        assert distro.os_version == value


@pytest.mark.parametrize("value", [
    [""],
    ["Test"]
])
def test_owners(cobbler_api, value):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    distro.owners = value

    # Assert
    assert distro.owners == value


@pytest.mark.parametrize("value,expected_exception", [
    ("", does_not_raise()),
    (["Test"], pytest.raises(TypeError))
])
def test_redhat_management_key(cobbler_api, value, expected_exception):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.redhat_management_key = value

        # Assert
        assert distro.redhat_management_key == value


@pytest.mark.parametrize("value", [
    [""],
    ["Test"]
])
def test_source_repos(cobbler_api, value):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    distro.source_repos = value

    # Assert
    assert distro.source_repos == value


@pytest.mark.parametrize("value,expected_exception", [
    ([""], pytest.raises(TypeError)),
    # ("test=test test1 test2=0", does_not_raise()), --> Fix this. It works but we can't compare
    ({"test": "test", "test2": 0}, does_not_raise())
])
def test_fetchable_files(cobbler_api, value, expected_exception):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.fetchable_files = value

        # Assert
        assert distro.fetchable_files == value


@pytest.mark.parametrize("value,expected_exception", [
    ([""], pytest.raises(TypeError)),
    ("", does_not_raise()),
])
def test_remote_boot_kernel(cobbler_api, value, expected_exception):
    # Arrange
    # TODO: Create fake kernel so we can test positive paths
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.remote_boot_kernel = value

        # Assert
        assert distro.remote_boot_kernel == value


@pytest.mark.parametrize("value,expected_exception", [
    ([""], pytest.raises(TypeError)),
    (["Test"], pytest.raises(TypeError)),
    ("", does_not_raise())
])
def test_remote_grub_kernel(cobbler_api, value, expected_exception):
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.remote_boot_kernel = value

        # Assert
        assert distro.remote_grub_kernel == value


@pytest.mark.parametrize("value,expected_exception", [
    ([""], pytest.raises(TypeError)),
    ("", does_not_raise())
])
def test_remote_boot_initrd(cobbler_api, value, expected_exception):
    # TODO: Create fake initrd to have a real test
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.remote_boot_initrd = value

        # Assert
        assert distro.remote_boot_initrd == value


@pytest.mark.parametrize("value,expected_exception", [
    ([""], pytest.raises(TypeError)),
    ("", does_not_raise())
])
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
