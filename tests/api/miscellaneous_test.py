"""
Tests that validate the functionality of the module that is responsible for providing miscellaneous API operations.
"""

import logging
from typing import TYPE_CHECKING, Any, Callable, List
from unittest.mock import create_autospec

import pytest

from cobbler import enums, settings
from cobbler.actions.buildiso.netboot import NetbootBuildiso
from cobbler.actions.buildiso.standalone import StandaloneBuildiso
from cobbler.api import CobblerAPI
from cobbler.cobbler_collections.templates import Templates
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
    """
    Verify that executing the automigrations with a combination of values works as expected.
    """
    # pylint: disable=protected-access
    # Arrange
    caplog.set_level(logging.DEBUG)
    # TODO: Create test where the YAML is missing the key
    spy_migrate = mocker.spy(settings, "migrate")
    spy_validate = mocker.spy(settings, "validate_settings")
    # Override private class variables to have a clean slate on all runs
    CobblerAPI._CobblerAPI__shared_state = {}  # type: ignore[reportAttributeAccessIssue,attr-defined]
    CobblerAPI._CobblerAPI__has_loaded = False  # type: ignore[reportAttributeAccessIssue,attr-defined]

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
    """
    Verify that the API calls the buildiso classes with the correct arguments.
    """
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
            ["kernel_options"],
            pytest.raises(ValueError),
            "",
        ),  # Wrong uuid format
        (
            "4c1d2e0050344a9ba96e2fd36908a53e",
            ["kernel_options"],
            pytest.raises(ValueError),
            "",
        ),  # Item not existing
        (
            "",
            ["test_not_existing"],
            pytest.raises(AttributeError),
            "",
        ),  # Attribute not existing
        ("", ["redhat_management_key"], does_not_raise(), ""),  # str attribute test
        ("", ["enable_ipxe"], does_not_raise(), False),  # bool attribute
        ("", ["virt", "ram"], does_not_raise(), 512),  # int attribute
        ("", ["virt", "file_size"], does_not_raise(), 5.0),  # double attribute
        ("", ["kernel_options"], does_not_raise(), {}),  # dict attribute
        ("", ["owners"], does_not_raise(), ["admin"]),  # list attribute
    ],
)
def test_get_item_resolved_value(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str], System],
    input_uuid: str,
    input_attribute_name: List[str],
    expected_exception: Any,
    expected_result: Any,
):
    """
    Verify that getting resolved values works as expected.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(test_profile.uid)

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
            ["kernel_options"],
            "",
            pytest.raises(ValueError),
            "",
        ),  # Wrong uuid format
        (
            "4c1d2e0050344a9ba96e2fd36908a53e",
            ["kernel_options"],
            "",
            pytest.raises(ValueError),
            "",
        ),  # Item not existing
        (
            "",
            ["test_not_existing"],
            "",
            pytest.raises(AttributeError),
            "",
        ),  # Attribute not existing
        ("", ["redhat_management_key"], "", does_not_raise(), ""),  # str attribute test
        ("", ["enable_ipxe"], "", does_not_raise(), False),  # bool attribute
        ("", ["virt", "ram"], "", does_not_raise(), 0),  # int attribute
        (
            "",
            ["virt", "ram"],
            enums.VALUE_INHERITED,
            does_not_raise(),
            enums.VALUE_INHERITED,
        ),  # int attribute inherit
        ("", ["virt", "file_size"], "", does_not_raise(), 0.0),  # double attribute
        ("", ["kernel_options"], "", does_not_raise(), {}),  # dict attribute
        ("", ["kernel_options"], "a=5", does_not_raise(), {}),  # dict attribute
        ("", ["kernel_options"], "a=6", does_not_raise(), {"a": "6"}),  # dict attribute
        (
            "",
            ["kernel_options"],
            enums.VALUE_INHERITED,
            does_not_raise(),
            enums.VALUE_INHERITED,
        ),  # dict attribute
        ("", ["owners"], "", does_not_raise(), []),  # list attribute
        (
            "",
            ["owners"],
            enums.VALUE_INHERITED,
            does_not_raise(),
            enums.VALUE_INHERITED,
        ),  # list attribute inherit
        (
            "",
            ["dns", "name_servers"],
            "10.0.0.1",
            does_not_raise(),
            [],
        ),  # list attribute deduplicate
        (
            "",
            ["dns", "name_servers"],
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
    input_attribute_name: List[str],
    input_value: str,
    expected_exception: Any,
    expected_result: Any,
):
    """
    Verify that setting resolved values works as expected.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.kernel_options = "a=5"  # type: ignore
    test_profile.dns.name_servers = ["10.0.0.1"]  # type: ignore[method-assign]
    cobbler_api.add_profile(test_profile)
    test_system = create_system(test_profile.uid)

    if input_uuid == "":
        input_uuid = test_system.uid

    # Act
    with expected_exception:
        cobbler_api.set_item_resolved_value(
            input_uuid, input_attribute_name, input_value
        )

        # Assert
        system_result = test_system.to_dict()
        for item in input_attribute_name:
            system_result = system_result.get(item)  # type: ignore
        assert system_result == expected_result


def test_templates_refresh_content_none(
    mocker: "MockerFixture", cobbler_api: CobblerAPI
):
    """
    TODO
    """
    # Arrange
    # pylint: disable=protected-access
    refresh_content_spy = mocker.patch.object(
        Templates,
        "refresh_content",
        wraps=cobbler_api._collection_mgr.templates().refresh_content,  # pyright: ignore [reportPrivateUsage]
    )
    # pylint: enable=protected-access

    # Act
    cobbler_api.templates_refresh_content(None)

    # Assert
    refresh_content_spy.assert_called_once()


def test_templates_refresh_content_objs(
    mocker: "MockerFixture", cobbler_api: CobblerAPI
):
    """
    Test to verify that templates can be successfully refreshed.
    """
    # Arrange
    object_list = cobbler_api.find_template(True, False, name="built-in-preseed_*")
    if object_list is None or not isinstance(object_list, list):
        pytest.fail("Search result for templates was of incorrect type!")

    spy_list = [
        mocker.patch.object(obj, "refresh_content", wraps=obj.refresh_content)
        for obj in object_list
    ]

    # Act
    cobbler_api.templates_refresh_content(object_list)

    # Assert
    for spy in spy_list:
        spy.assert_called_once()
