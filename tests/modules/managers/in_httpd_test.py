"""
Tests that validate the functionality of the module that is responsible for the default (copying) HTTP-serving
mode.
"""

from typing import TYPE_CHECKING, Any, Generator

import pytest

from cobbler.modules.managers import in_httpd

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="reset_singleton", scope="function", autouse=True)
def fixture_reset_singleton() -> Generator[Any, Any, Any]:
    """
    Fixture to reset the singleton instance of _InHttpdManager before and after each test.
    """
    in_httpd.MANAGER = None
    yield
    in_httpd.MANAGER = None


def test_register():
    """
    Test the register function to ensure it returns the expected string.
    """
    # Arrange & Act
    result = in_httpd.register()

    # Assert
    assert result == "manage"


def test_manager_what():
    """
    Test the what method of the _InHttpdManager class to ensure it returns the expected string.
    """
    # pylint: disable=protected-access
    # Arrange & Act & Assert
    assert in_httpd._InHttpdManager.what() == "in_httpd"  # type: ignore[reportPrivateUsage]


def test_in_httpd_singleton(mocker: "MockerFixture"):
    """
    Test to ensure that the _InHttpdManager class implements the singleton pattern correctly.
    """
    # Arrange
    mcollection = mocker.Mock()

    # Act
    manager_1 = in_httpd.get_manager(mcollection)
    manager_2 = in_httpd.get_manager(mcollection)

    # Assert
    assert manager_1 == manager_2
