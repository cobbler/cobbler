"""
Test module to verify that manipulation of the Kernel Command Line works as desired.
"""

from cobbler.api import CobblerAPI
from cobbler.utils.kernel_command_line import KernelCommandLine


def test_object_creation(cobbler_api: CobblerAPI):
    """
    Verify that the KernelCommandLine class can be successfully instantiated.
    """
    # Act & Arrange
    result = KernelCommandLine(cobbler_api)

    # Assert
    assert isinstance(result, KernelCommandLine)


def test_append_key_value(cobbler_api: CobblerAPI):
    """
    Verify that a key-value pair can be successfully appended to the Kernel Command Line.
    """
    # Arrange
    test_generator = KernelCommandLine(cobbler_api)
    key = "testkey"
    value = "testvalue"

    # Act
    test_generator.append_key_value(key, value)

    # Assert
    # pylint: disable-next=protected-access
    assert test_generator._KernelCommandLine__append_line == [(key, value)]  # type: ignore


def test_append_key(cobbler_api: CobblerAPI):
    """
    Verify that a keyword-only argument can be successfully appended to the Kernel Command Line.
    """
    # Arrange
    test_generator = KernelCommandLine(cobbler_api)
    key = "testkey"

    # Act
    test_generator.append_key(key)

    # Assert
    # pylint: disable-next=protected-access
    assert test_generator._KernelCommandLine__append_line == [(key,)]  # type: ignore


def test_append_raw(cobbler_api: CobblerAPI):
    """
    Verify that a raw string can be successfully appended to the Kernel Command Line.
    """
    # Arrange
    test_generator = KernelCommandLine(cobbler_api)
    raw_value = "raw=value textmode"

    # Act
    test_generator.append_raw(raw_value)

    # Assert
    # pylint: disable-next=protected-access
    assert test_generator._KernelCommandLine__append_line == [(raw_value,)]  # type: ignore


def test_replace_key(cobbler_api: CobblerAPI):
    """
    Verify that a key can be successfully replaced in the Kernel Command Line.
    """
    # Arrange
    test_generator = KernelCommandLine(cobbler_api)
    test_generator.append_key_value("testkey", "value")
    test_generator.append_key_value("teststays", "value_test")

    # Act
    test_generator.replace_key("testkey", "value", "newvalue")

    # Assert
    # pylint: disable-next=protected-access
    assert test_generator._KernelCommandLine__append_line == [  # type: ignore
        ("testkey", "newvalue"),
        ("teststays", "value_test"),
    ]


def test_render(cobbler_api: CobblerAPI):
    """
    Verify that the render method produces the expected output.
    """
    # Arrange
    test_generator = KernelCommandLine(cobbler_api)

    # Act
    result = test_generator.render({})

    # Assert
    assert result == ""
