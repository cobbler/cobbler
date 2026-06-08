"""
Tests that validate the functionality of the module that is responsible for validating data before it is consumed by
the application.
"""

import uuid
from ipaddress import AddressValueError, NetmaskValueError
from typing import Any

import pytest

from cobbler import enums, validate
from cobbler.api import CobblerAPI
from cobbler.utils import signatures

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
def test_hostname(input_dnsname: Any, expected_result: str, expected_exception: Any):
    """
    Test to verify if a given datapoint can be validated as a hostname.
    """
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
def test_ipv4_address(input_addr: Any, expected_result: str, expected_exception: Any):
    """
    Test to verify if a given datapoint can be validated as an IPv4 address.
    """
    # Arrange
    # Act
    with expected_exception:
        result = validate.ipv4_address(input_addr)

        # Assert
        assert result == expected_result


def test_validate_os_version():
    """
    Test to verify if a given datapoint can be validated as an OS version.
    """
    # Arrange
    signatures.load_signatures("/var/lib/cobbler/distro_signatures.json")

    # Act
    result = validate.validate_os_version("rhel4", "redhat")

    # Assert
    assert result == "rhel4"


def test_validate_breed():
    """
    Test to validate if a given datapoint can be validated as an operating system breed.
    """
    # Arrange
    signatures.load_signatures("/var/lib/cobbler/distro_signatures.json")

    # Act
    result = validate.validate_breed("redhat")

    # Assert
    assert result == "redhat"


def test_set_repos(cobbler_api: CobblerAPI):
    """
    Test to validate if a given datapoint can be validated as a list of repositories.
    """
    # Arrange

    # Act
    # TODO: Test this also with the bypass check
    result = validate.validate_repos(
        "testrepo1 testrepo2", cobbler_api, bypass_check=True
    )

    # Assert
    assert result == ["testrepo1", "testrepo2"]


def test_set_virt_file_size():
    """
    Test to validate if a given datapoint can be validated as a virtual disk size.
    """
    # Arrange

    # Act
    # TODO: Test multiple disks via comma separation
    result = validate.validate_virt_file_size("8")

    # Assert
    assert isinstance(result, float)
    assert result == 8


@pytest.mark.parametrize(
    "test_autoboot,expectation",
    [
        (True, does_not_raise()),
        (False, does_not_raise()),
        (0, does_not_raise()),
        (1, does_not_raise()),
        (2, does_not_raise()),
        ("Test", does_not_raise()),
    ],
)
def test_set_virt_auto_boot(test_autoboot: Any, expectation: Any):
    """
    Test to validate if a given datapoint can be validated as a boolean or string for the virt_auto_boot setting.
    """
    # Arrange

    # Act
    with expectation:
        result = validate.validate_virt_auto_boot(test_autoboot)

        # Assert
        assert isinstance(result, bool)
        assert result is True or result is False


@pytest.mark.parametrize(
    "test_input,expected_exception",
    [
        (True, does_not_raise()),
        (False, does_not_raise()),
        (0, does_not_raise()),
        (1, does_not_raise()),
        (5, does_not_raise()),
        ("", does_not_raise()),
    ],
)
def test_set_virt_pxe_boot(test_input: Any, expected_exception: Any):
    """
    Test to validate if a given datapoint can be validated as a boolean or integer for the virt_pxe_boot setting.
    """
    # Arrange

    # Act
    with expected_exception:
        result = validate.validate_virt_pxe_boot(test_input)

        # Assert
        assert isinstance(result, bool)
        assert result or not result


def test_set_virt_ram():
    """
    Test to validate if a given datapoint can be validated as an integer for the virt_ram setting.
    """
    # Arrange

    # Act
    result = validate.validate_virt_ram(1024)

    # Assert
    assert result == 1024


def test_set_virt_bridge():
    """
    Test to validate if a given datapoint can be validated as a string for the virt_bridge setting.
    """
    # Arrange

    # Act
    result = validate.validate_virt_bridge("testbridge")

    # Assert
    assert result == "testbridge"


def test_validate_virt_path():
    """
    Test to validate if a given datapoint can be validated as a string for the virt_path setting.
    """
    # Arrange
    test_location = "/somerandomfakelocation"

    # Act
    result = validate.validate_virt_path(test_location)

    # Assert
    assert result == test_location


@pytest.mark.parametrize(
    "value,expected_exception",
    [
        (0, does_not_raise()),
        (5, does_not_raise()),
        (enums.VALUE_INHERITED, does_not_raise()),
        (False, does_not_raise()),
        (0.0, pytest.raises(TypeError)),
        (-5, pytest.raises(ValueError)),
        ("test", pytest.raises(TypeError)),
    ],
)
def test_set_virt_cpus(value: Any, expected_exception: Any):
    """
    Test to validate if a given datapoint can be validated as an integer for the virt_cpus setting.
    """
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
    """
    Test to validate if a given datapoint can be validated for the serial_device setting.
    """
    # Arrange

    # Act
    result = validate.validate_serial_device(0)

    # Assert
    assert result == 0


