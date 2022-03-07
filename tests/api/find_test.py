import pytest

from tests.conftest import does_not_raise


@pytest.fixture
def find_fillup(cobbler_api):
    # TODO: Extend the fillup and add more testcases
    return cobbler_api


@pytest.mark.parametrize("what,criteria,name,return_list,no_errors,expected_exception,expected_result", [
    ("", None, "test", False, False, does_not_raise(), None),
    ("", None, "", False, False, pytest.raises(ValueError), None),
    ("distro", {}, "test", False, False, does_not_raise(), None),
    ("distro", {}, "", False, False, pytest.raises(ValueError), None)
])
def test_find_items(find_fillup, what, criteria, name, return_list, no_errors, expected_exception, expected_result):
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


@pytest.mark.parametrize("name,return_list,no_errors,criteria,expected_exception,expected_result", [
    (None, False, False, {}, pytest.raises(ValueError), None),
    ("testdistro", False, False, {}, does_not_raise(), None)
])
def test_find_distro(find_fillup, name, return_list, no_errors, criteria, expected_exception, expected_result):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_distro(name, return_list, no_errors, **criteria)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize("name,return_list,no_errors,criteria,expected_exception,expected_result", [
    (None, False, False, {}, pytest.raises(ValueError), None),
    ("testdistro", False, False, {}, does_not_raise(), None)
])
def test_find_profile(find_fillup, name, return_list, no_errors, criteria, expected_exception, expected_result):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_profile(name, return_list, no_errors, **criteria)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize("name,return_list,no_errors,criteria,expected_exception,expected_result", [
    (None, False, False, {}, pytest.raises(ValueError), None),
    ("testdistro", False, False, {}, does_not_raise(), None)
])
def test_find_system(find_fillup, name, return_list, no_errors, criteria, expected_exception, expected_result):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_system(name, return_list, no_errors, **criteria)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize("name,return_list,no_errors,criteria,expected_exception,expected_result", [
    (None, False, False, {}, pytest.raises(ValueError), None),
    ("testdistro", False, False, {}, does_not_raise(), None)
])
def test_find_repo(find_fillup, name, return_list, no_errors, criteria, expected_exception, expected_result):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_repo(name, return_list, no_errors, **criteria)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize("name,return_list,no_errors,criteria,expected_exception,expected_result", [
    (None, False, False, {}, pytest.raises(ValueError), None),
    ("testdistro", False, False, {}, does_not_raise(), None)
])
def test_find_image(find_fillup, name, return_list, no_errors, criteria, expected_exception, expected_result):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_image(name, return_list, no_errors, **criteria)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize("name,return_list,no_errors,criteria,expected_exception,expected_result", [
    (None, False, False, {}, pytest.raises(ValueError), None),
    ("testdistro", False, False, {}, does_not_raise(), None)
])
def test_find_mgmtclass(find_fillup, name, return_list, no_errors, criteria, expected_exception, expected_result):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_mgmtclass(name, return_list, no_errors, **criteria)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize("name,return_list,no_errors,criteria,expected_exception,expected_result", [
    (None, False, False, {}, pytest.raises(ValueError), None),
    ("testdistro", False, False, {}, does_not_raise(), None)
])
def test_find_package(find_fillup, name, return_list, no_errors, criteria, expected_exception, expected_result):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_package(name, return_list, no_errors, **criteria)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize("name,return_list,no_errors,criteria,expected_exception,expected_result", [
    (None, False, False, {}, pytest.raises(ValueError), None),
    ("testdistro", False, False, {}, does_not_raise(), None)
])
def test_find_file(find_fillup, name, return_list, no_errors, criteria, expected_exception, expected_result):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        result = test_api.find_file(name, return_list, no_errors, **criteria)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result


@pytest.mark.parametrize("name,return_list,no_errors,criteria,expected_exception,expected_result", [
    ("", False, False, {}, pytest.raises(ValueError), None),
    ("test", False, False, {}, does_not_raise(), None),
    (None, False, False, None, pytest.raises(ValueError), None),
    ("testdistro", False, False, {}, does_not_raise(), None)
])
def test_find_menu(find_fillup, name, return_list, no_errors, criteria, expected_exception, expected_result):
    # Arrange
    test_api = find_fillup

    # Act
    with expected_exception:
        if criteria is not None:
            result = test_api.find_menu(name, return_list, no_errors, **criteria)
        else:
            result = test_api.find_menu(name, return_list, no_errors)

        # Assert
        if expected_result is None:
            assert result is None
        else:
            assert result == expected_result
