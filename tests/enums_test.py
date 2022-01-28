import pytest

from cobbler import enums
from tests.conftest import does_not_raise


@pytest.mark.parametrize(
    "test_architecture,test_raise",
    [
        (enums.Archs.X86_64, does_not_raise()),
        ("x86_64", does_not_raise()),
        ("abc", pytest.raises(ValueError)),
        (0, pytest.raises(TypeError)),
    ],
)
def test_validate_arch(test_architecture, test_raise):
    # Arrange

    # Act
    with test_raise:
        result = enums.Archs.to_enum(test_architecture)

        # Assert
        if isinstance(test_architecture, str):
            assert result.value == test_architecture
        elif isinstance(test_architecture, enums.Archs):
            assert result == test_architecture
        else:
            raise TypeError("result had a non expected result")


@pytest.mark.parametrize("value,expected_exception", [
    ("qemu", does_not_raise()),
    ("<<inherit>>", does_not_raise()),
    (enums.VirtType.QEMU, does_not_raise()),
    (enums.VirtType.INHERITED, does_not_raise()),
    (0, pytest.raises(TypeError))
])
def test_set_virt_type(value, expected_exception):
    # Arrange

    # Act
    with expected_exception:
        result = enums.VirtType.to_enum(value)

        # Assert
        if isinstance(value, str):
            assert result.value == value
        elif isinstance(value, enums.VirtType):
            assert result == value
        else:
            raise TypeError("Unexpected type for value!")


@pytest.mark.parametrize("value,expected_exception", [
    ("allow", does_not_raise()),
    (enums.TlsRequireCert.ALLOW, does_not_raise()),
    (enums.VALUE_INHERITED, pytest.raises(ValueError)),
    (0, pytest.raises(TypeError))
])
def test_validate_ldap_tls_reqcert(value, expected_exception):
    # Arrange

    # Act
    with expected_exception:
        result = enums.TlsRequireCert.to_enum(value)

        # Assert
        if isinstance(value, str):
            assert result.value == value
        elif isinstance(value, enums.TlsRequireCert):
            assert result == value
        else:
            raise TypeError("Unexpected type for value!")


@pytest.mark.parametrize("test_driver,test_raise", [
    (enums.VirtDiskDrivers.RAW, does_not_raise()),
    (enums.VALUE_INHERITED, does_not_raise()),
    (enums.VirtDiskDrivers.INHERITED, does_not_raise()),
    ("qcow2", does_not_raise()),
    ("<<inherit>>", does_not_raise()),
    ("bad_driver", pytest.raises(ValueError)),
    (0, pytest.raises(TypeError))
])
def test_set_virt_disk_driver(test_driver, test_raise):
    # Arrange

    # Act
    with test_raise:
        result = enums.VirtDiskDrivers.to_enum(test_driver)

        # Assert
        if isinstance(test_driver, str):
            assert result.value == test_driver
        elif isinstance(test_driver, enums.VirtDiskDrivers):
            assert result == test_driver
        else:
            raise TypeError("Unexpected type for value!")
