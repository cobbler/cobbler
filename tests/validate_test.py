import uuid
from ipaddress import AddressValueError, NetmaskValueError

import pytest

from cobbler import enums, utils, validate
from tests.conftest import does_not_raise


@pytest.mark.parametrize(
    "input_dnsname,expected_result,expected_exception",
    [
        (0, "", pytest.raises(TypeError)),
        ("", "", does_not_raise()),
        ("host", "host", does_not_raise()),
        ("host.cobbler.org", "host.cobbler.org", does_not_raise()),
    ],
)
def test_hostname(input_dnsname, expected_result, expected_exception):
    # Arrange

    # Act
    with expected_exception:
        result = validate.hostname(input_dnsname)

        # Assert
        assert result == expected_result


@pytest.mark.parametrize(
    "input_addr,expected_result,expected_exception",
    [
        ("", "", does_not_raise()),
        ("192.168.1.5", "192.168.1.5", does_not_raise()),
        ("my-invalid-ip", "", pytest.raises(AddressValueError)),
        ("255.255.255.0", "", pytest.raises(NetmaskValueError)),
        (0, "", pytest.raises(TypeError)),
    ],
)
def test_ipv4_address(input_addr, expected_result, expected_exception):
    # Arrange
    # Act
    with expected_exception:
        result = validate.ipv4_address(input_addr)

        # Assert
        assert result == expected_result


def test_validate_os_version():
    # Arrange
    utils.load_signatures("/var/lib/cobbler/distro_signatures.json")

    # Act
    result = validate.validate_os_version("rhel4", "redhat")

    # Assert
    assert result == "rhel4"


def test_validate_breed():
    # Arrange
    utils.load_signatures("/var/lib/cobbler/distro_signatures.json")

    # Act
    result = validate.validate_breed("redhat")

    # Assert
    assert result == "redhat"


def test_set_repos(cobbler_api):
    # Arrange

    # Act
    # TODO: Test this also with the bypass check
    result = validate.validate_repos("testrepo1 testrepo2", cobbler_api, bypass_check=True)

    # Assert
    assert result == ["testrepo1", "testrepo2"]


def test_set_virt_file_size():
    # Arrange

    # Act
    # TODO: Test multiple disks via comma separation
    result = validate.validate_virt_file_size("8")

    # Assert
    assert isinstance(result, float)
    assert result == 8


@pytest.mark.parametrize("test_autoboot,expectation", [
    (True, does_not_raise()),
    (False, does_not_raise()),
    (0, does_not_raise()),
    (1, does_not_raise()),
    (2, does_not_raise()),
    ("Test", does_not_raise())
])
def test_set_virt_auto_boot(test_autoboot, expectation):
    # Arrange

    # Act
    with expectation:
        result = validate.validate_virt_auto_boot(test_autoboot)

        # Assert
        assert isinstance(result, bool)
        assert result is True or result is False


@pytest.mark.parametrize("test_input,expected_exception", [
    (True, does_not_raise()),
    (False, does_not_raise()),
    (0, does_not_raise()),
    (1, does_not_raise()),
    (5, does_not_raise()),
    ("", does_not_raise())
])
def test_set_virt_pxe_boot(test_input, expected_exception):
    # Arrange

    # Act
    with expected_exception:
        result = validate.validate_virt_pxe_boot(test_input)

        # Assert
        assert isinstance(result, bool)
        assert result or not result


def test_set_virt_ram():
    # Arrange

    # Act
    result = validate.validate_virt_ram(1024)

    # Assert
    assert result == 1024


def test_set_virt_bridge():
    # Arrange

    # Act
    result = validate.validate_virt_bridge("testbridge")

    # Assert
    assert result == "testbridge"


def test_validate_virt_path():
    # Arrange
    test_location = "/somerandomfakelocation"

    # Act
    result = validate.validate_virt_path(test_location)

    # Assert
    assert result == test_location


@pytest.mark.parametrize("value,expected_exception", [
    (0, does_not_raise()),
    (5, does_not_raise()),
    (enums.VALUE_INHERITED, does_not_raise()),
    (False, does_not_raise()),
    (0.0, pytest.raises(TypeError)),
    (-5, pytest.raises(ValueError)),
    ("test", pytest.raises(TypeError))
])
def test_set_virt_cpus(value, expected_exception):
    # Arrange

    # Act
    with expected_exception:
        result = validate.validate_virt_cpus(value)

        # Assert
        if value == enums.VALUE_INHERITED:
            assert result == 0
        else:
            assert result == int(value)


def test_set_serial_device():
    # Arrange

    # Act
    result = validate.validate_serial_device(0)

    # Assert
    assert result == 0


def test_set_serial_baud_rate():
    # Arrange

    # Act
    result = validate.validate_serial_baud_rate(9600)

    # Assert
    assert result == enums.BaudRates.B9600


@pytest.mark.parametrize("test_value,expected_result", [
    ("test", False),
    (0, False),
    ("ftp://test/test", False),
    ("http://test_invalid/test", False),
    ("http://test§invalid/test", False),
    ("http://test.local/test", True),
    # ("http://test.local:80/test", True),
    ("http://test/test", True),
    ("http://@@server@@/test", True),
    ("http://10.0.0.1/test", True),
    ("http://fe80::989c:95ff:fe42:47bf/test", True),
])
def test_validate_boot_remote_file(test_value, expected_result):
    # Arrange

    # Act
    result = validate.validate_boot_remote_file(test_value)

    # Assert
    assert expected_result == result


@pytest.mark.parametrize("test_value,expected_result", [
    ("test", False),
    (0, False),
    ("http://test.local/test", False),
    ("http://test/test", False),
    ("ftp://test/test", False),
    # ("(tftp,10.0.0.1:invalid)/test", False),
    # ("(tftp,local_invalid)/test", False),
    ("(http,10.0.0.1)/test", True),
    ("(tftp,10.0.0.1)/test", True),
    ("(tftp,test.local)/test", True),
    ("(tftp,10.0.0.1:8080)/test", True)
])
def test_validate_grub_remote_file(test_value, expected_result):
    # Arrange

    # Act
    result = validate.validate_grub_remote_file(test_value)

    # Assert
    assert expected_result == result


def test_validate_uuid():
    # Arrange
    test_uuid = uuid.uuid4().hex
    expected_result = True

    # Act
    result = validate.validate_uuid(test_uuid)

    # Arrange
    assert result is expected_result
