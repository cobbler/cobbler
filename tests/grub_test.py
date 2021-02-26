import pytest

from cobbler import grub
from tests.conftest import does_not_raise


@pytest.mark.parametrize("input_file_location,expected_output,expected_exception", [
    (None, None, pytest.raises(TypeError)),
    ("ftp://testuri", None, does_not_raise()),
    ("http://testuri", None, pytest.raises(ValueError)),
    ("tftp://testuri", None, pytest.raises(ValueError)),
    ("wss://testuri", None, does_not_raise()),
    ("http://10.0.0.1", "(http,10.0.0.1)/", does_not_raise()),
    ("tftp://10.0.0.1", "(tftp,10.0.0.1)/", does_not_raise()),
    ("tftp://10.0.0.1/testpath/testpath/", "(tftp,10.0.0.1)/testpath/testpath/", does_not_raise()),
])
def test_parse_grub_remote_file(input_file_location, expected_output, expected_exception):
    # Arrange & Act
    with expected_exception:
        result = grub.parse_grub_remote_file(input_file_location)

        # Assert
        assert result == expected_output
