import pytest

from cobbler.utils import input_converters

from tests.conftest import does_not_raise


@pytest.mark.parametrize(
    "test_input,expected_result,expected_exception",
    [
        ("<<inherit>>", "<<inherit>>", does_not_raise()),
        ("delete", [], does_not_raise()),
        (["test"], ["test"], does_not_raise()),
        ("my_test", ["my_test"], does_not_raise()),
        ("my_test my_test", ["my_test", "my_test"], does_not_raise()),
        (5, None, pytest.raises(TypeError)),
    ],
)
def test_input_string_or_list(test_input, expected_result, expected_exception):
    # Arrange & Act
    with expected_exception:
        result = input_converters.input_string_or_list(test_input)

        # Assert
        assert expected_result == result


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
def test_input_string_or_dict(testinput, expected_result, possible_exception):
    # Arrange

    # Act
    with possible_exception:
        result = input_converters.input_string_or_dict(testinput)

        # Assert
        assert expected_result == result


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
def test_input_boolean(testinput, expected_exception, expected_result):
    # Arrange

    # Act
    with expected_exception:
        result = input_converters.input_boolean(testinput)

        # Assert
        assert expected_result == result


@pytest.mark.parametrize(
    "testinput,expected_exception,expected_result",
    [
        (None, pytest.raises(TypeError), 1),
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
def test_input_int(testinput, expected_exception, expected_result):
    # Arrange --> Not needed

    # Act
    with expected_exception:
        result = input_converters.input_int(testinput)

        # Assert
        assert expected_result == result
