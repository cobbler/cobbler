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
    """
    Fixture to allow to create items to find for the tests.
    """
    # TODO: Extend the fillup and add more testcases
    return cobbler_api


@pytest.mark.parametrize(
    "what,criteria,return_list,no_errors,expected_exception,expected_result",
    [
        ("", None, False, False, pytest.raises(ValueError), None),
        ("distro", {"name": "test"}, False, False, does_not_raise(), None),
        ("distro", {}, False, False, pytest.raises(ValueError), None),
    ],
)
def test_find_items(
    find_fillup: CobblerAPI,
    what: str,
    criteria: Dict[str, Any],
    return_list: bool,
    no_errors: bool,
    expected_exception: Any,
    expected_result: None,
):
    """
    Test to verify that items can be found with and without given collections.
    """
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_items(what, criteria, return_list, no_errors)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "return_list,no_errors,criteria,expected_exception,expected_result",
    [
        (False, False, {}, pytest.raises(ValueError), None),
        (False, False, {"name": "testdistro"}, does_not_raise(), None),
    ],
)
def test_find_distro(
    find_fillup: CobblerAPI,
    return_list: bool,
    no_errors: bool,
    criteria: Dict[str, Any],
    expected_exception: Any,
    expected_result: None,
):
    """
    Test to verify that distros can be searched for.
    """
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_distro(return_list, no_errors, **criteria)  # type: ignore[reportArgumentType]

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "return_list,no_errors,criteria,expected_exception,expected_result",
    [
        (False, False, {}, pytest.raises(ValueError), None),
        (False, False, {"name": "testdistro"}, does_not_raise(), None),
    ],
)
def test_find_profile(
    find_fillup: CobblerAPI,
    return_list: bool,
    no_errors: bool,
    criteria: Dict[str, Any],
    expected_exception: Any,
    expected_result: None,
):
    """
    Test to verify that profiles can be searched for.
    """
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_profile(return_list, no_errors, **criteria)  # type: ignore[reportArgumentType]

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "return_list,no_errors,criteria,expected_exception,expected_result",
    [
        (False, False, {}, pytest.raises(ValueError), None),
        (False, False, {"name": "testdistro"}, does_not_raise(), None),
    ],
)
def test_find_system(
    find_fillup: CobblerAPI,
    return_list: bool,
    no_errors: bool,
    criteria: Dict[str, Any],
    expected_exception: Any,
    expected_result: None,
):
    """
    Test to verify that systems can be searched for.
    """
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_system(return_list, no_errors, **criteria)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "return_list,no_errors,criteria,expected_exception,expected_result",
    [
        (False, False, {}, pytest.raises(ValueError), None),
        (False, False, {"name": "testdistro"}, does_not_raise(), None),
    ],
)
def test_find_repo(
    find_fillup: CobblerAPI,
    return_list: bool,
    no_errors: bool,
    criteria: Dict[str, Any],
    expected_exception: Any,
    expected_result: None,
):
    """
    Test to verify that repositories can be searched for.
    """
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_repo(return_list, no_errors, **criteria)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "return_list,no_errors,criteria,expected_exception,expected_result",
    [
        (False, False, {}, pytest.raises(ValueError), None),
        (False, False, {"name": "testdistro"}, does_not_raise(), None),
    ],
)
def test_find_image(
    find_fillup: CobblerAPI,
    return_list: bool,
    no_errors: bool,
    criteria: Optional[Dict[str, Any]],
    expected_exception: Any,
    expected_result: None,
):
    """
    Test to verify that images can be searched for.
    """
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        if criteria is not None:
            result = test_api.find_image(return_list, no_errors, **criteria)
        else:
            result = test_api.find_image(return_list, no_errors)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "return_list,no_errors,criteria,expected_exception,expected_result",
    [
        (False, False, {}, pytest.raises(ValueError), None),
        (False, False, {"name": "test"}, does_not_raise(), None),
        (False, False, None, pytest.raises(ValueError), None),
        (False, False, {"name": "testdistro"}, does_not_raise(), None),
    ],
)
def test_find_menu(
    find_fillup: CobblerAPI,
    return_list: bool,
    no_errors: bool,
    criteria: Optional[Dict[str, Any]],
    expected_exception: Any,
    expected_result: None,
):
    """
    Test to verify that menus can be searched for.
    """
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        if criteria is not None:
            result = test_api.find_menu(return_list, no_errors, **criteria)
        else:
            result = test_api.find_menu(return_list, no_errors)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "return_list,no_errors,criteria,expected_exception,expected_result",
    [
        (False, False, {}, pytest.raises(ValueError), None),
        (False, False, {"name": "test"}, does_not_raise(), None),
        (False, False, None, pytest.raises(ValueError), None),
        (False, False, {"name": "testdistro"}, does_not_raise(), None),
    ],
)
def test_find_network_interface(
    find_fillup: CobblerAPI,
    return_list: bool,
    no_errors: bool,
    criteria: Optional[Dict[str, Any]],
    expected_exception: Any,
    expected_result: None,
):
    """
    Test to verify that network_interfaces can be searched for.
    """
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        if criteria is not None:
            result = test_api.find_network_interface(return_list, no_errors, **criteria)
        else:
            result = test_api.find_network_interface(return_list, no_errors)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize(
    "return_list,no_errors,criteria,expected_exception,expected_result",
    [
        (False, False, {}, pytest.raises(ValueError), None),
        (False, False, {"name": "test"}, does_not_raise(), None),
        (False, False, None, pytest.raises(ValueError), None),
        (False, False, {"name": "testdistro"}, does_not_raise(), None),
    ],
)
def test_find_template(
    find_fillup: CobblerAPI,
    return_list: bool,
    no_errors: bool,
    criteria: Optional[Dict[str, Any]],
    expected_exception: Any,
    expected_result: None,
):
    """
    Test to verify that templates can be searched for.
    """
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        if criteria is not None:
            result = test_api.find_template(return_list, no_errors, **criteria)
        else:
            result = test_api.find_template(return_list, no_errors)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result
