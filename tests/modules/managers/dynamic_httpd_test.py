"""
Tests that validate the functionality of the module that serves as a marker for the dynamic (non-copying)
HTTP-serving mode.
"""

from typing import TYPE_CHECKING, Any, Generator

import pytest

from cobbler.modules.managers import dynamic_httpd

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="reset_singleton", scope="function", autouse=True)
def fixture_reset_singleton() -> Generator[Any, Any, Any]:
    """
    Fixture to reset the singleton instance of _DynamicHttpdManager before and after each test.
    """
    dynamic_httpd.MANAGER = None
    yield
    dynamic_httpd.MANAGER = None


def test_register():
    """
    Test the register function to ensure it returns the expected string.
    """
    # Arrange & Act
    result = dynamic_httpd.register()

    # Assert
    assert result == "manage"


def test_manager_what():
    """
    Test the what method of the _DynamicHttpdManager class to ensure it returns the expected string.
    """
    # pylint: disable=protected-access
    # Arrange & Act & Assert
    assert dynamic_httpd._DynamicHttpdManager.what() == "dynamic_httpd"  # type: ignore[reportPrivateUsage]


def test_dynamic_httpd_singleton(mocker: "MockerFixture"):
    """
    Test to ensure that the _DynamicHttpdManager class implements the singleton pattern correctly.
    """
    # Arrange
    mcollection = mocker.Mock()

    # Act
    manager_1 = dynamic_httpd.get_manager(mcollection)
    manager_2 = dynamic_httpd.get_manager(mcollection)

    # Assert
    assert manager_1 == manager_2
