from cobbler.utils import signatures


def test_get_supported_distro_boot_loaders():
    # Arrange

    # Act
    result = signatures.get_supported_distro_boot_loaders(None)

    # Assert
    assert result == ["grub", "pxe", "ipxe"]


def test_load_signatures():
    # Arrange
    signatures.SIGNATURE_CACHE = {}
    old_cache = signatures.SIGNATURE_CACHE

    # Act
    signatures.load_signatures("/var/lib/cobbler/distro_signatures.json")

    # Assert
    assert old_cache != signatures.SIGNATURE_CACHE
