"""
Tests that validate the functionality of the module that is responsible for managing the signatures database of Cobbler.
"""

import pathlib

import pytest
from libcobblersignatures import Signatures
from libcobblersignatures.enums import ExportTypes, ImportTypes

from cobbler import enums
from cobbler.utils import signatures


def _write_built_in_signatures(path: pathlib.Path) -> None:
    built_in = Signatures()
    built_in.importsignatures(ImportTypes.BUILT_IN, "")
    built_in.jsontomodels()
    built_in.exportsignatures(ExportTypes.FILE, target=str(path))


@pytest.fixture(name="loaded_signatures")
def fixture_loaded_signatures(tmp_path: pathlib.Path) -> None:
    """
    Load the library's built-in signatures data into the module-wide cache for the duration of a test.
    """
    signatures_path = tmp_path / "distro_signatures.json"
    _write_built_in_signatures(signatures_path)
    signatures.load_signatures(str(signatures_path))


def test_get_supported_distro_boot_loaders():
    # Arrange

    # Act
    result = signatures.get_supported_distro_boot_loaders(None)  # type: ignore

    # Assert - use a set to ignore list ordering
    assert set(result) == {
        enums.BootLoader.GRUB,
        enums.BootLoader.PXE,
        enums.BootLoader.IPXE,
    }


def test_get_supported_distro_boot_loaders_converts_signature_strings_to_enum(
    loaded_signatures: None,
):
    # Arrange
    class FakeItem:
        breed = "redhat"
        os_version = "rhel7"
        arch = enums.Archs.PPC64LE

    # Act
    result = signatures.get_supported_distro_boot_loaders(FakeItem())  # type: ignore

    # Assert
    assert result == [enums.BootLoader.GRUB]


def test_load_signatures(tmp_path: pathlib.Path):
    # Arrange
    signatures_path = tmp_path / "distro_signatures.json"
    _write_built_in_signatures(signatures_path)

    # Act
    loaded = signatures.load_signatures(str(signatures_path))

    # Assert
    assert loaded.osbreeds
    assert signatures.get_breeds() == loaded.osbreeds


def test_get_valid_breeds(loaded_signatures: None):
    # Act
    result = signatures.get_valid_breeds()

    # Assert
    assert "redhat" in result
    assert "debian" in result


def test_get_valid_os_versions_for_breed(loaded_signatures: None):
    # Act
    result = signatures.get_valid_os_versions_for_breed("redhat")

    # Assert
    assert "rhel8" in result


def test_get_valid_os_versions_for_breed_unknown_breed(loaded_signatures: None):
    # Act
    result = signatures.get_valid_os_versions_for_breed("does-not-exist")

    # Assert
    assert result == []


def test_get_valid_os_versions(loaded_signatures: None):
    # Act
    result = signatures.get_valid_os_versions()

    # Assert
    assert "rhel8" in result
    assert len(result) == len(set(result))


def test_get_valid_archs(loaded_signatures: None):
    # Act
    result = signatures.get_valid_archs()

    # Assert
    assert "x86_64" in result
