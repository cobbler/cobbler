"""
Tests that validate the functionality of the module that is responsible for providing XML-RPC calls related to
input conversion.
"""

from typing import Any, Dict, List

import pytest

from cobbler.remote import CobblerXMLRPCInterface

from tests.conftest import does_not_raise


@pytest.mark.parametrize(
    "input_options,expected_result,expected_exception", [([], [], does_not_raise())]
)
def test_input_string_or_list_no_inherit(
    remote: CobblerXMLRPCInterface,
    input_options: List[str],
    expected_result: List[str],
    expected_exception: Any,
):
    """
    Test: check Cobbler status
    """
    # Arrange & Act
    with expected_exception:
        result = remote.input_string_or_list_no_inherit(input_options)

        # Assert
        assert result == expected_result


@pytest.mark.parametrize(
    "test_input,expected_result,expected_excpetion",
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
    remote: CobblerXMLRPCInterface,
    test_input: Any,
    expected_result: Any,
    expected_excpetion: Any,
):
    """
    Test: check Cobbler status
    """
    # Arrange & Act
    with expected_excpetion:
        result = remote.input_string_or_list(test_input)

        # Assert
        assert result == expected_result


@pytest.mark.parametrize(
    "testinput,expected_result,possible_exception",
    [
        ("<<inherit>>", "<<inherit>>", does_not_raise()),
        ([""], None, pytest.raises(TypeError)),
        ("a b=10 c=abc", {"a": None, "b": "10", "c": "abc"}, does_not_raise()),
        ({"ab": 0}, {"ab": 0}, does_not_raise()),
        (0, None, pytest.raises(TypeError)),
    ],
)
def test_input_string_or_dict(
    remote: CobblerXMLRPCInterface,
    testinput: Any,
    expected_result: Any,
    possible_exception: Any,
):
    """
    Test: check Cobbler status
    """
    # Arrange & Act
    with possible_exception:
        result = remote.input_string_or_dict(testinput)

        # Assert
        assert result == expected_result


@pytest.mark.parametrize(
    "input_options,input_allow_multiples,expected_result,expected_exception",
    [({}, True, {}, does_not_raise())],
)
def test_input_string_or_dict_no_inherit(
    remote: CobblerXMLRPCInterface,
    input_options: Dict[str, str],
    input_allow_multiples: bool,
    expected_result: Dict[str, str],
    expected_exception: Any,
):
    """
    Test: check Cobbler status
    """
    # Arrange & Act
    with expected_exception:
        result = remote.input_string_or_dict_no_inherit(
            input_options, allow_multiples=input_allow_multiples
        )

        # Assert
        assert result == expected_result


@pytest.mark.parametrize(
    "testinput,expected_exception,expected_result",
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
    remote: CobblerXMLRPCInterface,
    testinput: Any,
    expected_exception: Any,
    expected_result: bool,
):
    """
    Test: check Cobbler status
    """
    # Arrange & Act
    with expected_exception:
        result = remote.input_boolean(testinput)

        # Assert
        assert result == expected_result


@pytest.mark.parametrize(
    "testinput,expected_exception,expected_result",
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
    remote: CobblerXMLRPCInterface,
    testinput: Any,
    expected_exception: Any,
    expected_result: int,
):
    """
    Test: check Cobbler status
    """
    # Arrange & Act
    with expected_exception:
        result = remote.input_int(testinput)

        # Assert
        assert result == expected_result
