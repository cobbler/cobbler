"""
Tests that validate the functionality of the module that is responsible for managing the signatures database of Cobbler.
"""

from typing import Any, Dict

from cobbler import enums
from cobbler.utils import signatures


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


def test_load_signatures():
    # Arrange
    new_signatures: Dict[str, Any] = {}
    signatures.signature_cache = new_signatures
    old_cache = signatures.signature_cache

    # Act
    signatures.load_signatures("/var/lib/cobbler/distro_signatures.json")

    # Assert
    assert old_cache != signatures.signature_cache
