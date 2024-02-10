"""
Test module to confirm that the Cobbler Item Distro is working as expected.
"""

import os
import pathlib
from typing import Any, Callable

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.utils import signatures

from tests.conftest import does_not_raise


@pytest.fixture()
def test_settings(mocker, cobbler_api: CobblerAPI):
    settings = mocker.MagicMock(name="distro_setting_mock", spec=cobbler_api.settings())
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_object_creation(cobbler_api: CobblerAPI):
    """
    Verify that the constructor is working as expected.
    """
    # Arrange

    # Act
    distro = Distro(cobbler_api)

    # Arrange
    assert isinstance(distro, Distro)


def test_non_equality(cobbler_api: CobblerAPI):
    """
    Test that verifies if two created Distros don't match each other.
    """
    # Arrange
    distro1 = Distro(cobbler_api)
    distro2 = Distro(cobbler_api)

    # Act & Assert
    assert distro1 != distro2
    assert "" != distro1


def test_equality(cobbler_api: CobblerAPI):
    """
    Test that verifies if the equality check for Distros is working.
    """
    # Arrange
    distro = Distro(cobbler_api)

    # Act & Assert
    assert distro == distro


def test_make_clone(
    cobbler_api: CobblerAPI,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    Test that verifies that cloning a Distro is working as expected.
    """
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


def test_parent(cobbler_api: CobblerAPI):
    """
    Test that verifies if the parent of a Distro cannot be set.
    """
    # Arrange
    distro = Distro(cobbler_api)

    # Act & Assert
    assert distro.parent is None


def test_check_if_valid(
    cobbler_api: CobblerAPI,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    Test that verifies if the check for the validity of a Distro is working as expected.
    """
    # Arrange
    test_folder = create_kernel_initrd(fk_kernel, fk_initrd)
    test_distro = Distro(cobbler_api)
    test_distro.name = "testname"
    test_distro.kernel = os.path.join(test_folder, fk_kernel)
    test_distro.initrd = os.path.join(test_folder, fk_initrd)

    # Act
    test_distro.check_if_valid()

    # Assert
    assert True


def test_to_dict(cobbler_api: CobblerAPI):
    """
    Test that verifies if conversion to a pure dictionary works as expected (with raw data).
    """
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


def test_to_dict_resolved(cobbler_api: CobblerAPI, create_distro: Callable[[], Distro]):
    """
    Test that verifies if conversion to a pure dictionary works as expected (with resolved data).
    """
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
def test_tree_build_time(cobbler_api: CobblerAPI, value: Any, expected: Any):
    """
    Test that verifies if the tree build time can be correctly set and read as expected.
    """
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
def test_arch(cobbler_api: CobblerAPI, value: Any, expected: Any):
    """
    Test that verifies if the architecture of the Distro can be set as expected.
    """
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
def test_boot_loaders(
    cobbler_api: CobblerAPI, value: Any, expected_exception: Any, expected_result: Any
):
    """
    Test that verifies if the boot loaders can be set as expected.
    """
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
def test_breed(cobbler_api: CobblerAPI, value: Any, expected_exception: Any):
    """
    Test that verifies if the OS breed can be set as expected.
    """
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
    ],
)
def test_initrd(cobbler_api: CobblerAPI, value: Any, expected_exception: Any):
    """
    Test that verifies if the initrd path can be set as expected.
    """
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
    ],
)
def test_kernel(cobbler_api: CobblerAPI, value: Any, expected_exception: Any):
    """
    Test that verifies if the kernel path can be set as expected.
    """
    # TODO: Create fake kernel so we can set it successfully
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.kernel = value

        # Assert
        assert distro.kernel == value


@pytest.mark.parametrize(
    "value,expected_exception",
    [([""], pytest.raises(TypeError)), (False, pytest.raises(TypeError))],
)
def test_os_version(cobbler_api: CobblerAPI, value: Any, expected_exception: Any):
    """
    Test that verifies if the OS version can be set as expected.
    """
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.os_version = value

        # Assert
        assert distro.os_version == value


