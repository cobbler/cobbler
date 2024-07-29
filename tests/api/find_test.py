"""
Tests that validate the functionality of the module that is responsible for providing the search API for the
application.
"""

from typing import Any, Dict, Optional

import pytest

from cobbler.api import CobblerAPI

from tests.conftest import does_not_raise


@pytest.fixture(name="find_fillup")
def fixture_find_fillup(cobbler_api: CobblerAPI):
    # TODO: Extend the fillup and add more testcases
    return cobbler_api


@pytest.mark.parametrize(
    "what,criteria,name,return_list,no_errors,expected_exception,expected_result",
    [
        ("", None, "test", False, False, does_not_raise(), None),
        ("", None, "", False, False, pytest.raises(ValueError), None),
        ("distro", {}, "test", False, False, does_not_raise(), None),
        ("distro", {}, "", False, False, pytest.raises(ValueError), None),
    ],
)
def test_find_items(
    find_fillup: CobblerAPI,
    what: str,
    criteria: Dict[str, Any],
    name: str,
    return_list: bool,
    no_errors: bool,
    expected_exception: Any,
    expected_result: None,
):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_items(what, criteria, name, return_list, no_errors)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "name,return_list,no_errors,criteria,expected_exception,expected_result",
    [
        (None, False, False, {}, pytest.raises(ValueError), None),
        ("testdistro", False, False, {}, does_not_raise(), None),
    ],
)
def test_find_distro(
    find_fillup: CobblerAPI,
    name: Optional[str],
    return_list: bool,
    no_errors: bool,
    criteria: Dict[str, Any],
    expected_exception: Any,
    expected_result: None,
):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_distro(name, return_list, no_errors, **criteria)  # type: ignore[reportArgumentType]

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "name,return_list,no_errors,criteria,expected_exception,expected_result",
    [
        (None, False, False, {}, pytest.raises(ValueError), None),
        ("testdistro", False, False, {}, does_not_raise(), None),
    ],
)
def test_find_profile(
    find_fillup: CobblerAPI,
    name: Optional[str],
    return_list: bool,
    no_errors: bool,
    criteria: Dict[str, Any],
    expected_exception: Any,
    expected_result: None,
):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_profile(name, return_list, no_errors, **criteria)  # type: ignore[reportArgumentType]

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "name,return_list,no_errors,criteria,expected_exception,expected_result",
    [
        (None, False, False, {}, pytest.raises(ValueError), None),
        ("testdistro", False, False, {}, does_not_raise(), None),
    ],
)
def test_find_system(
    find_fillup: CobblerAPI,
    name: Optional[str],
    return_list: bool,
    no_errors: bool,
    criteria: Dict[str, Any],
    expected_exception: Any,
    expected_result: None,
):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_system(name, return_list, no_errors, **criteria)  # type: ignore[reportArgumentType]

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "name,return_list,no_errors,criteria,expected_exception,expected_result",
    [
        (None, False, False, {}, pytest.raises(ValueError), None),
        ("testdistro", False, False, {}, does_not_raise(), None),
    ],
)
def test_find_repo(
    find_fillup: CobblerAPI,
    name: Optional[str],
    return_list: bool,
    no_errors: bool,
    criteria: Dict[str, Any],
    expected_exception: Any,
    expected_result: None,
):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_repo(name, return_list, no_errors, **criteria)  # type: ignore[reportArgumentType]

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "name,return_list,no_errors,criteria,expected_exception,expected_result",
    [
        (None, False, False, {}, pytest.raises(ValueError), None),
        ("testdistro", False, False, {}, does_not_raise(), None),
    ],
)
def test_find_image(
    find_fillup: CobblerAPI,
    name: Optional[str],
    return_list: bool,
    no_errors: bool,
    criteria: Optional[Dict[str, Any]],
    expected_exception: Any,
    expected_result: None,
):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_image(name, return_list, no_errors, **criteria)  # type: ignore[reportArgumentType]

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "name,return_list,no_errors,criteria,expected_exception,expected_result",
    [
        ("", False, False, {}, pytest.raises(ValueError), None),
        ("test", False, False, {}, does_not_raise(), None),
        (None, False, False, None, pytest.raises(ValueError), None),
        ("testdistro", False, False, {}, does_not_raise(), None),
    ],
)
def test_find_menu(
    find_fillup: CobblerAPI,
    name: Optional[str],
    return_list: bool,
    no_errors: bool,
    criteria: Optional[Dict[str, Any]],
    expected_exception: Any,
    expected_result: None,
):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        if criteria is not None:
            result = test_api.find_menu(name, return_list, no_errors, **criteria)  # type: ignore[reportArgumentType]
        else:
            result = test_api.find_menu(name, return_list, no_errors)  # type: ignore[reportArgumentType]

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result
