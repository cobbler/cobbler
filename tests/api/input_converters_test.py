"""
Tests that validate the functionality of the module that is responsible for providing the API for input conversion.
"""

from typing import Any, Dict, List, Optional, Union

import pytest

from cobbler.api import CobblerAPI

from tests.conftest import does_not_raise


@pytest.mark.parametrize(
    "input_options,expected_result,expected_exception", [([], [], does_not_raise())]
)
def test_input_string_or_list_no_inherit(
    cobbler_api: CobblerAPI,
    input_options: List[str],
    expected_result: List[str],
    expected_exception: Any,
):
    # Arrange & Act
    with expected_exception:
        result = cobbler_api.input_string_or_list_no_inherit(input_options)

        # Assert
        assert result == expected_result


@pytest.mark.parametrize(
    "input_options,expected_result,expected_exception",
    [
        ("<<inherit>>", "<<inherit>>", does_not_raise()),
        ("delete", [], does_not_raise()),
        (["test"], ["test"], does_not_raise()),
        ("my_test", ["my_test"], does_not_raise()),
        ("my_test my_test", ["my_test", "my_test"], does_not_raise()),
        (5, None, pytest.raises(TypeError)),
    ],
)
def test_input_string_or_list(
    cobbler_api: CobblerAPI,
    input_options: Any,
    expected_result: Optional[Union[str, List[str]]],
    expected_exception: Any,
):
    # Arrange & Act
    with expected_exception:
        result = cobbler_api.input_string_or_list(input_options)

        # Assert
        assert result == expected_result


@pytest.mark.parametrize(
    "input_options,input_allow_multiples,expected_result,possible_exception",
    [
        ("<<inherit>>", True, "<<inherit>>", does_not_raise()),
        ([""], True, None, pytest.raises(TypeError)),
        ("a b=10 c=abc", True, {"a": None, "b": "10", "c": "abc"}, does_not_raise()),
        ({"ab": 0}, True, {"ab": 0}, does_not_raise()),
        (0, True, None, pytest.raises(TypeError)),
    ],
)
def test_input_string_or_dict(
    cobbler_api: CobblerAPI,
    input_options: Any,
    input_allow_multiples: bool,
    expected_result: Union[str, Dict[str, Any]],
    possible_exception: Any,
):
    # Arrange & Act
    with possible_exception:
        result = cobbler_api.input_string_or_dict(
            input_options, allow_multiples=input_allow_multiples
        )

        # Assert
        assert result == expected_result


@pytest.mark.parametrize(
    "input_options,input_allow_multiples,expected_result,expected_exception",
    [({}, True, {}, does_not_raise())],
)
def test_input_string_or_dict_no_inherit(
    cobbler_api: CobblerAPI,
    input_options: Dict[str, Any],
    input_allow_multiples: bool,
    expected_result: Dict[str, Any],
    expected_exception: Any,
):
    # Arrange & Act
    with expected_exception:
        result = cobbler_api.input_string_or_dict_no_inherit(
            input_options, allow_multiples=input_allow_multiples
        )

        # Assert
        assert result == expected_result


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_result",
    [
        (True, does_not_raise(), True),
        (1, does_not_raise(), True),
        ("oN", does_not_raise(), True),
        ("yEs", does_not_raise(), True),
        ("Y", does_not_raise(), True),
        ("Test", does_not_raise(), False),
        (-5, does_not_raise(), False),
        (0.5, pytest.raises(TypeError), False),
    ],
)
def test_input_boolean(
    cobbler_api: CobblerAPI,
    input_value: Any,
    expected_exception: Any,
    expected_result: bool,
):
    # Arrange & Act
    with expected_exception:
        result = cobbler_api.input_boolean(input_value)

        # Assert
        assert result == expected_result


@pytest.mark.parametrize(
    "input_value,expected_exception,expected_result",
    [
        (True, does_not_raise(), 1),
        (1, does_not_raise(), 1),
        ("1", does_not_raise(), 1),
        ("text", pytest.raises(TypeError), 1),
        ("5.0", pytest.raises(TypeError), 0),
        ([], pytest.raises(TypeError), 0),
        ({}, pytest.raises(TypeError), 0),
        (-5, does_not_raise(), -5),
        (0.5, does_not_raise(), 0),
    ],
)
def test_input_int(
    cobbler_api: CobblerAPI,
    input_value: Any,
    expected_exception: Any,
    expected_result: int,
):
    # Arrange & Act
    with expected_exception:
        result = cobbler_api.input_int(input_value)

        # Assert
        assert result == expected_result