def test_set_serial_baud_rate():
    """
    Test to validate if a given datapoint can be validated for the serial_baud_rate setting.
    """
    # Arrange

    # Act
    result = validate.validate_serial_baud_rate(9600)

    # Assert
    assert result == enums.BaudRates.B9600


@pytest.mark.parametrize(
    "test_value,expected_result",
    [
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
    ],
)
def test_validate_boot_remote_file(test_value: Any, expected_result: bool):
    """
    Test to validate if a given datapoint can be validated as a remote file URL for boot files.
    """
    # Arrange

    # Act
    result = validate.validate_boot_remote_file(test_value)

    # Assert
    assert expected_result == result


@pytest.mark.parametrize(
    "test_value,expected_result",
    [
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
        ("(tftp,10.0.0.1:8080)/test", True),
    ],
)
def test_validate_grub_remote_file(test_value: Any, expected_result: bool):
    """
    Test to validate if a given datapoint can be validated as a remote file URL for GRUB files.
    """
    # Arrange

    # Act
    result = validate.validate_grub_remote_file(test_value)

    # Assert
    assert expected_result == result


def test_validate_uuid():
    """
    Test to validate if a given datapoint can be validated as a UUID.
    """
    # Arrange
    test_uuid = uuid.uuid4().hex
    expected_result = True

    # Act
    result = validate.validate_uuid(test_uuid)

    # Arrange
    assert result is expected_result


@pytest.mark.parametrize(
    "input_dnsname,allow_trailing,expected_result,expected_exception",
    [
        ("", False, "", does_not_raise()),
        ("host", False, "host", does_not_raise()),
        ("host.cobbler.org", False, "host.cobbler.org", does_not_raise()),
        (
            "host.cobbler.org.",
            False,
            "",
            pytest.raises(ValueError),
        ),  # Trailing dot rejected
        ("example..", False, "", pytest.raises(ValueError)),  # Double dot
        (".example", False, "", pytest.raises(ValueError)),  # Leading dot
        ("host-name", False, "host-name", does_not_raise()),  # Hyphens OK
        (0, False, "", pytest.raises(TypeError)),  # Type check
    ],
)
def test_hostname_trailing_dot_variants(
    input_dnsname: Any,
    allow_trailing: bool,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test hostname validation with default behavior (no trailing dots allowed).
    """
    # Arrange & Act
    with expected_exception:
        result = validate.hostname(input_dnsname, allow_trailing_dot=allow_trailing)
        # Assert
        assert result == expected_result


@pytest.mark.parametrize(
    "input_dnsname,expected_result,expected_exception",
    [
        ("host.cobbler.org.", "host.cobbler.org.", does_not_raise()),
        ("example.com.", "example.com.", does_not_raise()),
        ("sub.example.com.", "sub.example.com.", does_not_raise()),
        ("example.com", "example.com", does_not_raise()),  # Still optional
        (
            "localhost.",
            "localhost.",
            does_not_raise(),
        ),  # Single label with trailing dot
        ("example..", "", pytest.raises(ValueError)),  # Double dot still fails
        (".example", "", pytest.raises(ValueError)),  # Leading dot still fails
        (".", "", pytest.raises(ValueError)),  # Just a dot is invalid
    ],
)
def test_hostname_allow_trailing_dot(
    input_dnsname: Any,
    expected_result: str,
    expected_exception: Any,
):
    """
    Test hostname validation with trailing dots allowed.
    """
    # Arrange & Act
    with expected_exception:
        result = validate.hostname(input_dnsname, allow_trailing_dot=True)
        # Assert
        assert result == expected_result


@pytest.mark.parametrize(
    "input_search,expected_result,expected_exception",
    [
        ([], [], does_not_raise()),
        (["example.com"], ["example.com"], does_not_raise()),
        (["example.com."], ["example.com."], does_not_raise()),  # Trailing dot
        (
            ["example.com", "internal.local."],
            ["example.com", "internal.local."],
            does_not_raise(),
        ),  # Mixed
        (
            "example.com example.org.",
            ["example.com", "example.org."],
            does_not_raise(),
        ),  # String input
        (["sub.domain.example.com."], ["sub.domain.example.com."], does_not_raise()),
        (["example.."], [], pytest.raises(ValueError)),  # Malformed
        ([".example"], [], pytest.raises(ValueError)),  # Leading dot
    ],
)
def test_name_servers_search_trailing_dot(
    input_search: Any,
    expected_result: Any,
    expected_exception: Any,
):
    """
    Test name_servers_search validation with trailing dots allowed.
    """
    # Arrange & Act
    with expected_exception:
        result = validate.name_servers_search(input_search, for_item=False)
        # Assert
        assert result == expected_result
