from cobbler.utils import signatures


def test_get_supported_distro_boot_loaders():
    # Arrange

    # Act
    result = signatures.get_supported_distro_boot_loaders(None)  # type: ignore

    # Assert
    assert result == ["grub", "pxe", "ipxe"]


def test_load_signatures():
    # Arrange
    signatures.signature_cache = {}
    old_cache = signatures.signature_cache

    # Act
    signatures.load_signatures("/var/lib/cobbler/distro_signatures.json")

    # Assert
    assert old_cache != signatures.signature_cache