@pytest.mark.parametrize("value", [[""], ["Test"]])
def test_owners(cobbler_api: CobblerAPI, value: Any):
    """
    Test that verifies if the owners of a Distro can be set as expected.
    """
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
def test_redhat_management_key(
    cobbler_api: CobblerAPI, value: Any, expected_exception: Any, expected_result: str
):
    """
    Test that verifies if the redhat management key can be set as expected.
    """
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.redhat_management_key = value

        # Assert
        assert distro.redhat_management_key == expected_result


@pytest.mark.parametrize("value", [[""], ["Test"]])
def test_source_repos(cobbler_api: CobblerAPI, value: Any):
    """
    Test that verifies if the source repositories can be set as expected.
    """
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
        ("", does_not_raise()),
    ],
)
def test_remote_boot_kernel(
    cobbler_api: CobblerAPI, value: Any, expected_exception: Any
):
    """
    Test that verifies if a remote boot path can be set as expected.
    """
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
def test_remote_grub_kernel(
    cobbler_api: CobblerAPI, value: Any, expected_exception: Any
):
    """
    Test that verifies if a remote GRUB path can be set as expected for the kernel.
    """
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
def test_remote_boot_initrd(
    cobbler_api: CobblerAPI, value: Any, expected_exception: Any
):
    """
    Test that verifies if a remote initrd path can be set as expected for the initrd.
    """
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
def test_remote_grub_initrd(
    cobbler_api: CobblerAPI, value: Any, expected_exception: Any
):
    """
    Test that verifies if a given remote initrd path is correctly converted to its GRUB counter part.
    """
    # Arrange
    distro = Distro(cobbler_api)

    # Act
    with expected_exception:
        distro.remote_boot_initrd = value

        # Assert
        assert distro.remote_grub_initrd == value


def test_supported_boot_loaders(cobbler_api: CobblerAPI):
    """
    Test that verifies if the supported bootloaders are correctly detected for the current Distro.
    """
    # Arrange
    distro = Distro(cobbler_api)

    # Assert
    assert isinstance(distro.supported_boot_loaders, list)
    assert distro.supported_boot_loaders == ["grub", "pxe", "ipxe"]


@pytest.mark.skip(
    "This is hard to test as we are creating a symlink in the method. For now we skip it."
)
def test_link_distro(cobbler_api: CobblerAPI):
    """
    Test that verifies if the Distro is correctly linked inside the web directory.
    """
    # Arrange
    test_distro = Distro(cobbler_api)

    # Act
    test_distro.link_distro()

    # Assert
    assert False


def test_find_distro_path(
    cobbler_api: CobblerAPI,
    create_testfile: Callable[[str], None],
    tmp_path: pathlib.Path,
):
    """
    Test that verifies if the method "find_distro_path()" can correctly identify the folder of the Distro in the
    web directory.
    """
    # Arrange
    fk_kernel = "vmlinuz1"
    create_testfile(fk_kernel)
    test_distro = Distro(cobbler_api)
    test_distro.kernel = os.path.join(tmp_path, fk_kernel)

    # Act
    result = test_distro.find_distro_path()

    # Assert
    assert result == tmp_path.as_posix()


def test_inheritance(mocker, cobbler_api: CobblerAPI, test_settings):
    """
    Checking that inherited properties are correctly inherited from settings and
    that the <<inherit>> value can be set for them.
    """
    # Arrange
    mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
    distro = Distro(cobbler_api)

    # Act
    for key, key_value in distro.__dict__.items():
        if key_value == enums.VALUE_INHERITED:
            new_key = key[1:].lower()
            new_value = getattr(distro, new_key)
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

            prev_value = getattr(distro, new_key)
            setattr(distro, new_key, enums.VALUE_INHERITED)

            # Assert
            assert prev_value == new_value
            assert prev_value == getattr(distro, new_key)
