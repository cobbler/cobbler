import logging
from unittest.mock import create_autospec

import pytest

from cobbler import enums
from cobbler import settings
from cobbler.api import CobblerAPI
from cobbler.actions.buildiso.netboot import NetbootBuildiso
from cobbler.actions.buildiso.standalone import StandaloneBuildiso
from tests.conftest import does_not_raise


@pytest.mark.parametrize("input_automigration,result_migrate_count,result_validate_count", [
    (None, 0, 2),
    (True, 1, 2),
    (False, 0, 2),
])
def test_settings_migration(caplog, mocker, input_automigration, result_migrate_count, result_validate_count):
    # Arrange
    caplog.set_level(logging.DEBUG)
    # TODO: Create test where the YAML is missing the key
    spy_migrate = mocker.spy(settings, "migrate")
    spy_validate = mocker.spy(settings, "validate_settings")
    # Override private class variables to have a clean slate on all runs
    CobblerAPI._CobblerAPI__shared_state = {}
    CobblerAPI._CobblerAPI__has_loaded = False

    # Act
    CobblerAPI(execute_settings_automigration=input_automigration)

    # Assert
    assert len(caplog.records) > 0
    if input_automigration is not None:
        assert 'Daemon flag overwriting other possible values from "settings.yaml" for automigration!' in caplog.text
    assert spy_migrate.call_count == result_migrate_count
    assert spy_validate.call_count == result_validate_count


def test_buildiso(mocker, cobbler_api):
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
        ("", "enable_ipxe", does_not_raise(), False),  # bool attribute
        ("", "virt_ram", does_not_raise(), 512),  # int attribute
        ("", "virt_file_size", does_not_raise(), 5.0),  # double attribute
        ("", "kernel_options", does_not_raise(), {}),  # dict attribute
        ("", "owners", does_not_raise(), ["admin"]),  # list attribute
    ],
)
def test_get_item_resolved_value(
    cobbler_api,
    create_distro,
    create_profile,
    create_system,
    input_uuid,
    input_attribute_name,
    expected_exception,
    expected_result,
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
    ],
)
def test_set_item_resolved_value(
    cobbler_api,
    create_distro,
    create_profile,
    create_system,
    input_uuid,
    input_attribute_name,
    input_value,
    expected_exception,
    expected_result,
):
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    test_profile.kernel_options = "a=5"
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
