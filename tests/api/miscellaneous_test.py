"""
Tests that validate the functionality of the module that is responsible for providing miscellaneous API operations.
"""

import logging
from typing import TYPE_CHECKING, Any, Callable
from unittest.mock import create_autospec

import pytest

from cobbler import enums, settings
from cobbler.actions.buildiso.netboot import NetbootBuildiso
from cobbler.actions.buildiso.standalone import StandaloneBuildiso
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System

from tests.conftest import does_not_raise

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    "input_automigration,result_migrate_count,result_validate_count",
    [
        (None, 0, 2),
        (True, 1, 2),
        (False, 0, 2),
    ],
)
def test_settings_migration(
    caplog: pytest.LogCaptureFixture,
    mocker: "MockerFixture",
    input_automigration: bool,
    result_migrate_count: int,
    result_validate_count: int,
):
    # pylint: disable=protected-access
    # Arrange
    caplog.set_level(logging.DEBUG)
    # TODO: Create test where the YAML is missing the key
    spy_migrate = mocker.spy(settings, "migrate")
    spy_validate = mocker.spy(settings, "validate_settings")
    # Override private class variables to have a clean slate on all runs
    CobblerAPI._CobblerAPI__shared_state = {}  # type: ignore[reportAttributeAccessIssue]
    CobblerAPI._CobblerAPI__has_loaded = False  # type: ignore[reportAttributeAccessIssue]

    # Act
    CobblerAPI(execute_settings_automigration=input_automigration)

    # Assert
    assert len(caplog.records) > 0
    if input_automigration is not None:  # type: ignore
        assert (
            'Daemon flag overwriting other possible values from "settings.yaml" for automigration!'
            in caplog.text
        )
    assert spy_migrate.call_count == result_migrate_count
    assert spy_validate.call_count == result_validate_count


def test_buildiso(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    # Arrange
    netboot_stub = create_autospec(spec=NetbootBuildiso)
    standalone_stub = create_autospec(spec=StandaloneBuildiso)
    mocker.patch("cobbler.api.StandaloneBuildiso", return_value=standalone_stub)
    mocker.patch("cobbler.api.NetbootBuildiso", return_value=netboot_stub)

    # Act
    cobbler_api.build_iso()

    # Assert
    assert netboot_stub.run.call_count == 1
    assert standalone_stub.run.call_count == 0


@pytest.mark.parametrize(
    "input_uuid,input_attribute_name,expected_exception,expected_result",
    [
        (0, "", pytest.raises(TypeError), ""),  # Wrong argument type uuid
        ("", 0, pytest.raises(TypeError), ""),  # Wrong argument type attribute name
        (
            "yxvyxcvyxcvyxcvyxcvyxcvyxcv",
            "kernel_options",
            pytest.raises(ValueError),
            "",
        ),  # Wrong uuid format
        (
            "4c1d2e0050344a9ba96e2fd36908a53e",
            "kernel_options",
            pytest.raises(ValueError),
            "",
        ),  # Item not existing
        (
            "",
            "test_not_existing",
            pytest.raises(AttributeError),
            "",
        ),  # Attribute not existing
        ("", "redhat_management_key", does_not_raise(), ""),  # str attribute test
        ("", "redhat_management_org", does_not_raise(), ""),  # str attribute test
        ("", "redhat_management_user", does_not_raise(), ""),  # str attribute test
        ("", "redhat_management_password", does_not_raise(), ""),  # str attribute test
        ("", "enable_ipxe", does_not_raise(), False),  # bool attribute
        ("", "virt_ram", does_not_raise(), 512),  # int attribute
        ("", "virt_file_size", does_not_raise(), 5.0),  # double attribute
        ("", "kernel_options", does_not_raise(), {}),  # dict attribute
        ("", "owners", does_not_raise(), ["admin"]),  # list attribute
    ],
)
def test_get_item_resolved_value(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str], System],
    input_uuid: str,
    input_attribute_name: str,
    expected_exception: Any,
    expected_result: Any,
):
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    test_system = create_system(test_profile.name)

    if input_uuid == "":
        input_uuid = test_system.uid

    # Act
    with expected_exception:
        result = cobbler_api.get_item_resolved_value(input_uuid, input_attribute_name)

        # Assert
        assert expected_result == result


@pytest.mark.parametrize(
    "input_uuid,input_attribute_name,input_value,expected_exception,expected_result",
    [
        (0, "", "", pytest.raises(TypeError), ""),  # Wrong argument type uuid
        ("", 0, "", pytest.raises(TypeError), ""),  # Wrong argument type attribute name
        (
            "yxvyxcvyxcvyxcvyxcvyxcvyxcv",
            "kernel_options",
            "",
            pytest.raises(ValueError),
            "",
        ),  # Wrong uuid format
        (
            "4c1d2e0050344a9ba96e2fd36908a53e",
            "kernel_options",
            "",
            pytest.raises(ValueError),
            "",
        ),  # Item not existing
        (
            "",
            "test_not_existing",
            "",
            pytest.raises(AttributeError),
            "",
        ),  # Attribute not existing
        ("", "redhat_management_key", "", does_not_raise(), ""),  # str attribute test
        ("", "redhat_management_org", "", does_not_raise(), ""),  # str attribute test
        ("", "redhat_management_user", "", does_not_raise(), ""),  # str attribute test
        (
            "",
            "redhat_management_password",
            "",
            does_not_raise(),
            "",
        ),  # str attribute test
        ("", "enable_ipxe", "", does_not_raise(), False),  # bool attribute
        ("", "virt_ram", "", does_not_raise(), 0),  # int attribute
        (
            "",
            "virt_ram",
            enums.VALUE_INHERITED,
            does_not_raise(),
            enums.VALUE_INHERITED,
        ),  # int attribute inherit
        ("", "virt_file_size", "", does_not_raise(), 0.0),  # double attribute
        ("", "kernel_options", "", does_not_raise(), {}),  # dict attribute
        ("", "kernel_options", "a=5", does_not_raise(), {}),  # dict attribute
        ("", "kernel_options", "a=6", does_not_raise(), {"a": "6"}),  # dict attribute
        (
            "",
            "kernel_options",
            enums.VALUE_INHERITED,
            does_not_raise(),
            enums.VALUE_INHERITED,
        ),  # dict attribute
        ("", "owners", "", does_not_raise(), []),  # list attribute
        (
            "",
            "owners",
            enums.VALUE_INHERITED,
            does_not_raise(),
            enums.VALUE_INHERITED,
        ),  # list attribute inherit
        (
            "",
            "name_servers",
            "10.0.0.1",
            does_not_raise(),
            [],
        ),  # list attribute deduplicate
        (
            "",
            "name_servers",
            "10.0.0.1 10.0.0.2",
            does_not_raise(),
            ["10.0.0.2"],
        ),  # list attribute deduplicate
    ],
)
def test_set_item_resolved_value(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str], System],
    input_uuid: str,
    input_attribute_name: str,
    input_value: str,
    expected_exception: Any,
    expected_result: Any,
):
    """
    Verify that setting resolved values works as expected.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    test_profile.kernel_options = "a=5"  # type: ignore
    test_profile.name_servers = ["10.0.0.1"]
    cobbler_api.add_profile(test_profile)
    test_system = create_system(test_profile.name)

    if input_uuid == "":
        input_uuid = test_system.uid

    # Act
    with expected_exception:
        cobbler_api.set_item_resolved_value(
            input_uuid, input_attribute_name, input_value
        )

        # Assert
        assert test_system.to_dict().get(input_attribute_name) == expected_result
